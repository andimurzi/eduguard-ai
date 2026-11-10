"""API EduGuard AI: login terdata (MySQL) + prediksi risiko + penjelasan SHAP.



Jalankan:  uvicorn main:app --reload --port 8000

Web & API satu alamat:  http://localhost:8000   (dokumentasi: /docs)

"""

import os

from datetime import datetime, timedelta

from typing import Annotated, List, Literal, Optional



import joblib

import numpy as np

import pandas as pd

import shap

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response

from fastapi.middleware.cors import CORSMiddleware

from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel, Field

from sqlalchemy import text



from auth import DUMMY, SECRET, buat_token, butuh, cek_pw, hash_pw

from database import engine

from features import FITUR, buat_fitur

from pdf_export import pdf_daftar, pdf_detail



if len(SECRET) < 32:

    raise RuntimeError("ju6i7Ot9XbGaOf3yEfIHJZ1PjvMiW8u21QlXmHDefdV5KBJkceFmp715G0ZUaYUt")



BASE = os.path.dirname(os.path.abspath(__file__))

MAX_GAGAL, KUNCI_MENIT = 5, 5



app = FastAPI(title="EduGuard AI API", version="2.0")

app.add_middleware(CORSMiddleware, allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:8000").split(","),

                   allow_methods=["*"], allow_headers=["*"])



bundle = joblib.load(os.path.join(BASE, "model.joblib"))

model = bundle["model"]

explainer = shap.TreeExplainer(model)

KELAS = list(model.classes_)  # ['rendah', 'sedang', 'tinggi']

LVL = {"rendah": "lo", "sedang": "mid", "tinggi": "hi"}

LABEL_LVL = {"hi": "tinggi", "mid": "sedang", "lo": "rendah"}





# ---------- skema data ----------

class LoginIn(BaseModel):

    peran: Literal["admin", "dosen"]                      # tab yang dipilih di halaman login

    identitas: str = Field(min_length=1, max_length=50)   # admin: username, dosen: NIDN

    password: str = Field(min_length=1, max_length=128)





class Akademik(BaseModel):

    ips: List[Annotated[float, Field(ge=0, le=4)]] = Field(min_length=1, max_length=14)

    hadir: float = Field(ge=0, le=100)

    tugas: float = Field(ge=0, le=100)

    sks_gagal: float = Field(ge=0, le=200)

    ukt: int = Field(ge=0, le=1)





class MhsBaru(Akademik):

    dosen_pa_id: Optional[int] = None   # hanya dipakai admin; untuk dosen otomatis dirinya sendiri

    nim: str = Field(pattern=r"^\d{6,20}$")

    nama: str = Field(min_length=2, max_length=100)

    prodi: str = Field(min_length=2, max_length=80)

    smt: int = Field(ge=1, le=14)





class Simulasi(BaseModel):

    hadir: Optional[float] = Field(None, ge=0, le=100)

    tugas: Optional[float] = Field(None, ge=0, le=100)

    sks_gagal: Optional[float] = Field(None, ge=0, le=200)

    ips_terakhir: Optional[float] = Field(None, ge=0, le=4)





class UserBaru(BaseModel):

    role: Literal["admin", "dosen"]

    nama: str = Field(min_length=2, max_length=100)

    password: str = Field(min_length=8, max_length=128)

    username: Optional[str] = Field(None, pattern=r"^[a-zA-Z0-9._-]{3,30}$")  # wajib untuk admin

    nidn: Optional[str] = Field(None, pattern=r"^\d{10}$")                     # wajib untuk dosen





class PenugasanPA(BaseModel):

    dosen_pa_id: Optional[int] = None   # None = lepas penugasan


class PenugasanMassal(PenugasanPA):

    nim: List[str] = Field(min_length=1, max_length=500)


class UserUbah(BaseModel):

    aktif: Optional[bool] = None

    password: Optional[str] = Field(None, min_length=8, max_length=128)





# ---------- mesin AI ----------

def ke_fitur(d: dict) -> dict:

    ips = d["ips"]

    last = ips[-1]

    prev = sum(ips[:-1]) / (len(ips) - 1) if len(ips) > 1 else last

    return {"ipk": round(sum(ips) / len(ips), 2), "ips_terakhir": last, "ips_sebelumnya": prev,

            "hadir": d["hadir"], "tugas": d["tugas"], "sks_gagal": d["sks_gagal"], "ukt": int(d["ukt"])}





def nama_faktor(k: str, m: dict) -> str:

    return {"ipk": f"IPK rendah ({m['ipk']:.2f})", "hadir": f"Kehadiran rendah ({m['hadir']:.0f}%)",

            "tugas": f"Nilai tugas rendah ({m['tugas']:.0f})", "sks_gagal": f"{m['sks_gagal']:.0f} SKS tidak lulus",

            "tren": f"IPS menurun ({m['ips_sebelumnya']:.2f} ke {m['ips_terakhir']:.2f})",

            "ukt": "Tunggakan UKT"}[k]





def shap_tinggi(X: pd.DataFrame) -> np.ndarray:

    sv = explainer.shap_values(X)  # bentuk keluaran berbeda antar versi shap

    idx = KELAS.index("tinggi")

    return np.asarray(sv[idx]) if isinstance(sv, list) else np.asarray(sv)[:, :, idx]





def narasi(skor: int, lvl: str, faktor: list, d: dict, m: dict) -> str:

    nm = {"hi": "tinggi", "mid": "sedang", "lo": "rendah"}[lvl]

    if not faktor:

        return (f"Risiko akademik {nm} (skor {skor}/100). Tidak ada faktor yang menonjol, "

                "pertahankan kinerja saat ini.")



    top = ", ".join(f["nama"][0].lower() + f["nama"][1:] for f in faktor[:3])

    p = [f"Risiko akademik {nm} dengan skor {skor}/100. Pendorong utama: {top}. "

         f"Intervensi paling berdampak diarahkan ke faktor pertama."]



    # Tren IPS

    ips = d["ips"]

    if len(ips) >= 2:

        selisih = ips[-1] - ips[0]

        rata = sum(ips) / len(ips)

        if selisih <= -0.3:

            p.append(f"IPS menunjukkan tren menurun dari {ips[0]:.2f} menjadi {ips[-1]:.2f} "

                     f"(turun {abs(selisih):.2f} poin) dengan rata-rata {rata:.2f}. Penurunan ini perlu "

                     "ditelusuri, apakah karena beban mata kuliah, kesulitan materi, atau faktor non-akademik.")

        elif selisih >= 0.3:

            p.append(f"IPS membaik dari {ips[0]:.2f} menjadi {ips[-1]:.2f}. "

                     "Pola belajar saat ini sudah berjalan baik dan perlu dipertahankan.")

        else:

            p.append(f"IPS relatif stabil di kisaran {rata:.2f}, belum ada perbaikan maupun penurunan signifikan.")



    # Kehadiran & tugas

    k = []

    if m["hadir"] < 75:

        k.append(f"Kehadiran {m['hadir']:.0f}% berada di bawah batas minimal 75%, sehingga ada risiko "

                 "tidak diizinkan mengikuti ujian akhir.")

    else:

        k.append(f"Kehadiran {m['hadir']:.0f}% sudah memenuhi batas minimal.")

    if m["tugas"] < 70:

        k.append(f"Nilai tugas rata-rata {m['tugas']:.0f} tergolong rendah dan menarik turun nilai akhir.")

    else:

        k.append(f"Nilai tugas rata-rata {m['tugas']:.0f} cukup baik, tetapi masih bisa ditingkatkan.")

    p.append(" ".join(k))



    # SKS & UKT

    k = []

    if m["sks_gagal"] > 0:

        k.append(f"Terdapat {m['sks_gagal']:.0f} SKS tidak lulus. Jika tidak segera diulang, beban semester "

                 "berikutnya bertambah dan kelulusan tepat waktu terancam.")

    if m["ukt"]:

        k.append("Tunggakan UKT dapat menghambat registrasi dan pengisian KRS semester depan.")

    if k:

        p.append(" ".join(k))



    # Dampak

    if lvl == "hi":

        p.append("Tanpa penanganan segera, mahasiswa berpotensi mendapat peringatan akademik dan keterlambatan studi.")

    elif lvl == "mid":

        p.append("Jika dibiarkan, risiko dapat naik ke level tinggi pada semester berikutnya. "

                 "Penanganan sejak dini akan jauh lebih efektif.")

    return "\n\n".join(p)





def prediksi(daftar: List[dict]):

    fitur = [ke_fitur(d) for d in daftar]

    X = buat_fitur(pd.DataFrame(fitur))

    proba, sv, hasil = model.predict_proba(X), shap_tinggi(X), []

    for i, m in enumerate(fitur):

        p = dict(zip(KELAS, proba[i]))

        skor = int(round(100 * (p["tinggi"] + 0.5 * p["sedang"])))

        lvl = LVL[KELAS[int(np.argmax(proba[i]))]]

        kontrib = {f: max(0.0, float(sv[i][j])) for j, f in enumerate(FITUR)}

        total, faktor = sum(kontrib.values()), []

        if total > 0:

            for f, v in sorted(kontrib.items(), key=lambda kv: -kv[1]):

                pts = v / total * skor

                if pts >= 3:

                    faktor.append({"key": {"sks_gagal": "gagal"}.get(f, f), "nama": nama_faktor(f, m), "pts": round(pts, 1)})

        hasil.append({"skor": skor, "lvl": lvl, "yakin": round(float(proba[i].max()), 3),

                      "proba": {k: round(float(v), 3) for k, v in p.items()}, "f": faktor,

                      "narasi": narasi(skor, lvl, faktor, daftar[i], m)})

    return hasil





# ---------- akses data ----------

def ambil_mhs(nim: Optional[str] = None, u: Optional[dict] = None):
    """Ambil mahasiswa. Dosen PA hanya mendapat mahasiswa bimbingannya; admin mendapat semuanya."""
    where, par = [], {}
    if u is not None and u["role"] == "dosen":
        where.append("m.dosen_pa_id=:pa")
        par["pa"] = u["id"]
    if nim:
        where.append("m.nim=:n")
        par["n"] = nim
    w = (" WHERE " + " AND ".join(where)) if where else ""

    with engine.connect() as c:
        rows = [dict(r) for r in c.execute(text(
            "SELECT m.nim,m.nama,m.prodi,m.smt,m.hadir,m.tugas,m.sks_gagal,m.ukt,"
            "m.dosen_pa_id, d.nama AS dosen_pa "
            "FROM mahasiswa m LEFT JOIN users d ON d.id=m.dosen_pa_id" + w + " ORDER BY m.nama"), par).mappings()]
        ips = {}
        for n, v in c.execute(text(
            "SELECT i.nim,i.ips FROM ips_semester i JOIN mahasiswa m ON m.nim=i.nim" + w +
            " ORDER BY i.nim,i.semester"), par):
            ips.setdefault(n, []).append(float(v))

    for r in rows:
        r["ips"] = ips.get(r["nim"], [])
        r["ukt"] = bool(r["ukt"])

    # Semua mahasiswa tetap ditampilkan meskipun belum memiliki riwayat IPS.
    return rows


def cek_dosen(c, dosen_id: Optional[int]):
    """Pastikan id adalah akun dosen yang aktif (None = tanpa dosen PA)."""
    if dosen_id is None:
        return
    if not c.execute(text("SELECT 1 FROM users WHERE id=:i AND role='dosen' AND aktif=1"), {"i": dosen_id}).first():
        raise HTTPException(400, "Dosen PA tidak ditemukan atau tidak aktif.")


# ---------- autentikasi ----------

@app.post("/auth/login")

def login(b: LoginIn, req: Request):

    ip, err, hasil = (req.client.host if req.client else "-"), None, None

    kolom = "nidn" if b.peran == "dosen" else "username"   # dosen masuk dengan NIDN, admin dengan username

    with engine.begin() as c:

        # Filter role ikut di query: NIDN tidak bisa dipakai masuk sebagai admin, dan sebaliknya.

        u = c.execute(text(f"SELECT * FROM users WHERE {kolom}=:i AND role=:r"),

                      {"i": b.identitas.strip(), "r": b.peran}).mappings().first()



        def catat(ok, ket):

            c.execute(text("INSERT INTO login_log(username,ip,berhasil,keterangan) VALUES(:u,:ip,:o,:k)"),

                      {"u": b.identitas.strip()[:50], "ip": ip, "o": int(ok), "k": f"{b.peran}: {ket}"[:100]})



        if u and u["terkunci_hingga"] and u["terkunci_hingga"] > datetime.now():

            catat(False, "akun terkunci")

            err = (429, f"Akun dikunci sementara karena terlalu banyak percobaan. Coba lagi dalam {KUNCI_MENIT} menit.")

        else:

            cocok = cek_pw(b.password, u["password_hash"] if u else DUMMY)  # waktu respons dibuat sama

            if not (u and u["aktif"] and cocok):

                if u and cocok:

                    catat(False, "akun nonaktif")

                elif u:

                    gagal = u["gagal_login"] + 1

                    kunci = datetime.now() + timedelta(minutes=KUNCI_MENIT) if gagal >= MAX_GAGAL else None

                    c.execute(text("UPDATE users SET gagal_login=:g, terkunci_hingga=:k WHERE id=:i"),

                              {"g": 0 if kunci else gagal, "k": kunci, "i": u["id"]})

                    catat(False, "kata sandi salah" + (" (akun dikunci)" if kunci else ""))

                else:

                    catat(False, "akun tidak terdaftar")

                err = (401, "NIDN/username atau kata sandi salah, atau akun tidak aktif.")

            else:

                c.execute(text("UPDATE users SET gagal_login=0, terkunci_hingga=NULL, last_login=NOW() WHERE id=:i"), {"i": u["id"]})

                catat(True, "login berhasil")

                hasil = {"token": buat_token(u["username"], u["role"]),

                         "user": {"username": u["username"], "nidn": u["nidn"], "nama": u["nama"], "role": u["role"]}}

    if err:

        raise HTTPException(*err)

    return hasil





@app.get("/auth/me")

def me(u=Depends(butuh("admin", "dosen"))):

    return {"username": u["username"], "nidn": u["nidn"], "nama": u["nama"], "role": u["role"]}





@app.get("/health")

def health(u=Depends(butuh("admin", "dosen"))):

    return {"status": "ok", "model": bundle.get("nama", "RandomForest"), "metrik": bundle.get("metrik", {})}





# ---------- mahasiswa & prediksi ----------

@app.get("/mahasiswa")
def daftar_mhs(u=Depends(butuh("admin", "dosen"))):
    d = ambil_mhs(u=u)   # dosen: hanya mahasiswa bimbingannya
    # Prediksi hanya dapat dilakukan untuk mahasiswa yang memiliki riwayat IPS.
    ada_ips = [s for s in d if s["ips"]]
    hasil_prediksi = prediksi(ada_ips) if ada_ips else []
    prediksi_per_nim = {
        s["nim"]: p for s, p in zip(ada_ips, hasil_prediksi)
    }
    # Mahasiswa tanpa IPS tetap dikirim ke UI dengan p=None.
    return [{**s, "p": prediksi_per_nim.get(s["nim"])} for s in d]


def _pdf(isi: bytes, nama: str) -> Response:

    return Response(isi, media_type="application/pdf",

                    headers={"Content-Disposition": f'attachment; filename="{nama}"', "Cache-Control": "no-store"})





@app.get("/mahasiswa/export/pdf")

def export_pdf(level: Optional[Literal["hi", "mid", "lo"]] = None, q: Optional[str] = Query(None, max_length=100),

               u=Depends(butuh("admin", "dosen"))):

    """PDF seluruh mahasiswa terprediksi. Filter `level` dan `q` (nama/NIM) sama dengan yang dipakai di halaman Data Mahasiswa."""

    d = ambil_mhs(u=u)

    ada_ips = [s for s in d if s["ips"]]
    hasil_prediksi = prediksi(ada_ips) if ada_ips else []
    data = [{**s, "p": p} for s, p in zip(ada_ips, hasil_prediksi)]

    ket = []

    if level:

        data = [s for s in data if s["p"]["lvl"] == level]

        ket.append(f"risiko {LABEL_LVL[level]}")

    if q and q.strip():

        k = q.strip().lower()

        data = [s for s in data if k in (s["nama"] + s["nim"]).lower()]

        ket.append(f'cari "{q.strip()}"')

    return _pdf(pdf_daftar(data, u["nama"], ", ".join(ket) or ("semua mahasiswa bimbingan" if u["role"] == "dosen" else "semua mahasiswa")),

                f"eduguard-prediksi-{datetime.now():%Y%m%d}.pdf")





@app.get("/mahasiswa/{nim}/pdf")

def detail_pdf(nim: str, u=Depends(butuh("admin", "dosen"))):

    """PDF laporan satu mahasiswa: skor, narasi AI, faktor SHAP, rekomendasi."""

    d = ambil_mhs(nim, u)

    if not d:

        raise HTTPException(404, "Mahasiswa tidak ditemukan.")

    if not d[0]["ips"]:

        raise HTTPException(400, "Mahasiswa belum memiliki riwayat IPS, prediksi belum tersedia.")

    s = {**d[0], "p": prediksi(d)[0]}

    return _pdf(pdf_detail(s, u["nama"]), f"eduguard-{nim}.pdf")





@app.post("/mahasiswa", status_code=201)

def tambah_mhs(m: MhsBaru, u=Depends(butuh("admin", "dosen"))):

    # Dosen PA: mahasiswa baru otomatis menjadi bimbingannya. Admin: boleh memilih dosen PA (atau dikosongkan).
    pa = u["id"] if u["role"] == "dosen" else m.dosen_pa_id

    with engine.begin() as c:

        cek_dosen(c, pa)

        if c.execute(text("SELECT 1 FROM mahasiswa WHERE nim=:n"), {"n": m.nim}).first():

            raise HTTPException(409, "NIM sudah terdaftar.")

        c.execute(text("INSERT INTO mahasiswa(nim,nama,prodi,smt,hadir,tugas,sks_gagal,ukt,dosen_pa_id) VALUES(:n,:nm,:p,:s,:h,:t,:g,:u,:pa)"),

                  {"n": m.nim, "nm": m.nama, "p": m.prodi, "s": m.smt, "h": round(m.hadir), "t": round(m.tugas),

                   "g": round(m.sks_gagal), "u": m.ukt, "pa": pa})

        for k, v in enumerate(m.ips, 1):

            c.execute(text("INSERT INTO ips_semester(nim,semester,ips) VALUES(:n,:k,:v)"), {"n": m.nim, "k": k, "v": v})

    return {"ok": True, "nim": m.nim}





@app.post("/predict")

def predict(a: Akademik, u=Depends(butuh("admin", "dosen"))):

    return prediksi([a.model_dump()])[0]





@app.post("/mahasiswa/{nim}/simulasi")

def simulasi(nim: str, s: Simulasi, u=Depends(butuh("admin", "dosen"))):

    d = ambil_mhs(nim, u)

    if not d:

        raise HTTPException(404, "Mahasiswa tidak ditemukan.")

    d = d[0]

    if not d["ips"]:

        raise HTTPException(400, "Mahasiswa belum memiliki riwayat IPS.")

    d["ips"] = d["ips"][:-1] + [s.ips_terakhir if s.ips_terakhir is not None else d["ips"][-1]]

    for k in ("hadir", "tugas", "sks_gagal"):

        if getattr(s, k) is not None:

            d[k] = getattr(s, k)

    return prediksi([d])[0]





# ---------- manajemen akses (khusus admin) ----------

@app.get("/admin/users")

def daftar_user(u=Depends(butuh("admin"))):

    with engine.connect() as c:

        return [dict(r) for r in c.execute(text(

            "SELECT id,username,nidn,nama,role,aktif,last_login,terkunci_hingga FROM users ORDER BY id")).mappings()]





@app.post("/admin/users", status_code=201)

def buat_user(b: UserBaru, u=Depends(butuh("admin"))):

    if b.role == "dosen":

        if not b.nidn:

            raise HTTPException(400, "NIDN wajib diisi untuk dosen (10 digit angka).")

        username, nidn = b.nidn, b.nidn          # dosen: username otomatis = NIDN

    else:

        if not b.username:

            raise HTTPException(400, "Username wajib diisi untuk admin.")

        username, nidn = b.username, None

    with engine.begin() as c:

        if c.execute(text("SELECT 1 FROM users WHERE username=:u"), {"u": username}).first():

            raise HTTPException(409, "Username sudah dipakai.")

        if nidn and c.execute(text("SELECT 1 FROM users WHERE nidn=:n"), {"n": nidn}).first():

            raise HTTPException(409, "NIDN sudah terdaftar.")

        c.execute(text("INSERT INTO users(username,nidn,nama,role,password_hash) VALUES(:u,:d,:n,:r,:h)"),

                  {"u": username, "d": nidn, "n": b.nama, "r": b.role, "h": hash_pw(b.password)})

    return {"ok": True}





@app.patch("/admin/users/{uid}")

def ubah_user(uid: int, b: UserUbah, u=Depends(butuh("admin"))):

    if b.aktif is False and uid == u["id"]:

        raise HTTPException(400, "Anda tidak dapat menonaktifkan akun sendiri.")

    with engine.begin() as c:

        if not c.execute(text("SELECT 1 FROM users WHERE id=:i"), {"i": uid}).first():

            raise HTTPException(404, "Akun tidak ditemukan.")

        if b.aktif is not None:

            c.execute(text("UPDATE users SET aktif=:a WHERE id=:i"), {"a": int(b.aktif), "i": uid})

        if b.password:

            c.execute(text("UPDATE users SET password_hash=:h, gagal_login=0, terkunci_hingga=NULL WHERE id=:i"),

                      {"h": hash_pw(b.password), "i": uid})

    return {"ok": True}





@app.get("/admin/dosen-pa")

def daftar_dosen_pa(u=Depends(butuh("admin"))):

    """Daftar dosen beserta jumlah mahasiswa bimbingannya, untuk halaman Pembagian Dosen PA."""

    with engine.connect() as c:

        dosen = [dict(r) for r in c.execute(text(

            "SELECT u.id,u.nidn,u.nama,u.aktif,COUNT(m.nim) AS jumlah FROM users u "

            "LEFT JOIN mahasiswa m ON m.dosen_pa_id=u.id WHERE u.role='dosen' "

            "GROUP BY u.id,u.nidn,u.nama,u.aktif ORDER BY u.nama")).mappings()]

        tanpa = c.execute(text("SELECT COUNT(*) FROM mahasiswa WHERE dosen_pa_id IS NULL")).scalar() or 0

    return {"dosen": dosen, "tanpa_dosen": int(tanpa)}


@app.patch("/admin/mahasiswa/{nim}/dosen-pa")

def tetapkan_dosen_pa(nim: str, b: PenugasanPA, u=Depends(butuh("admin"))):

    with engine.begin() as c:

        cek_dosen(c, b.dosen_pa_id)

        r = c.execute(text("UPDATE mahasiswa SET dosen_pa_id=:d WHERE nim=:n"), {"d": b.dosen_pa_id, "n": nim})

        if not c.execute(text("SELECT 1 FROM mahasiswa WHERE nim=:n"), {"n": nim}).first():

            raise HTTPException(404, "Mahasiswa tidak ditemukan.")

    return {"ok": True}


@app.post("/admin/mahasiswa/dosen-pa")

def tetapkan_dosen_pa_massal(b: PenugasanMassal, u=Depends(butuh("admin"))):

    """Tetapkan satu dosen PA untuk banyak mahasiswa sekaligus."""

    with engine.begin() as c:

        cek_dosen(c, b.dosen_pa_id)

        for n in set(b.nim):

            c.execute(text("UPDATE mahasiswa SET dosen_pa_id=:d WHERE nim=:n"), {"d": b.dosen_pa_id, "n": n})

    return {"ok": True, "jumlah": len(set(b.nim))}


@app.get("/admin/log")

def log_akses(u=Depends(butuh("admin"))):

    with engine.connect() as c:

        return [dict(r) for r in c.execute(text(

            "SELECT waktu,username,ip,berhasil,keterangan FROM login_log ORDER BY id DESC LIMIT 100")).mappings()]





# Frontend dilayani dari alamat yang sama (harus paling akhir)

FRONTEND = os.path.join(BASE, "frontend")
if not os.path.isdir(FRONTEND):                      # cadangan: struktur lama (frontend sejajar backend)
    FRONTEND = os.path.join(BASE, "..", "frontend")
app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="web")
