import requests
import sys
import matplotlib.pyplot as plt
import time

# generate test hashes
import hashlib
def generate_hash(password):
    return hashlib.md5(password.encode()).hexdigest()

def try_request(port, payload):
    url = f"http://127.0.0.1:{port}/crack"
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception:
        return None  # service failed or unresponsive

def run_client():
    # cmd line args
    if len(sys.argv) != 5:
        print("Usage: python client.py <start-port> <end-port> <md5_password> <max_password_length>")
        sys.exit(1)
        
    try:
        start_port = int(sys.argv[1])
        end_port = int(sys.argv[2])
        md5_password = sys.argv[3]
        max_length = int(sys.argv[4])
    except ValueError:
        print("Error: Invalid arguments")
        sys.exit(1)

    ports = list(range(start_port, end_port + 1))
    num_services = len(ports)
    chars = 26 

    # compute total search space size
    total = 0
    power = 1
    for L in range(1, max_length + 1):
        power *= chars
        total += power

    # split total into even chunks
    base = total // num_services
    remainder = total % num_services

    chunks = []
    start = 0
    for i in range(num_services):
        size = base + (1 if i < remainder else 0)
        end = start + size - 1
        chunks.append((start, end))
        start = end + 1

    print(f"Total space: {total}, split across {num_services} services")

    start_time = time.time()

    # iterate through chunks and send to services with retry on failure
    for i, (chunk_start, chunk_end) in enumerate(chunks):
        # initial port assignment 
        assigned_port = ports[i % num_services]

        payload = {
            "hashed_password": md5_password,
            "max_length": max_length,
            "start_index": chunk_start,
            "end_index": chunk_end
        }

        result = try_request(assigned_port, payload)
        # if initial attempt failed retry on other ports
        if not result:
            print(f"Service on port {assigned_port} failed, sending chunk to another port")
            for alt in ports:
                if alt == assigned_port:
                    continue
                print(f"Retrying on port {alt}")
                result = try_request(alt, payload)
                if result:
                    assigned_port = alt
                    break

        if not result:
            print(f"Services failed for chunk {chunk_start}-{chunk_end}. Moving to next chunk.")
            continue

        # successful JSON response
        status = result.get('status')
        if status == 'success':
            end_time = time.time()
            total_time = end_time - start_time
            print(f"Password cracked! {result['cleartext_password']}")
            print(f"Found by port: {assigned_port}")
            print(f"Total time to crack: {total_time:.2f} seconds")
            return
        elif status == 'failed':
            # server processed the chunk but didn't find password
            end_time = time.time()
            total_time = end_time - start_time
            print(f"Chunk {chunk_start}-{chunk_end} processed by port {assigned_port}: {result.get('message')}")
            print(f"Returned after {total_time}.")
        else:
            # unexpected response
            print(f"Error: {assigned_port}: {result}")

    print("Password not found in given range.")


    # PART 2
    '''for i, (start_i, end_i) in enumerate(chunks):
        port = start_port + i
        url = f"http://127.0.0.1:{port}/crack"
        payload = {
            "hashed_password": md5_password,
            "max_length": max_length,
            "start_index": start_i,
            "end_index": end_i
        } 

        try:
            response = requests.post(url, json=payload)
            result = response.json()

            if result.get('status') == 'success':
                print("Password cracked!")
                print(f"Found: {result['cleartext_password']} (by port {port})")
                return
        except Exception:
            print("Error")

    print("Password not found in given range") '''
        
if __name__ == "__main__":
    run_client()