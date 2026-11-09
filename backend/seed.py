
"""Mengisi MySQL dengan akun admin dan data mahasiswa contoh.
Jalankan setelah schema.sql.
"""

import os
import secrets

import numpy as np
from sqlalchemy import text

from auth import hash_pw
from database import engine

NAMES = [
    "Andi Pratama", "Siti Rahma", "Budi Santoso",
    "Dewi Lestari", "Rizky Maulana", "Nadia Putri",
    "Fajar Nugroho", "Maya Anggraini", "Dimas Saputra",
    "Laras Wulandari", "Hendra Kusuma", "Putri Ayu",
    "Yoga Prakoso", "Intan Permata", "Bagas Wicaksono",
    "Rina Marlina", "Eko Setiawan", "Tania Salsabila",
    "Galih Ramadhan", "Citra Dewanti", "Ilham Firmansyah",
    "Aulia Zahra", "Reza Mahendra", "Vina Oktavia",
]

PRODI = [
    "Teknik Informatika",
    "Sistem Teknologi Informasi",
    "Teknik Mesin",
    "Teknik Elektro",
    "Teknologi Rekayasa Mekatronika",
]

rng = np.random.default_rng()
cl = lambda x, a, b: float(np.clip(x, a, b))


def seed_admin(c):
    """Membuat akun admin hanya jika belum ada."""
    if not c.execute(
        text("SELECT 1 FROM users WHERE username = 'admin' LIMIT 1")
    ).first():
        pw = os.getenv("ADMIN_PASSWORD") or secrets.token_urlsafe(10)

        c.execute(
            text("""
                INSERT INTO users(username, nama, role, password_hash)
                VALUES ('admin', 'Admin Akademik', 'admin', :h)
            """),
            {"h": hash_pw(pw)},
        )

        print(
            f"\n=== AKUN ADMIN ===\n"
            f"Username: admin\n"
            f"Password: {pw}\n"
            f"Simpan password ini dengan aman.\n"
        )
    else:
        print("Akun admin sudah tersedia.")


def seed_mahasiswa(target_total):
    """Menambah mahasiswa sampai jumlah total sesuai target."""

    if target_total < 1:
        raise ValueError("Target harus minimal 1 mahasiswa.")

    ditambahkan = 0

    with engine.begin() as c:
        seed_admin(c)

        total_awal = c.execute(
            text("SELECT COUNT(*) FROM mahasiswa")
        ).scalar() or 0

        if total_awal >= target_total:
            print(
                f"Database sudah memiliki {total_awal} mahasiswa. "
                f"Target {target_total} sudah tercapai."
            )
            return

        # Dosen aktif: mahasiswa contoh dibagi bergiliran ke mereka (kosong = belum ditentukan).
        dosen_ids = [r[0] for r in c.execute(
            text("SELECT id FROM users WHERE role='dosen' AND aktif=1 ORDER BY id")
        )]

        # Mulai dari NIM contoh dan lewati NIM yang sudah terpakai.
        nomor = 1

        while total_awal + ditambahkan < target_total:
            nim = str(2403046000 + nomor)

            ada = c.execute(
                text("SELECT 1 FROM mahasiswa WHERE nim = :nim LIMIT 1"),
                {"nim": nim},
            ).first()

            if ada:
                nomor += 1
                continue

            i = nomor - 1
            nama_dasar = NAMES[i % len(NAMES)]
            nama = f"{nama_dasar} {nomor:04d}"
            prodi = PRODI[i % len(PRODI)]

            smt = int(rng.integers(3, 8))
            base = 1.5 + rng.random() * 2.4
            q = (base - 1.5) / 2.4
            tr = (rng.random() - 0.6) * 0.5

            ips_list = [
                round(
                    cl(
                        base
                        + tr * (k - (smt - 2) / 2)
                        + (rng.random() - 0.5) * 0.3,
                        0.8,
                        4.0,
                    ),
                    2,
                )
                for k in range(1, smt)
            ]

            hadir = int(
                cl(48 + q * 45 + (rng.random() - 0.5) * 22, 35, 100)
            )
            tugas = int(
                cl(42 + q * 45 + (rng.random() - 0.5) * 24, 20, 100)
            )
            sks_gagal = int(cl((1 - q) * 10 * rng.random(), 0, 12))
            ukt = int(rng.random() < (0.35 if q < 0.4 else 0.06))

            c.execute(
                text("""
                    INSERT INTO mahasiswa
                    (nim, nama, prodi, smt, hadir, tugas, sks_gagal, ukt, dosen_pa_id)
                    VALUES
                    (:n, :nm, :p, :s, :h, :t, :g, :u, :pa)
                """),
                {
                    "n": nim,
                    "nm": nama,
                    "p": prodi,
                    "s": smt,
                    "h": hadir,
                    "t": tugas,
                    "g": sks_gagal,
                    "u": ukt,
                    "pa": dosen_ids[i % len(dosen_ids)] if dosen_ids else None,
                },
            )

            for semester, ips in enumerate(ips_list, start=1):
                c.execute(
                    text("""
                        INSERT INTO ips_semester(nim, semester, ips)
                        VALUES (:n, :k, :v)
                    """),
                    {"n": nim, "k": semester, "v": ips},
                )

            ditambahkan += 1
            nomor += 1

        total_akhir = c.execute(
            text("SELECT COUNT(*) FROM mahasiswa")
        ).scalar()

    print(f"Mahasiswa baru ditambahkan: {ditambahkan}")
    print(f"Total mahasiswa sekarang: {total_akhir}")


if __name__ == "__main__":
    try:
        target = int(input("Masukkan target total mahasiswa: "))
        seed_mahasiswa(target)
    except ValueError as e:
        print(f"Input tidak valid: {e}")
