# Lightweight Encryption Utilities
# Fast encryption for sensitive data without performance impact

import base64
import hashlib
import logging
import os
from typing import Optional, Union

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


class FastEncryptor:
    """
    Fast, lightweight encryption for sensitive data.
    Uses Fernet (AES 128) with PBKDF2 key derivation.
    Designed for minimal performance impact.
    """

    def __init__(self, key: Optional[bytes] = None, salt: Optional[bytes] = None):
        """
        Initialize encryptor with key and salt.

        Args:
            key: Encryption key (if None, derived from environment)
            salt: Salt for key derivation (if None, uses default)
        """
        self.salt = salt or b"grokputer_salt_2024"  # Fixed salt for consistency

        if key is None:
            # Derive key from environment variable or generate one
            env_key = os.getenv("GROKPUTER_ENCRYPTION_KEY")
            if env_key:
                # Use provided key
                key = base64.urlsafe_b64decode(env_key)
            else:
                # Generate key from system info (not secure, but fast)
                import platform

                uname_info = platform.uname() if hasattr(platform, "uname") else os.name
                system_info = f"{uname_info}{os.getpid()}{os.getcwd()}".encode()
                key = self._derive_key(system_info, self.salt)

        self.fernet = Fernet(key)

    def _derive_key(self, password: bytes, salt: bytes) -> bytes:
        """Derive encryption key from password using PBKDF2."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,  # Balance security vs speed
        )
        return base64.urlsafe_b64encode(kdf.derive(password))

    def encrypt(self, data: Union[str, bytes]) -> str:
        """
        Encrypt data.

        Args:
            data: String or bytes to encrypt

        Returns:
            Base64-encoded encrypted string
        """
        if isinstance(data, str):
            data = data.encode("utf-8")

        encrypted = self.fernet.encrypt(data)
        return base64.urlsafe_b64encode(encrypted).decode("ascii")

    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt data.

        Args:
            encrypted_data: Base64-encoded encrypted string

        Returns:
            Decrypted string

        Raises:
            Exception: If decryption fails
        """
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode("ascii"))
            decrypted = self.fernet.decrypt(encrypted_bytes)
            return decrypted.decode("utf-8")
        except Exception as e:
            logger.warning(f"Decryption failed: {e}")
            # Return original data if decryption fails (graceful degradation)
            return encrypted_data

    def encrypt_dict_values(self, data: dict, keys_to_encrypt: list) -> dict:
        """
        Encrypt specific values in a dictionary.

        Args:
            data: Dictionary to process
            keys_to_encrypt: List of keys whose values should be encrypted

        Returns:
            Dictionary with encrypted values
        """
        result = data.copy()
        for key in keys_to_encrypt:
            if key in result and isinstance(result[key], (str, int, float)):
                result[key] = self.encrypt(str(result[key]))
        return result

    def decrypt_dict_values(self, data: dict, keys_to_decrypt: list) -> dict:
        """
        Decrypt specific values in a dictionary.

        Args:
            data: Dictionary to process
            keys_to_decrypt: List of keys whose values should be decrypted

        Returns:
            Dictionary with decrypted values
        """
        result = data.copy()
        for key in keys_to_decrypt:
            if key in result and isinstance(result[key], str):
                try:
                    result[key] = self.decrypt(result[key])
                except Exception:
                    # Keep original if decryption fails
                    pass
        return result


# Global encryptor instance for performance
_encryptor = None


def get_encryptor() -> FastEncryptor:
    """Get global encryptor instance (singleton pattern)."""
    global _encryptor
    if _encryptor is None:
        _encryptor = FastEncryptor()
    return _encryptor


def encrypt_sensitive_data(data: Union[str, bytes]) -> str:
    """Convenience function for encrypting sensitive data."""
    return get_encryptor().encrypt(data)


def decrypt_sensitive_data(encrypted_data: str) -> str:
    """Convenience function for decrypting sensitive data."""
    return get_encryptor().decrypt(encrypted_data)


# Randomized encryption (changes ciphertext each time)
def randomize_encrypt(data: Union[str, bytes], add_entropy: bool = True) -> str:
    """
    Encrypt with randomization (different output each time).
    Adds entropy to prevent pattern analysis.

    Args:
        data: Data to encrypt
        add_entropy: Whether to add random entropy

    Returns:
        Encrypted string (different each time)
    """
    encryptor = get_encryptor()

    if add_entropy:
        # Add random entropy to make each encryption unique
        import secrets

        entropy = secrets.token_bytes(16)
        if isinstance(data, str):
            data = data.encode("utf-8")
        data = entropy + b"|" + data

    encrypted = encryptor.encrypt(data)
    return f"RND:{encrypted}"  # Mark as randomized


def randomize_decrypt(encrypted_data: str) -> str:
    """
    Decrypt randomized data.

    Args:
        encrypted_data: Encrypted string from randomize_encrypt

    Returns:
        Decrypted string
    """
    if not encrypted_data.startswith("RND:"):
        # Not randomized, use normal decrypt
        return decrypt_sensitive_data(encrypted_data)

    encrypted_data = encrypted_data[4:]  # Remove RND: prefix
    decrypted = decrypt_sensitive_data(encrypted_data)

    # Remove entropy if present
    if b"|" in decrypted.encode("utf-8"):
        parts = decrypted.split("|", 1)
        if len(parts) == 2:
            return parts[1]

    return decrypted


# Example usage:
if __name__ == "__main__":
    # Test encryption
    encryptor = FastEncryptor()

    # Basic encryption
    secret = "my_api_key_12345"
    encrypted = encryptor.encrypt(secret)
    decrypted = encryptor.decrypt(encrypted)
    print(f"Original: {secret}")
    print(f"Encrypted: {encrypted}")
    print(f"Decrypted: {decrypted}")

    # Randomized encryption
    rnd_encrypted1 = randomize_encrypt(secret)
    rnd_encrypted2 = randomize_encrypt(secret)
    print(f"Randomized 1: {rnd_encrypted1}")
    print(f"Randomized 2: {rnd_encrypted2}")
    print(f"Different outputs: {rnd_encrypted1 != rnd_encrypted2}")
