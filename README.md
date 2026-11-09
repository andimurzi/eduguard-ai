# EduGuard AI v2

Prediksi risiko akademik mahasiswa: login terdata (MySQL), model AI dengan penjelasan SHAP,
what-if simulator, dan tampilan modern beranimasi.

## Struktur
    backend/   main.py (API), auth.py, database.py, schema.sql, seed.py,
               features.py, pdf_export.py, generate_data.py, train_model.py, data_mahasiswa.csv
    frontend/  index.html, style.css, script.js   (dilayani otomatis oleh backend)

## Implementasi

### 1. Siapkan MySQL (8.x / MariaDB 10.5+)
    mysql -u root -p < backend/schema.sql
    mysql -u root -p -e "CREATE USER 'eduguard_user'@'localhost' IDENTIFIED BY 'PASSWORD_KUAT'; GRANT ALL ON eduguard.* TO 'eduguard_user'@'localhost';"

### 2. Konfigurasi
    cd backend
    pip install -r requirements.txt
    cp .env.example .env        # Windows: copy .env.example .env
Isi `.env`: `DB_URL` (user/password MySQL tadi) dan `JWT_SECRET`
(buat: `python -c "import secrets;print(secrets.token_urlsafe(48))"`).

### 3. Latih model dan isi database
    python generate_data.py     # opsional, dataset sintetis sudah disertakan
    python train_model.py       # memilih RandomForest atau GradientBoosting terbaik
    python seed.py              # membuat akun admin + 24 mahasiswa contoh

`seed.py` mencetak password admin satu kali. Catat, lalu simpan di tempat aman.

### 4. Jalankan
    uvicorn main:app --reload --port 8000
Buka **http://localhost:8000**. API docs: http://localhost:8000/docs

## Cara kerja login
- Hanya akun di tabel `users` yang dapat masuk. Tidak ada akun bawaan, tidak ada isian otomatis.
- Peran ditentukan database, bukan dipilih pengguna di form:
  - **Admin Akademik**: semua mahasiswa, menu **Pembagian Dosen PA** (tetapkan dosen PA per mahasiswa atau massal) dan
    Manajemen Akses (tambah akun, nonaktifkan, reset sandi, lihat log)
  - **Dosen PA**: hanya melihat dan mengelola **mahasiswa bimbingannya sendiri** (dashboard, daftar, detail, simulasi,
    PDF, prediksi baru). Mahasiswa yang ia simpan otomatis menjadi bimbingannya. Mahasiswa milik dosen lain tidak
    tampil dan tidak bisa dibuka lewat URL/API (hasilnya 404).
- Kata sandi disimpan dengan bcrypt. Sesi memakai JWT 8 jam; peran dicek ulang ke database tiap permintaan,
  jadi akun yang dinonaktifkan langsung kehilangan akses.
- 5 kali salah sandi mengunci akun 5 menit. Semua percobaan (berhasil/gagal) masuk tabel `login_log`.

## Dosen PA (pembimbing akademik)
Setiap mahasiswa punya kolom `dosen_pa_id` (mengacu ke `users.id`). Admin menetapkannya di menu **Pembagian Dosen PA**
(centang beberapa mahasiswa lalu "Tetapkan ke yang dipilih", atau ubah satu per satu lewat dropdown) atau saat
menambah mahasiswa di *Prediksi Baru*. Mahasiswa tanpa dosen PA hanya terlihat oleh admin.
- Database baru: `schema.sql` sudah memuat kolomnya.
- Database lama: jalankan sekali `mysql -u root -p < backend/migrate_dosen_pa.sql` (berisi opsi bagi rata otomatis).
- `seed.py` membagi mahasiswa contoh bergiliran ke dosen aktif.
- Endpoint admin: `GET /admin/dosen-pa`, `PATCH /admin/mahasiswa/{nim}/dosen-pa`, `POST /admin/mahasiswa/dosen-pa`.

## Tampilan responsif
Antarmuka menyesuaikan layar: laptop (sidebar), tablet dan HP (bilah menu atas yang bisa digeser), dan di HP tabel
otomatis menjadi kartu. Diuji pada lebar 360, 390, 768, 1280, dan 1920 px tanpa konten yang melebar keluar layar.

## Ekspor PDF
- **Data Mahasiswa > Ekspor PDF**: laporan semua mahasiswa terprediksi (landscape A4, urut skor tertinggi, ringkasan
  jumlah per level risiko). Mengikuti filter yang sedang aktif (pencarian nama/NIM dan level risiko).
- **Detail mahasiswa > Unduh PDF**: laporan satu mahasiswa (skor, data akademik, IPS per semester, analisis AI,
  faktor SHAP, rekomendasi intervensi).
- Endpoint: `GET /mahasiswa/export/pdf?level=hi|mid|lo&q=...` dan `GET /mahasiswa/{nim}/pdf` (butuh login Admin/Dosen).
- Memakai library `reportlab`. Jika belum terpasang: `pip install -r requirements.txt`.

## Data asli
Data mahasiswa kini di tabel `mahasiswa` dan `ips_semester`. Untuk mengganti data contoh, kosongkan
kedua tabel lalu impor data kampus. Untuk melatih ulang model dengan data historis, ganti
`data_mahasiswa.csv` (kolom: ipk, ips_terakhir, ips_sebelumnya, hadir, tugas, sks_gagal, ukt, risiko)
dan jalankan `python train_model.py`. Dataset bawaan sintetis, jadi akurasinya belum mencerminkan kondisi nyata.

## Untuk produksi
Pakai HTTPS (reverse proxy Nginx/Caddy), isi `ALLOWED_ORIGINS` dengan domain Anda, dan simpan `.env` di luar repositori.
