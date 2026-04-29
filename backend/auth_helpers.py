"""
Shared authentication helpers - avoids circular imports between main.py and bom_routes.py
"""
import os
import bcrypt
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from models import get_db, InternalUser, AuditLog, SessionLocal

JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY = int(os.getenv("JWT_EXPIRY", "3600"))

security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False


def create_jwt_token(user_id: int, username: str, role: str) -> str:
    expire = datetime.utcnow() + timedelta(seconds=JWT_EXPIRY)
    payload = {"user_id": user_id, "username": username, "role": role, "exp": expire}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: SessionLocal = Depends(get_db)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_jwt_token(credentials.credentials)
    user = db.query(InternalUser).filter(InternalUser.id == payload["user_id"]).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


def log_audit(db, user_id: int, action: str, entity_type: str, entity_id: int = None, old_value: dict = None, new_value: dict = None, ip_address: str = None):
    audit = AuditLog(
        user_id=user_id, action=action, entity_type=entity_type,
        entity_id=entity_id,
        old_value=str(old_value) if old_value else None,
        new_value=str(new_value) if new_value else None,
        ip_address=ip_address
    )
    db.add(audit)
    db.commit()
