"""
Symmetric encryption helper ‑ uses SECRET_KEY as the base material.
"""
import base64
import hashlib

from cryptography.fernet import Fernet

from core.config import settings

# derive 32‑byte key from SECRET_KEY (not suitable for HSM‑grade needs,
# but fine for this demo)
fernet_key = base64.urlsafe_b64encode(
    hashlib.sha256(settings.SECRET_KEY.encode()).digest()
)
fernet = Fernet(fernet_key)


def encrypt(data: str) -> str:
    return fernet.encrypt(data.encode()).decode()


def decrypt(token: str) -> str:
    return fernet.decrypt(token.encode()).decode()
