"""
vault_security.py
=================
At-rest encryption for sensitive swarm vault files.

Uses Fernet (AES-128-CBC + HMAC) from the cryptography library.
If cryptography is not installed, falls back to plaintext with a loud warning.

Encrypted files get a .vault extension. The key is stored separately in
a file with restricted permissions (Windows: only current user).
"""
from __future__ import annotations

import os
import json
import base64
from pathlib import Path
from typing import Optional

VAULT_KEY_PATH = Path(__file__).parent.parent.parent / "tools" / ".vault_key"
SENSITIVE_PATTERNS = ["api_key", "secret", "password", "token", "private_key", "sk_live", "sk_test"]


def _get_fernet():
    try:
        from cryptography.fernet import Fernet
        return Fernet
    except ImportError:
        return None


def _get_or_create_key() -> bytes:
    """Load existing key or generate a new one."""
    if VAULT_KEY_PATH.exists():
        key = VAULT_KEY_PATH.read_bytes()
        # Strip any trailing whitespace/newlines
        key = key.strip()
        # Validate key length (Fernet keys are 32 bytes base64-encoded = 44 chars)
        try:
            decoded = base64.urlsafe_b64decode(key + b"=" * (-len(key) % 4))
        except Exception:
            decoded = b""
        if len(decoded) != 32:
            raise RuntimeError(
                f"Invalid vault key in {VAULT_KEY_PATH}. Delete it to auto-regenerate."
            )
        return key

    Fernet = _get_fernet()
    if Fernet is None:
        raise RuntimeError("cryptography library not installed. Run: pip install cryptography")

    key = Fernet.generate_key()
    VAULT_KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    VAULT_KEY_PATH.write_bytes(key)

    # Restrict permissions on Windows
    try:
        os.system(f'icacls "{VAULT_KEY_PATH}" /inheritance:r /grant:r "%USERNAME%:R" >nul 2>&1')
    except Exception:
        pass

    return key


def _vault_path(path: Path) -> Path:
    return path.with_suffix(path.suffix + ".vault")


def _plaintext_path(path: Path) -> Path:
    return path.with_suffix(path.suffix + ".plaintext")


def encrypt_json(data: dict, path: Path) -> Path:
    """Encrypt a dict and write it to path with .vault extension.

    Deletes any existing plaintext file at *path* to prevent credential leakage.
    """
    Fernet = _get_fernet()
    if Fernet is None:
        # Fallback: write plaintext with warning marker
        plain_path = _plaintext_path(path)
        plain_path.write_text(
            json.dumps({"__WARNING__": "ENCRYPTION_UNAVAILABLE", "data": data}, indent=2),
            encoding="utf-8",
        )
        # Remove stale vault so load logic prefers the new plaintext fallback
        _vault_path(path).unlink(missing_ok=True)
        return plain_path

    key = _get_or_create_key()
    f = Fernet(key)
    plaintext = json.dumps(data).encode("utf-8")
    ciphertext = f.encrypt(plaintext)

    vault_path = _vault_path(path)
    vault_path.write_bytes(ciphertext)

    # Hardening: remove any leaked plaintext versions of the same logical file
    path.unlink(missing_ok=True)
    _plaintext_path(path).unlink(missing_ok=True)

    return vault_path


def decrypt_json(path: Path) -> Optional[dict]:
    """Decrypt a .vault file back to a dict."""
    if not path.exists():
        return None

    Fernet = _get_fernet()
    if Fernet is None:
        raise RuntimeError("cryptography library not installed. Cannot decrypt vault.")

    key = _get_or_create_key()
    f = Fernet(key)
    ciphertext = path.read_bytes()
    plaintext = f.decrypt(ciphertext)
    return json.loads(plaintext.decode("utf-8"))


def is_sensitive(data: dict) -> bool:
    """Heuristic: does this dict contain sensitive credentials?"""
    text = json.dumps(data).lower()
    return any(p in text for p in SENSITIVE_PATTERNS)


def secure_save(data: dict, path: Path, force_encrypt: bool = False) -> Path:
    """Save a dict. Encrypts automatically if sensitive data is detected.

    Removes stale encrypted/plaintext siblings so load logic is unambiguous.
    """
    if force_encrypt or is_sensitive(data):
        return encrypt_json(data, path)

    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    # Hardening: remove stale encrypted/plaintext siblings
    _vault_path(path).unlink(missing_ok=True)
    _plaintext_path(path).unlink(missing_ok=True)
    return path


def secure_load(path: Path) -> Optional[dict]:
    """Load a dict. Handles both encrypted .vault and plaintext."""
    vault_path = _vault_path(path)
    if vault_path.exists():
        return decrypt_json(vault_path)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    # Fallback for when cryptography was unavailable at save time
    plain_path = _plaintext_path(path)
    if plain_path.exists():
        raw = json.loads(plain_path.read_text(encoding="utf-8"))
        return raw.get("data", raw)
    return None
