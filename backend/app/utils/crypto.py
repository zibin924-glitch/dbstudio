"""
AES-256 symmetric encryption utilities for DBStudio.

Passwords for remote database connections are encrypted at rest using
AES-256-CBC with PKCS7 padding and a cryptographically random 16-byte IV.
The ciphertext layout stored in the database is::

    base64( IV[16] || AES-CBC(plaintext, key, IV) )

The 64-character hex key (32 bytes) is read from the
``DBSTUDIO_ENCRYPTION_KEY`` environment variable / config setting.

Generate a suitable key once with::

    python -c "import secrets; print(secrets.token_hex(32))"
"""

import base64
import os

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding as sym_padding


# AES block size in bits (always 128 for AES regardless of key length).
_AES_BLOCK_BITS = 128
_IV_BYTES = 16  # 128 bits


def _validate_key(key: str) -> bytes:
    """
    Decode and validate a hex-encoded AES-256 key.

    Args:
        key: A 64-character hexadecimal string representing exactly 32 bytes.

    Returns:
        The decoded 32-byte key.

    Raises:
        ValueError: If *key* is not exactly 64 hex characters (32 bytes).
    """
    if not key or len(key) != 64:
        raise ValueError(
            "ENCRYPTION_KEY must be a 64-character hex string (32 bytes). "
            "Generate one with:  python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    try:
        raw = bytes.fromhex(key)
    except ValueError as exc:
        raise ValueError(
            "ENCRYPTION_KEY contains non-hexadecimal characters."
        ) from exc

    if len(raw) != 32:
        raise ValueError(
            f"Decoded key is {len(raw)} bytes; AES-256 requires exactly 32 bytes."
        )
    return raw


def encrypt(plaintext: str, key: str) -> str:
    """
    Encrypt *plaintext* with AES-256-CBC and return a base64-encoded string.

    The returned string contains ``IV || ciphertext`` so that the matching
    ``decrypt`` call can recover the IV without any out-of-band state.

    Args:
        plaintext: The clear-text value to encrypt (e.g. a database password).
        key:       64-character hex AES-256 key.

    Returns:
        Base64-encoded ``IV + ciphertext`` ready for storage.

    Raises:
        ValueError: If *key* is malformed.
    """
    raw_key = _validate_key(key)
    iv = os.urandom(_IV_BYTES)

    # PKCS7-pad the plaintext to a multiple of the AES block size.
    padder = sym_padding.PKCS7(_AES_BLOCK_BITS).padder()
    padded_data = padder.update(plaintext.encode("utf-8")) + padder.finalize()

    cipher = Cipher(algorithms.AES(raw_key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded_data) + encryptor.finalize()

    # Prepend IV so decrypt can extract it without separate storage.
    return base64.b64encode(iv + ciphertext).decode("ascii")


def decrypt(ciphertext_b64: str, key: str) -> str:
    """
    Decrypt a value previously produced by :func:`encrypt`.

    Args:
        ciphertext_b64: Base64 string containing ``IV || ciphertext``.
        key:            64-character hex AES-256 key (same one used to encrypt).

    Returns:
        The original plaintext string.

    Raises:
        ValueError:  If *key* is malformed.
        Exception:   If decryption or unpadding fails (wrong key, corrupted data).
    """
    raw_key = _validate_key(key)

    try:
        raw_payload = base64.b64decode(ciphertext_b64)
    except Exception as exc:
        raise Exception("Ciphertext is not valid base64.") from exc

    if len(raw_payload) < _IV_BYTES + 16:
        raise Exception(
            "Ciphertext is too short to contain a valid IV and at least one AES block."
        )

    iv = raw_payload[:_IV_BYTES]
    ciphertext = raw_payload[_IV_BYTES:]

    cipher = Cipher(algorithms.AES(raw_key), modes.CBC(iv))
    decryptor = cipher.decryptor()

    try:
        padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
    except Exception as exc:
        raise Exception("Decryption failed — the key may be incorrect.") from exc

    try:
        unpadder = sym_padding.PKCS7(_AES_BLOCK_BITS).unpadder()
        plaintext_bytes = unpadder.update(padded_plaintext) + unpadder.finalize()
    except Exception as exc:
        raise Exception(
            "PKCS7 unpadding failed — the ciphertext may be corrupt or the key is wrong."
        ) from exc

    return plaintext_bytes.decode("utf-8")
