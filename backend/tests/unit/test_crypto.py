"""
Unit tests for app.utils.crypto — AES-256 encryption/decryption utilities.

Tests verify round-trip encryption, randomness of IV, handling of wrong keys,
edge cases (empty strings, unicode, long payloads), and key validation.
"""

import pytest

from app.utils.crypto import decrypt, encrypt


@pytest.mark.unit
class TestCrypto:
    """Tests for the encrypt / decrypt helpers."""

    def test_encrypt_decrypt_roundtrip(self, encryption_key):
        """Encrypting then decrypting must return the original plaintext."""
        plaintext = "my_secret_password_123"
        ciphertext = encrypt(plaintext, encryption_key)
        result = decrypt(ciphertext, encryption_key)
        assert result == plaintext

    def test_encrypt_produces_different_ciphertext(self, encryption_key):
        """Two encryptions of the same plaintext should differ (random IV)."""
        plaintext = "same_password"
        ct1 = encrypt(plaintext, encryption_key)
        ct2 = encrypt(plaintext, encryption_key)
        assert ct1 != ct2, "Ciphertexts should differ because IV is randomised"
        # But both must decrypt to the same plaintext
        assert decrypt(ct1, encryption_key) == plaintext
        assert decrypt(ct2, encryption_key) == plaintext

    def test_decrypt_with_wrong_key_fails(self, encryption_key):
        """Decrypting with a different key must raise an exception."""
        plaintext = "top_secret"
        ciphertext = encrypt(plaintext, encryption_key)
        wrong_key = "b" * 64  # different 64-hex-char key
        with pytest.raises(Exception):
            decrypt(ciphertext, wrong_key)

    def test_encrypt_empty_string(self, encryption_key):
        """Empty string should encrypt and decrypt without errors."""
        ciphertext = encrypt("", encryption_key)
        assert ciphertext is not None
        assert decrypt(ciphertext, encryption_key) == ""

    def test_encrypt_unicode(self, encryption_key):
        """Unicode characters (Chinese, emoji, special chars) must survive round-trip."""
        plaintext = "数据库密码🔐 — café & résumé <script>"
        ciphertext = encrypt(plaintext, encryption_key)
        result = decrypt(ciphertext, encryption_key)
        assert result == plaintext

    def test_encrypt_long_password(self, encryption_key):
        """A 500-character password should encrypt and decrypt correctly."""
        plaintext = "A" * 250 + "B" * 250
        ciphertext = encrypt(plaintext, encryption_key)
        result = decrypt(ciphertext, encryption_key)
        assert result == plaintext

    def test_invalid_key_length(self):
        """A key that is not 64 hex characters should raise ValueError."""
        with pytest.raises(ValueError):
            encrypt("test", "short_key")
        with pytest.raises(ValueError):
            decrypt("some_ciphertext", "abc")
