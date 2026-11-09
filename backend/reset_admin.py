from getpass import getpass
from sqlalchemy import text
from auth import hash_pw
from database import engine

username = input("Username admin yang direset: ").strip()
pw = getpass("Kata sandi baru (min. 8 karakter): ")
assert len(pw) >= 8, "Kata sandi terlalu pendek"

with engine.begin() as c:
    r = c.execute(text("UPDATE users SET password_hash=:h, gagal_login=0, terkunci_hingga=NULL, aktif=1 "
                       "WHERE username=:u AND role='admin'"), {"h": hash_pw(pw), "u": username})
print("Berhasil direset." if r.rowcount else "Username admin tidak ditemukan.")