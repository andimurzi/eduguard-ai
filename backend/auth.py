"""Autentikasi: bcrypt + JWT, peran dibaca dari database pada setiap permintaan."""
import os
import time
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, Header, HTTPException
from sqlalchemy import text

from database import engine

SECRET = os.getenv("JWT_SECRET", "")


def hash_pw(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


def cek_pw(p: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(p.encode(), h.encode())
    except ValueError:
        return False


DUMMY = hash_pw("dummy-agar-waktu-respons-sama")


def buat_token(username: str, role: str) -> str:
    return jwt.encode({"sub": username, "role": role, "exp": int(time.time()) + 8 * 3600}, SECRET, "HS256")


def current_user(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Anda belum masuk.")
    try:
        data = jwt.decode(authorization[7:], SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Sesi tidak valid atau sudah berakhir.")
    with engine.connect() as c:
        u = c.execute(text("SELECT id,username,nidn,nama,role,aktif FROM users WHERE username=:u"),
                      {"u": data["sub"]}).mappings().first()
    if not u or not u["aktif"]:
        raise HTTPException(401, "Akun tidak aktif atau tidak terdaftar.")
    return dict(u)


def butuh(*roles: str):
    def dep(u=Depends(current_user)):
        if u["role"] not in roles:
            raise HTTPException(403, "Anda tidak punya akses ke fitur ini.")
        return u
    return dep
