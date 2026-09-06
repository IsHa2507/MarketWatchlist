from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordBearer
from fastapi import Request
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import get_db
from app.core.security import decode_token, hash_password
from app.models.user import User

security = HTTPBearer()

# Optional security — does NOT raise 403 when the Authorization header is absent
security_optional = HTTPBearer(auto_error=False)

# ── Shared demo user ──────────────────────────────────────────────────────────
# When no token is provided, requests are scoped to this auto-created user.
# Authentication is preserved: real tokens always take precedence.
DEMO_EMAIL    = "demo@marketpulse.app"
DEMO_PASSWORD = "demo123"


def _get_or_create_demo_user(db: Session) -> User:
    """
    Return the demo user, creating it if it doesn't exist yet.
    Called only when the request carries no JWT.
    """
    user = db.query(User).filter(User.email == DEMO_EMAIL).first()
    if user:
        return user
    user = User(
        email=DEMO_EMAIL,
        password_hash=hash_password(DEMO_PASSWORD),
        full_name="Demo User",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    Strict auth dependency — requires a valid JWT.
    Used by auth-sensitive routes (register, login, /auth/me).
    """
    token = credentials.credentials
    user_id = decode_token(token)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional),
    db: Session = Depends(get_db),
) -> User:
    """
    Optional auth dependency — used by dashboard and watchlist routes.

    Behaviour:
      - Valid JWT present  → return the real user (normal authenticated flow)
      - No JWT / invalid   → return the shared demo user (auto-created)

    This allows the frontend to open the dashboard without logging in,
    while preserving full authentication when a token IS provided.
    """
    if credentials and credentials.credentials:
        user_id = decode_token(credentials.credentials)
        if user_id:
            user = db.query(User).filter(User.id == int(user_id)).first()
            if user:
                return user
        # Token present but invalid — still fall through to demo user
        # (avoids hard 401 for demo/bypass tokens the frontend may send)

    return _get_or_create_demo_user(db)
