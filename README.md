# Distributed Password Cracker
MPCS 52040 — Distributed Systems  

## Overview
A distributed brute-force MD5 password-cracking system built with Flask. Multiple service instances run in parallel, each searching a portion of the password space. A Python client coordinates chunking, concurrency, retries, and early termination.

## Components
- `cracker_service.py` — Flask REST API, JSON I/O, partial-space cracking, in-memory caching.  
- `client.py` — Distributes chunks across ports, handles failures, aggregates results.  
- `performance_tests.py` — Scaling experiments + matplotlib plots.  
- `report.md` — Documentation for fault tolerance, caching, and performance.

## Running Services
flask --app cracker_service run --port <port>

shell
Code kopieren

## Running Client
python client.py <start-port> <end-port> <md5_hash> <max_length>

markdown
Code kopieren

## Features
### Distributed Search
- Deterministic chunk partitioning (prefix-based).
- Concurrent requests to all active services.
- Stops immediately once any worker finds the password.

### Fault Tolerance
- Detects timeouts/connection errors.
- Automatically reassigns failed chunks.
- Manually killing a service mid-run still results in full coverage.

### Caching (Service-side)
- Stores results per `(hashed_password, chunk_id)`.
- Eliminates repeated computation for identical requests.

## Performance Evaluation
Two required plots:
1. Cracking time vs. password length.  
2. Cracking time vs. chunk size (fixed workers/length).  

General trends:
- Time grows exponentially (~26^L).  
- More workers help until core saturation.  
- Too few chunks → idle workers. Too many → overhead.  
- Best chunk count is ~4–8 per worker.

## Hashing
```python
import hashlib
hashlib.md5("password".encode()).hexdigest()
Repository Structure
Code kopieren
.
├── cracker_service.py
├── client.py
├── performance_tests.py
├── plots/
├── report.md
└── README.md
