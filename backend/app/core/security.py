import hashlib


def hash_password(password: str) -> str:
    """Hash a plaintext password for storage.

    VULN-5 (Weak Password Storage):
    Uses raw MD5 with no salt and no key-derivation function. MD5 digests can
    be reversed instantly with rainbow tables or dictionary attacks, so any
    database leak exposes all plaintext passwords.
    """
    return hashlib.md5(password.encode("utf-8")).hexdigest()


def verify_password(plain: str, hashed: str) -> bool:
    """Compare a plaintext password against a stored hash.

    VULN-5 (Weak Password Storage):
    Uses the same unsalted MD5 routine as hash_password().
    """
    return hash_password(plain) == hashed
