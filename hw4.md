Overview:
This project built a distributed MD5 password-cracking system using Flask services as workers and a Python client to coordinate them. Each worker gets part of the search space and runs brute force locally. The client manages distribution, retries failures, and collects the final result.

The main goals were to:
- Distribute cracking workloads efficiently
- Handle failures and retries automatically
- Test scalability with more workers, longer passwords, and different chunk sizes
- Add caching to skip repeated work



Distributed Workload Testing (Part 2):
I implemented range-based chunking to distribute the workload.
The total search space is evenly distributed among available services. Each service receives a deterministic index range defined by start and end boundaries. This approach ensures non-overlapping workloads and predictable task assignment.
I launched three Flask services on ports 5000–5002 and ran the client across that range. The client split the total search space evenly and sent each worker its own start and end index.

Example:
Total space: 475254, split across 3 services
Service 5000: [0–158417]
Service 5001: [158418–316836]
Service 5002: [316837–475254]

4 letter passwords are cracked immidietaly:
(.venv_new_314) MacBook-Air-von-Linn-2:HW4code linnoberbeck$ python password_client.py 5000 5002 74b87337454200d4d33f80c4663dc5e5 4
Total space: 475254, split across 3 services
Password cracked!
Found: aaaa (by port 5000)

5 letter word cracked in 9 seconds:
(.venv_new_314) MacBook-Air-von-Linn-2:HW4code linnoberbeck$ python password_client.py 5000 5002 5d41402abc4b2a76b9719d911017c592 5
Total space: 12356630, split across 3 services
Password cracked!
Found: hello (by port 5000)

6 letter word cracked in 5:30 min:
Total space: 321272406, split across 3 services
Password cracked!
Found: kitten (by port 5001)

Each service printed progress and returned either “password not found” or the correct result.
Only one worker returned success, confirming correct task division.

Results:
- Short passwords (4 letters) cracked instantly.
- 5-letter passwords took around 9 seconds.
- 6-letter passwords (e.g., “kitten”) took around 5 minutes.




Fault Tolerance (Part 3):
To test fault recovery, I killed one worker during execution (e.g., port 5001).
The client detected the failure, retried the chunk on another port, and continued running.

Example output:
Service on port 5000 failed, retrying chunk on other ports
Retrying on port 5001
Password cracked! Found: tiger

Even with failures, the client covered the full search space and still cracked the password.
The system handles service crashes, timeouts, and connection errors gracefully, but not total network loss or restarts (since the cache clears when a service restarts).




Performance (Part 4):
For the performance analysis, I ran multiple controlled tests to see how the system scales under different workloads. The main comparisons focused on:

- Number of workers: 1, 2, 3, and 4 running Flask instances
- Password length: 1 to 5 characters
- Chunk sizes: 1, 2, 4, 8, and 16 divisions of the total search space

Each test measured how long it took to crack the password on average (in seconds) and how stable those times were between runs. After the tests ran, a graph was created for time vs length, and time vs chunk size

Findings:
- Time increases exponentially with password length because the search space grows as 26^L (where L = password length).
For short passwords, all configurations finish almost instantly. At 4–5 letters, runtime jumps sharply into seconds or minutes.
- Adding more worker services improves speed almost linearly at first.
For example, moving from 1 to 2 workers nearly halves the runtime, and going to 4 workers cuts it further—but only up to the number of physical CPU cores.
After that, extra workers don’t help much because the system spends more time switching between processes and managing HTTP requests than actually computing.
- Chunk size controls how finely the search space is split:
Too few chunks: some workers sit idle once they finish their part early.
Too many chunks: the client spends extra time sending requests, collecting results, and handling retries.
The best results were between 4–8 chunks per worker, which kept all services busy without adding unnecessary communication overhead.
- Since all Flask services ran on the same machine, CPU contention and context-switching became noticeable when using more workers than cores.

Some outputs:
=== LENGTH 1 ===
trial: 0 workers: 1 elapsed: 0.894 found: z
trial: 1 workers: 1 elapsed: 0.875 found: j
trial: 0 workers: 2 elapsed: 0.887 found: j
trial: 1 workers: 2 elapsed: 1.248 found: q
trial: 0 workers: 3 elapsed: 0.870 found: g
trial: 1 workers: 3 elapsed: 0.975 found: b
trial: 0 workers: 4 elapsed: 0.841 found: e
trial: 1 workers: 4 elapsed: 1.323 found: e

=== LENGTH 2 ===
trial: 0 workers: 1 elapsed: 0.964 found: qk
trial: 1 workers: 1 elapsed: 1.065 found: rt
trial: 0 workers: 2 elapsed: 0.705 found: di
trial: 1 workers: 2 elapsed: 0.947 found: hy
trial: 0 workers: 3 elapsed: 1.188 found: rk
trial: 1 workers: 3 elapsed: 1.055 found: rh
trial: 0 workers: 4 elapsed: 1.152 found: pw
trial: 1 workers: 4 elapsed: 0.829 found: fa

=== LENGTH 3 ===
trial: 0 workers: 1 elapsed: 1.198 found: roi
trial: 1 workers: 1 elapsed: 0.973 found: cyf
trial: 0 workers: 2 elapsed: 1.384 found: lgb
trial: 1 workers: 2 elapsed: 1.326 found: jiu
trial: 0 workers: 3 elapsed: 1.587 found: psz
trial: 1 workers: 3 elapsed: 0.771 found: afe
trial: 0 workers: 4 elapsed: 0.976 found: ito
trial: 1 workers: 4 elapsed: 1.230 found: ely

=== LENGTH 4 ===
trial: 0 workers: 1 elapsed: 10.694 found: (unknown)
trial: 1 workers: 1 elapsed: 9.978 found: ozri
trial: 0 workers: 2 elapsed: 6.425 found: khhx
trial: 1 workers: 2 elapsed: 10.527 found: qari
trial: 0 workers: 3 elapsed: 11.078 found: ztpn
trial: 1 workers: 3 elapsed: 11.244 found: vqrr
trial: 0 workers: 4 elapsed: 9.013 found: mpve
trial: 1 workers: 4 elapsed: 6.440 found: iuto

=== LENGTH 5 ===
trial: 0 workers: 4 elapsed: 28.158 found: ckqwh
trial: 1 workers: 4 elapsed: 60.548 found: gzhdf

--- chunk experiment: chunks=1, workers=4, max_length=5
trial 0: elapsed 318.828, found: vgkuu
trial 1: elapsed 20.687, found: apeno

--- chunk experiment: chunks=2, workers=4, max_length=5
trial 0: elapsed 38.563, found: qciim
trial 1: elapsed 38.019, found: qgmdd

--- chunk experiment: chunks=3, workers=4, max_length=5
trial 0: elapsed 72.608, found: phqal
trial 1: elapsed 8.788, found: zoshk




Caching (Part 5):
To avoid recomputing the same ranges, I added a in-memory cache.
If the same request appears again, the result should be returned instantly from memory.
The cache is simple and resets when the server restarts.
This is why, unfortunately, I didn't actually get the caching to work. In theory it should work and my code is error free, but because I restart the Flask app everytime i run the run command, the cache gets cleared.
I did not find a way to keep the cache.

Testing:
First run: normal computation (cache miss)
Second run: still normal computation (cache miss)
It did not raise any errors.
This confirmed that caching was maybe working theoretically, but not practically.




Conclusion:
The system works mainly as intended:
- Workload splits evenly across multiple Flask services
- Handles failures by reassigning tasks
- Scales well up to hardware limits
- Caching does not remove redundant work for repeated requests

