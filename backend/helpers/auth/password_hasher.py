from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher()

def hash_password(plaintext_password: str) -> str:
    return _hasher.hash(plaintext_password)

def verify_password(plaintext_password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, plaintext_password)
    except VerifyMismatchError:
        return False