from flask import Flask, request, jsonify
import itertools
import string
import hashlib
import threading
# import time


def bruteforce_password(hashed_password, max_length):
    ''' PART 1 find the cleartext password up to max_length '''
    chars = string.ascii_lowercase
    
    for password_length in range(1, max_length + 1):
        for guess_tuple in itertools.product(chars, repeat=password_length):
            guess = ''.join(guess_tuple)
            if hashlib.md5(guess.encode()).hexdigest() == hashed_password:
                return guess

    return None

# print(bruteforce_password('cce6b3fb87d8237167f1c5dec15c3133', 4))

''' PART 2 distribute workload '''
def d_to_char(d):
    return string.ascii_lowercase[d]

def unrank_password(index, max_length):
    chars = string.ascii_lowercase
    n = len(chars) # 26

    # determine length
    length = 1
    current_count = n
    while index >= current_count and length < max_length:
        index -= current_count
        length += 1
        current_count *= n 

    if length > max_length: 
        return None 
    
    # remaining index to base-n string
    guess = []
    
    for _ in range(length):
        digit = index % n
        guess.append(d_to_char(digit))
        index //= n
    
    return "".join(reversed(guess))

def bruteforce_index_range(hashed_password, start_index, end_index, max_length):
    for i in range(start_index, end_index + 1):
        guess = unrank_password(i, max_length)
        if guess is None: # only if < max_length
            continue

        if hashlib.md5(guess.encode()).hexdigest() == hashed_password:
            return guess
    return None

# create cache for part 5 
cache = {}
cache_lock = threading.Lock()

def cache_get(key):
    with cache_lock:
        return cache.get(key)

def cache_set(key, value):
    with cache_lock:
        cache[key] = value

app = Flask(__name__) 

# @app registers crack_password function as handler for HTTP POST requests sent to /crack on flask app
@app.route('/crack', methods=['POST'])
def crack_password():
    ''' REST to receive hashed password and return cracked password '''
    try:
        data = request.get_json()

        hashed_password = data.get('hashed_password')
        max_length = data.get('max_length')
        start_index = data.get('start_index')
        end_index = data.get('end_index')

        if not hashed_password or not isinstance(max_length, int):
            return jsonify({"Error": "Invalid input"}), 400

        # part 2
        if start_index is not None and end_index is not None:
            # normalize and prepare cache key
            start_index = int(start_index)
            end_index = int(end_index)
            key = (hashed_password, int(max_length), start_index, end_index)

            # cache hit
            cached = cache_get(key)
            if cached is not None:
                return jsonify(cached), 200

            print("Distributing workload ")
            cleartext_password = bruteforce_index_range(hashed_password, start_index, end_index, max_length)
            if cleartext_password:
                result = {
                    "status": "success",
                    "cleartext_password": cleartext_password,
                    "hashed_password": hashed_password
                }
            else:
                result = {
                    "status": "failed",
                    "message": f"Password not found in range {start_index}-{end_index} up to length {max_length}",
                    "hashed_password": hashed_password
                }

            cache_set(key, result)
            return jsonify(result), 200

        # full search part 1
        print("Full search")
        cleartext_password = bruteforce_password(hashed_password, max_length)
        if cleartext_password:
            return jsonify({
                "status": "success",
                "cleartext_password": cleartext_password,
                "hashed_password": hashed_password
            }), 200
        else:
            return jsonify({
                "status": "failed",
                "message": f"Password not found up to length {max_length}",
                "hashed_password": hashed_password
            }), 200

    except Exception:
        return jsonify({"Error"}), 500
    
