"""
real_experiment.py

Real (end-to-end) experiment runner for cracker_service.py + password_client.py.

Usage:
    python3 real_experiment.py

Requirements:
    pip3 install requests pandas matplotlib

Edit the PARAMETERS section below to change test scale.
"""
import os, sys, time, subprocess, math, random, socket, json
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Event
import requests
import pandas as pd
import matplotlib.pyplot as plt

# --------------------- PARAMETERS (edit as needed) ---------------------
PY = sys.executable or "python3"
BASE_PORT = 5000                   # first port to use when starting services
WORKER_TEST_LIST = [1, 2, 3, 4]    # which worker counts to test (must be <= number of ports you are willing to open)
MAX_TEST_LENGTH = 5                # max password length to test (1..MAX_TEST_LENGTH). 4 is safe; 5 slower; 6 very slow.
TRIALS = 2                        # trials per (workers, length) config
CHUNK_EXPERIMENT_WORKERS = 4       # number of services to run for chunk-size experiment
CHUNK_LIST = [1, 2, 4, 8, 16]     # chunk counts to test (smaller => larger chunk size)
TIMEOUT_CLIENT = 600 * 10           # timeout (s) for running the client per trial (use large for bigger lengths)
TIMEOUT_POST = 600 * 10             # timeout for requests.post to a service chunk
PASSWORD_CHARS = "abcdefghijklmnopqrstuvwxyz"  # must match what your service expects
CRACKER_MODULE = "cracker_service" # filename without .py
CLIENT_SCRIPT = "password_client.py"           # your client file
OUTPUT_DIR = "exp_results"
RANDOM_SEED = 12345
# ----------------------------------------------------------------------

random.seed(RANDOM_SEED)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --------------------- helper utilities ---------------------
def is_port_open(port, host="127.0.0.1", timeout=1.0):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False

def start_service_process(port):
    """Start a Python subprocess that imports cracker_service and runs app.run(port=port)."""
    cmd = [
        PY, "-u", "-c",
        (
            "import importlib, sys; "
            f"m = importlib.import_module('{CRACKER_MODULE}'); "
            f"app = getattr(m, 'app'); "
            f"app.run(host='127.0.0.1', port={port})"
        )
    ]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # wait until port listening (simple loop)
    for _ in range(40):
        if is_port_open(port, timeout=0.25):
            return p
        time.sleep(0.05)
    # if not open after tries, still return process (caller should check)
    return p

def stop_service_process(p):
    try:
        p.terminate()
        p.wait(timeout=1.0)
    except Exception:
        try:
            p.kill()
        except Exception:
            pass

def start_services(n, base_port=BASE_PORT):
    procs = []
    for i in range(n):
        port = base_port + i
        p = start_service_process(port)
        procs.append((p, port))
    # final check: ensure ports open
    for _, port in procs:
        if not is_port_open(port):
            print(f"Warning: port {port} not open (service may have crashed).")
    # brief warmup
    time.sleep(0.15)
    return procs

def stop_services(procs):
    for p, port in procs:
        stop_service_process(p)
    time.sleep(0.05)

def parse_found_from_stdout(out):
    """Robustly try to extract cracked password from client stdout."""
    if not out:
        return None
    out = out.strip()
    for line in out.splitlines():
        low = line.lower().strip()
        if low.startswith("found:"):
            return line.split(":",1)[1].strip()
        if "password cracked" in low or "password found" in low or "cleartext" in low:
            # fallback heuristic: last token
            parts = line.strip().split()
            if parts:
                cand = parts[-1].strip()
                if cand:
                    return cand
    return None

# --------------------- supporting math for chunking ---------------------
ALPH = PASSWORD_CHARS
N = len(ALPH)

def total_space(max_length):
    total = 0
    power = 1
    for L in range(1, max_length+1):
        power *= N
        total += power
    return total

def build_chunks(total, num_chunks):
    base = total // num_chunks
    rem = total % num_chunks
    out = []
    s = 0
    for i in range(num_chunks):
        size = base + (1 if i < rem else 0)
        e = s + size - 1
        out.append((s,e))
        s = e + 1
    return out

# --------------------- Experiment A: services vs length (real client) ---------------------
def run_client_trial(start_port, end_port, md5_password, max_length):
    cmd = [PY, CLIENT_SCRIPT, str(start_port), str(end_port), md5_password, str(max_length)]
    t0 = time.time()
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=TIMEOUT_CLIENT, text=True)
        elapsed = time.time() - t0
        out = proc.stdout or ""
        err = proc.stderr or ""
        found = parse_found_from_stdout(out)
        return elapsed, found, out, err
    except subprocess.TimeoutExpired:
        return float('inf'), None, "", "TIMEOUT"

def experiment_services_vs_length():
    rows = []
    for L in range(1, MAX_TEST_LENGTH + 1):
        total = total_space(L)
        print(f"\n== LENGTH {L} total_space={total} ==")
        for workers in WORKER_TEST_LIST:
            print(f" Testing workers={workers} ...")
            procs = start_services(workers, BASE_PORT)
            start_port = BASE_PORT
            end_port = BASE_PORT + workers - 1
            trial_times = []
            for t in range(TRIALS):
                # choose a random password index and generate a plaintext matching the service alphabet
                # we pick a random cleartext by randomly selecting characters - it's in the search space
                pw = "".join(random.choice(ALPH) for _ in range(L))
                md5 = __import__("hashlib").md5(pw.encode()).hexdigest()
                elapsed, found, out, err = run_client_trial(start_port, end_port, md5, L)
                trial_times.append(elapsed)
                print(f"  trial: {t} workers: {workers} elapsed: {elapsed:.3f} found: {found if found else '(unknown)'}")
                # small pause
                time.sleep(0.06)
            stop_services(procs)
            finite = [x for x in trial_times if math.isfinite(x)]
            mean = sum(finite)/len(finite) if finite else float('inf')
            std = math.sqrt(sum((x-mean)**2 for x in finite)/len(finite)) if finite else float('inf')
            rows.append({'length': L, 'workers': workers, 'mean_time_s': mean, 'std_time_s': std, 'trials': TRIALS, 'total_space': total})
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUTPUT_DIR, "services_vs_length.csv"), index=False)
    return df

# --------------------- Experiment B: chunk-size experiment (direct POSTs) ---------------------
def post_chunk(port, payload, timeout=TIMEOUT_POST):
    try:
        resp = requests.post(f"http://127.0.0.1:{port}/crack", json=payload, timeout=timeout)
        if resp.ok:
            return resp.json()
    except Exception as e:
        return None
    return None

def experiment_chunks_vs_time():
    rows = []
    max_length = MAX_TEST_LENGTH
    total = total_space(max_length)
    workers = CHUNK_EXPERIMENT_WORKERS
    ports = [BASE_PORT + i for i in range(workers)]
    print(f"\n== Chunk experiment: max_length={max_length}, total_space={total}, workers={workers} ==")
    for chunks in CHUNK_LIST:
        print(f" Testing chunks={chunks} ...")
        trial_times = []
        for t in range(TRIALS):
            # random target plaintext
            pw = "".join(random.choice(ALPH) for _ in range(max_length))
            hashed = __import__("hashlib").md5(pw.encode()).hexdigest()
            ranges = build_chunks(total, chunks)
            # start services
            procs = start_services(workers, BASE_PORT)
            # fire off threads calling post_chunk for each chunk (assign port round-robin)
            success_event = Event()
            found_pw = [None]
            t0 = time.time()
            with ThreadPoolExecutor(max_workers=len(ranges)) as ex:
                futures = []
                for i,(s,e) in enumerate(ranges):
                    port = ports[i % len(ports)]
                    payload = {"hashed_password": hashed, "max_length": max_length, "start_index": s, "end_index": e}
                    futures.append(ex.submit(post_chunk, port, payload, TIMEOUT_POST))
                # wait for any successful response
                elapsed = float('inf')
                for fut in as_completed(futures, timeout=TIMEOUT_POST):
                    try:
                        res = fut.result(timeout=0.01)
                        if res and res.get('status') == 'success':
                            elapsed = time.time() - t0
                            found_pw[0] = res.get('cleartext_password')
                            break
                    except Exception:
                        pass
            stop_services(procs)
            trial_times.append(elapsed)
            print(f"  trial {t}: elapsed {elapsed if math.isfinite(elapsed) else 'TIMEOUT/inf'} found: {found_pw[0] if found_pw[0] else '(not found)'}")
            time.sleep(0.06)
        finite = [x for x in trial_times if math.isfinite(x)]
        mean = sum(finite)/len(finite) if finite else float('inf')
        std = math.sqrt(sum((x-mean)**2 for x in finite)/len(finite)) if finite else float('inf')
        rows.append({'max_length': max_length, 'workers': workers, 'chunks': chunks, 'mean_time_s': mean, 'std_time_s': std, 'trials': TRIALS, 'total_space': total})
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUTPUT_DIR, "chunks_vs_time.csv"), index=False)
    return df

# --------------------- Plotting ---------------------
def plot_services_vs_length(df):
    plt.figure(figsize=(9,6))
    for L in sorted(df['length'].unique()):
        sub = df[df['length']==L].sort_values('workers')
        plt.plot(sub['workers'], sub['mean_time_s'], marker='o', label=f'length={L}')
    plt.xlabel('Number of services (workers)')
    plt.ylabel('Average time to crack (s)')
    plt.title('Services vs Avg cracking time (real-run)')
    plt.legend()
    plt.grid(True)
    out = os.path.join(OUTPUT_DIR, "services_vs_length.png")
    plt.savefig(out)
    plt.close()
    print("Saved:", out)

def plot_chunks_vs_time(df):
    plt.figure(figsize=(9,6))
    sub = df.sort_values('chunks')
    plt.plot(sub['chunks'], sub['mean_time_s'], marker='o')
    plt.xscale('log', base=2)
    plt.xlabel('Number of chunks (log2)')
    plt.ylabel('Average time to crack (s)')
    plt.title(f'Chunk count vs Avg time (workers={CHUNK_EXPERIMENT_WORKERS})')
    plt.grid(True)
    out = os.path.join(OUTPUT_DIR, "chunks_vs_time.png")
    plt.savefig(out)
    plt.close()
    print("Saved:", out)

# --------------------- Main ---------------------
def main():
    print("REAL experiment starting. WARNING: long runs possible for large lengths.")
    print(f"Parameters: BASE_PORT={BASE_PORT}, WORKER_TEST_LIST={WORKER_TEST_LIST}, MAX_TEST_LENGTH={MAX_TEST_LENGTH}, TRIALS={TRIALS}")
    svc_df = experiment_services_vs_length()
    plot_services_vs_length(svc_df)
    chunk_df = experiment_chunks_vs_time()
    plot_chunks_vs_time(chunk_df)
    print("Finished. Results in", OUTPUT_DIR)

if __name__ == "__main__":
    main()