"""
Encryption service for secure file storage.
GDPR-compliant encryption at rest using AES-256-GCM.
"""

import os
import base64
from pathlib import Path
from typing import Optional, Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from loguru import logger

from app.core.config import settings


class EncryptionService:
    """Service for encrypting and decrypting files."""

    NONCE_SIZE = 12  # 96 bits for GCM
    KEY_SIZE = 32  # 256 bits for AES-256
    SALT_SIZE = 16  # 128 bits

    def __init__(self):
        self._master_key: Optional[bytes] = None

    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """Derive encryption key from password using PBKDF2."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=self.KEY_SIZE,
            salt=salt,
            iterations=480000,  # OWASP recommendation for 2023+
        )
        return kdf.derive(password.encode())

    def _get_master_key(self) -> bytes:
        """Get or derive the master encryption key."""
        if self._master_key is None:
            # Use fixed salt for master key (stored securely in production)
            master_salt = b"VoxDocsMasterSalt"[:self.SALT_SIZE]
            self._master_key = self._derive_key(settings.MASTER_KEY, master_salt)
        return self._master_key

    def encrypt_data(self, data: bytes) -> Tuple[bytes, bytes, bytes]:
        """
        Encrypt data using AES-256-GCM.

        Returns:
            Tuple of (encrypted_data, nonce, salt)
        """
        # Generate random salt and nonce
        salt = os.urandom(self.SALT_SIZE)
        nonce = os.urandom(self.NONCE_SIZE)

        # Derive key from master key with salt
        key = self._derive_key(
            base64.b64encode(self._get_master_key()).decode(),
            salt
        )

        # Encrypt
        aesgcm = AESGCM(key)
        encrypted_data = aesgcm.encrypt(nonce, data, None)

        return encrypted_data, nonce, salt

    def decrypt_data(self, encrypted_data: bytes, nonce: bytes, salt: bytes) -> bytes:
        """
        Decrypt data using AES-256-GCM.

        Args:
            encrypted_data: The encrypted data
            nonce: The nonce used during encryption
            salt: The salt used for key derivation

        Returns:
            Decrypted data
        """
        # Derive the same key
        key = self._derive_key(
            base64.b64encode(self._get_master_key()).decode(),
            salt
        )

        # Decrypt
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, encrypted_data, None)

    def encrypt_file(self, input_path: Path, output_path: Optional[Path] = None) -> Path:
        """
        Encrypt a file and save it to the encrypted directory.

        Args:
            input_path: Path to the file to encrypt
            output_path: Optional output path. If not provided, uses encrypted directory.

        Returns:
            Path to the encrypted file
        """
        if output_path is None:
            output_path = settings.ENCRYPTED_DIR / f"{input_path.stem}.enc"

        logger.debug(f"Encrypting file: {input_path}")

        # Read the file
        with open(input_path, "rb") as f:
            data = f.read()

        # Encrypt
        encrypted_data, nonce, salt = self.encrypt_data(data)

        # Write encrypted file with metadata header
        # Format: [salt (16 bytes)][nonce (12 bytes)][encrypted_data]
        with open(output_path, "wb") as f:
            f.write(salt)
            f.write(nonce)
            f.write(encrypted_data)

        logger.info(f"File encrypted: {output_path}")
        return output_path

    def decrypt_file(self, encrypted_path: Path, output_path: Optional[Path] = None) -> Path:
        """
        Decrypt a file.

        Args:
            encrypted_path: Path to the encrypted file
            output_path: Optional output path. If not provided, uses temp directory.

        Returns:
            Path to the decrypted file
        """
        if output_path is None:
            output_path = Path("/tmp") / f"decrypted_{encrypted_path.stem}"

        logger.debug(f"Decrypting file: {encrypted_path}")

        # Read encrypted file
        with open(encrypted_path, "rb") as f:
            salt = f.read(self.SALT_SIZE)
            nonce = f.read(self.NONCE_SIZE)
            encrypted_data = f.read()

        # Decrypt
        decrypted_data = self.decrypt_data(encrypted_data, nonce, salt)

        # Write decrypted file
        with open(output_path, "wb") as f:
            f.write(decrypted_data)

        logger.info(f"File decrypted: {output_path}")
        return output_path

    def secure_delete(self, file_path: Path):
        """
        Securely delete a file by overwriting with random data.
        """
        if not file_path.exists():
            return

        # Get file size
        file_size = file_path.stat().st_size

        # Overwrite with random data multiple times
        for _ in range(3):
            with open(file_path, "wb") as f:
                f.write(os.urandom(file_size))

        # Delete the file
        file_path.unlink()
        logger.info(f"File securely deleted: {file_path}")


# Global service instance
encryption_service = EncryptionService()


# Helper functions for direct use
async def encrypt_file(data: bytes, filename: str) -> Tuple[str, int]:
    """
    Encrypt file data and save to encrypted directory.

    Args:
        data: File data to encrypt
        filename: Filename to save as

    Returns:
        Tuple of (encrypted_filename, file_size)
    """
    import uuid
    from pathlib import Path

    # Generate unique encrypted filename
    unique_id = str(uuid.uuid4())[:8]
    encrypted_filename = f"{Path(filename).stem}_{unique_id}.enc"
    encrypted_path = settings.ENCRYPTED_DIR / encrypted_filename

    # Ensure directory exists
    settings.ENCRYPTED_DIR.mkdir(parents=True, exist_ok=True)

    # Encrypt data
    encrypted_data, nonce, salt = encryption_service.encrypt_data(data)

    # Write encrypted file with metadata header
    # Format: [salt (16 bytes)][nonce (12 bytes)][encrypted_data]
    with open(encrypted_path, "wb") as f:
        f.write(salt)
        f.write(nonce)
        f.write(encrypted_data)

    file_size = len(data)
    logger.info(f"File encrypted: {encrypted_filename} ({file_size} bytes)")

    return encrypted_filename, file_size


async def decrypt_file(encrypted_filename: str) -> bytes:
    """
    Decrypt a file from the encrypted directory.

    Args:
        encrypted_filename: Name of the encrypted file

    Returns:
        Decrypted file data
    """
    encrypted_path = settings.ENCRYPTED_DIR / encrypted_filename

    if not encrypted_path.exists():
        raise FileNotFoundError(f"Encrypted file not found: {encrypted_filename}")

    # Read encrypted file
    with open(encrypted_path, "rb") as f:
        salt = f.read(EncryptionService.SALT_SIZE)
        nonce = f.read(EncryptionService.NONCE_SIZE)
        encrypted_data = f.read()

    # Decrypt
    decrypted_data = encryption_service.decrypt_data(encrypted_data, nonce, salt)

    logger.info(f"File decrypted: {encrypted_filename}")
    return decrypted_data

