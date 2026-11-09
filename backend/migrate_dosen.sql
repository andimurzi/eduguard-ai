-- MIGRASI untuk database eduguard yang SUDAH ADA. Jalankan SATU KALI saja.
USE eduguard;

-- 1) Tambah kolom NIDN (khusus dosen, 10 digit, tidak boleh kembar)
ALTER TABLE users ADD COLUMN nidn VARCHAR(10) NULL UNIQUE AFTER username;

-- 2) Ubah peran: dosen_pa menjadi dosen, akun pimpinan dihapus, lalu kunci menjadi admin/dosen saja
ALTER TABLE users MODIFY role ENUM('admin','dosen_pa','pimpinan','dosen') NOT NULL;
UPDATE users SET role='dosen' WHERE role='dosen_pa';
DELETE FROM users WHERE role='pimpinan';
ALTER TABLE users MODIFY role ENUM('admin','dosen') NOT NULL;

-- 3) Cek hasilnya. Dosen lama masih NIDN = NULL (belum bisa login) sampai Anda isi NIDN-nya.
SELECT id, username, nidn, nama, role, aktif FROM users;
