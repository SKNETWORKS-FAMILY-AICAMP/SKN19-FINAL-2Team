# ============================================================================
# backend/routers/auth.py "JWT 토큰 발급 라우터"
# ============================================================================

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from passlib.context import CryptContext
import httpx
from jose import jwt
import os
from datetime import datetime, timedelta

from agent.database import get_member_db_connection, release_member_db_connection

router = APIRouter(prefix="/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

class LocalTokenRequest(BaseModel):
    email: str
    password: str

class KakaoTokenRequest(BaseModel):
    kakao_access_token: str

def _issue_token(member_id: int, role: str, user_mode: str):
    secret = os.getenv("SECRET_KEY")
    algorithm = os.getenv("ALGORITHM", "HS256")
    expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

    payload = {
        "sub": str(member_id),
        "role": role,
        "user_mode": user_mode,
        "exp": datetime.utcnow() + timedelta(minutes=expire_minutes),
    }
    token = jwt.encode(payload, secret, algorithm=algorithm)
    return {"access_token": token, "token_type": "bearer", "expires_in": expire_minutes * 60}

@router.post("/token")
def issue_token_local(req: LocalTokenRequest):
    conn = get_member_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT member_id, pwd_hash, role_type, user_mode
            FROM tb_member_basic_m
            WHERE login_id=%s AND join_channel='LOCAL'
            """,
            (req.email,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        member_id, pwd_hash, role_type, user_mode = row
        if not pwd_hash or not pwd_context.verify(req.password, pwd_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        role = (role_type or "USER").upper()
        mode = (user_mode or "BEGINNER").upper()
        return _issue_token(member_id, role, mode)
    finally:
        cur.close()
        release_member_db_connection(conn)

@router.post("/token/kakao")
def issue_token_kakao(req: KakaoTokenRequest):
    headers = {"Authorization": f"Bearer {req.kakao_access_token}"}
    res = httpx.get("https://kapi.kakao.com/v2/user/me", headers=headers, timeout=10.0)
    if res.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid Kakao token")

    data = res.json()
    kakao_id = str(data.get("id"))
    if not kakao_id:
        raise HTTPException(status_code=401, detail="Kakao id missing")

    conn = get_member_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT member_id
            FROM tb_member_auth_t
            WHERE provider='KAKAO' AND provider_user_id=%s
            """,
            (kakao_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Kakao user not registered")
        member_id = row[0]

        cur.execute(
            "SELECT role_type, user_mode FROM tb_member_basic_m WHERE member_id=%s",
            (member_id,),
        )
        row2 = cur.fetchone()
        role = (row2[0] or "USER").upper()
        mode = (row2[1] or "BEGINNER").upper()

        return _issue_token(member_id, role, mode)
    finally:
        cur.close()
        release_member_db_connection(conn)
