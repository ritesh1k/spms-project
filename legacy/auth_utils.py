import base64
import hashlib
import hmac
import os
import re
import secrets

_HASH_PREFIX = "pbkdf2_sha256"
_ITERATIONS = 180000
_SALT_BYTES = 16

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(value):
    return str(value or "").strip().lower()


def valid_email(value):
    return bool(EMAIL_REGEX.match(normalize_email(value)))


def hash_password(password: str) -> str:
    if not password or not isinstance(password, str):
        raise ValueError("Password must be a non-empty string")

    salt = secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        _ITERATIONS,
        dklen=32,
    )
    return "{}${}${}${}".format(
        _HASH_PREFIX,
        _ITERATIONS,
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    )


def is_hashed_password(value: str) -> bool:
    return isinstance(value, str) and value.startswith(f"{_HASH_PREFIX}$")


def verify_password(password: str, stored_password: str) -> bool:
    if not isinstance(password, str) or not isinstance(stored_password, str):
        return False

    if is_hashed_password(stored_password):
        try:
            _, iterations_text, salt_text, digest_text = stored_password.split("$", 3)
            iterations = int(iterations_text)
            salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
            expected_digest = base64.urlsafe_b64decode(digest_text.encode("ascii"))
            actual_digest = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt,
                iterations,
                dklen=len(expected_digest),
            )
            return hmac.compare_digest(actual_digest, expected_digest)
        except Exception:
            return False

    # Legacy plaintext fallback for migration support
    return hmac.compare_digest(stored_password, password)


def should_upgrade_password(stored_password: str) -> bool:
    return isinstance(stored_password, str) and stored_password and not is_hashed_password(stored_password)


def generate_temp_password(length: int = 12) -> str:
    if length < 8:
        length = 8
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))
