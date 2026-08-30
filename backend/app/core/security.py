import os
import hmac
import hashlib
import base64
import json
import time
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.enums import UserRole
from app.db.session import get_db
from app.models.entities import User

logger = logging.getLogger(__name__)

security_scheme = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    """NIST-compliant PBKDF2-HMAC-SHA256 password hashing."""
    salt = os.urandom(16)
    hashed = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return f"{salt.hex()}:{hashed.hex()}"

def verify_password(plain_password: str, hashed_password_str: str) -> bool:
    """Verifies plain password against salt:hash format securely."""
    try:
        parts = hashed_password_str.split(':')
        if len(parts) != 2:
            return False
        salt = bytes.fromhex(parts[0])
        expected_hash = bytes.fromhex(parts[1])
        computed_hash = hashlib.pbkdf2_hmac('sha256', plain_password.encode('utf-8'), salt, 100000)
        return hmac.compare_digest(computed_hash, expected_hash)
    except Exception as e:
        logger.error(f"Error verifying password: {e}")
        return False

def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')

def _base64url_decode(data: str) -> bytes:
    padding = '=' * (4 - (len(data) % 4))
    return base64.urlsafe_b64decode(data + padding)

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Dependency-free HMAC-SHA256 JWT access token generator."""
    header = {"alg": "HS256", "typ": "JWT"}
    header_json = json.dumps(header, separators=(',', ':')).encode('utf-8')
    header_b64 = _base64url_encode(header_json)

    payload = data.copy()
    now_ts = int(time.time())
    exp_ts = now_ts + (int(expires_delta.total_seconds()) if expires_delta else 86400) # 24h default
    payload.update({"iat": now_ts, "exp": exp_ts})
    payload_json = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    payload_b64 = _base64url_encode(payload_json)

    signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
    secret = settings.SECRET_KEY.encode('utf-8')
    signature = hmac.new(secret, signing_input, hashlib.sha256).digest()
    sig_b64 = _base64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{sig_b64}"

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodes base64 header/payload and verifies HMAC-SHA256 JWT signature and exp."""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts

        signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
        secret = settings.SECRET_KEY.encode('utf-8')
        expected_sig = hmac.new(secret, signing_input, hashlib.sha256).digest()
        actual_sig = _base64url_decode(sig_b64)

        if not hmac.compare_digest(actual_sig, expected_sig):
            return None

        payload_json = _base64url_decode(payload_b64).decode('utf-8')
        payload = json.loads(payload_json)

        if payload.get("exp", 0) < int(time.time()):
            return None # Expired token

        return payload
    except Exception as e:
        logger.warning(f"Failed to decode token: {e}")
        return None

def get_current_user_optional(
    auth: Optional[HTTPAuthorizationCredentials] = Security(security_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Retrieves current user if Authorization: Bearer <JWT> header is provided."""
    if not auth or not auth.credentials:
        return None

    payload = decode_access_token(auth.credentials)
    if not payload or "sub" not in payload:
        return None

    user_id = payload["sub"]
    return db.query(User).filter(User.id == user_id).first()

def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Security(security_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Requires valid JWT Bearer token and returns authenticated User or 401."""
    user = get_current_user_optional(auth, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing, expired or invalid Authorization Bearer token.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user

def require_roles(allowed_roles: list[UserRole]):
    """RBAC dependency requiring specific user roles or raising 403 Forbidden."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role.value}' is not authorized to perform this operation. Allowed: {[r.value for r in allowed_roles]}."
            )
        return current_user
    return role_checker
