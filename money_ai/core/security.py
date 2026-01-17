import os
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt, JWTError

PWD_CONTEXT = CryptContext(schemes=["bcrypt"], deprecated="auto")

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALG = "HS256"
JWT_EXPIRE_MIN = int(os.getenv("JWT_EXPIRE_MIN", "43200"))  # 30 días

def hash_password(pw: str) -> str:
    return PWD_CONTEXT.hash(pw)

def verify_password(pw: str, pw_hash: str) -> bool:
    return PWD_CONTEXT.verify(pw, pw_hash)

def create_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MIN),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def decode_token(token: str) -> int:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        return int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise ValueError("Invalid token")
