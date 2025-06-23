"""
JWT helpers - Phase 1 only stubs; full OAuth flow arrives in Phase 2.
"""

from datetime import datetime, timedelta
from typing import Any, Union, Protocol, Dict

from jose import jwt

from core.config import settings

Algorithm = "HS256"


def create_access_token(
    subject: Union[str, dict[str, Any]],
    expires_delta: Union[timedelta, None] = None,
) -> str:
    if isinstance(subject, dict):
        to_encode: Dict[str, Any] = subject.copy()
    else:
        to_encode = {"sub": subject}

    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=Algorithm)
    return encoded_jwt
