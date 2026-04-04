import random
import string
import hashlib

def generate_random_key(length: str) -> str:
    letters = string.ascii_letters + string.digits
    return ''.join(random.choice(letters) for _ in range(length))

def get_as_hashed(string: str) -> str:
    return hashlib.sha256(string.encode()).hexdigest()