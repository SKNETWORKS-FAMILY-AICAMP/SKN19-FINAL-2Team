# ============================================================================
# backend/agent/auth.py "BFF -> Backend 요청 검증 + JWT 토큰 발급"
# ============================================================================

import os
from dataclasses import dataclass
from fastapi import Header, HTTPException, Request
from typing import Optional
from jose import jwt, JWTError

@dataclass
class RequestIdentity:
    user_id: Optional[int]
    role: str
    user_mode: str

def _parse_int(value: Optional[str]) -> Optional[int]:
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None

def _decode_jwt(token: str):
    secret = os.getenv("SECRET_KEY")
    algorithm = os.getenv("ALGORITHM", "HS256")
    if not secret:
        raise HTTPException(status_code=500, detail="SECRET_KEY is missing")
    return jwt.decode(token, secret, algorithms=[algorithm])

def get_identity(
    request: Request,
    x_scentence_user_id: Optional[str] = Header(None),
    x_scentence_role: Optional[str] = Header(None),
    x_scentence_user_mode: Optional[str] = Header(None),
    x_scentence_internal_secret: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
) -> RequestIdentity:
    expected_secret = os.getenv("INTERNAL_REQUEST_SECRET")

    # 1) BFF 요청 (Next.js -> Backend)
    if expected_secret and x_scentence_internal_secret == expected_secret and x_scentence_user_id:
        return RequestIdentity(
            user_id=_parse_int(x_scentence_user_id),
            role=(x_scentence_role or "USER").upper(),
            user_mode=(x_scentence_user_mode or "BEGINNER").upper(),
        )

    # 2) 앱 요청 (JWT)
    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
        try:
            payload = _decode_jwt(token)
            return RequestIdentity(
                user_id=_parse_int(str(payload.get("sub"))),
                role=(payload.get("role") or "USER").upper(),
                user_mode=(payload.get("user_mode") or "BEGINNER").upper(),
            )
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")

    # 3) 게스트
    return RequestIdentity(user_id=None, role="USER", user_mode="BEGINNER")

def require_authenticated(identity: RequestIdentity):
    if not identity.user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    return identity

def require_admin(identity: RequestIdentity):
    require_authenticated(identity)
    if identity.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin required")
    return identity

def require_member_match(member_id: int, identity: RequestIdentity):
    require_authenticated(identity)
    if identity.user_id != member_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return identity
