-- MIGRASI untuk database eduguard yang SUDAH ADA. Jalankan SATU KALI saja:
--   mysql -u root -p < migrate_dosen_pa.sql
USE eduguard;

-- 1) Kolom dosen PA pada mahasiswa (NULL = belum ditentukan)
ALTER TABLE mahasiswa
  ADD COLUMN dosen_pa_id INT NULL AFTER ukt,
  ADD INDEX idx_mhs_dosen_pa (dosen_pa_id),
  ADD CONSTRAINT fk_mhs_dosen_pa FOREIGN KEY (dosen_pa_id) REFERENCES users(id) ON DELETE SET NULL;

-- 2) (OPSIONAL) Bagi rata mahasiswa yang belum punya dosen PA ke semua dosen aktif secara bergiliran.
--    Lewati bagian ini jika Anda ingin menetapkan sendiri lewat menu "Pembagian Dosen PA" (login admin).
--    Perlu MySQL 8.0+ / MariaDB 10.2+. Hapus tanda komentar (--) pada baris di bawah untuk menjalankan.
-- UPDATE mahasiswa m
-- JOIN (SELECT nim, ROW_NUMBER() OVER (ORDER BY nim) AS rn FROM mahasiswa WHERE dosen_pa_id IS NULL) x ON x.nim = m.nim
-- JOIN (SELECT id, ROW_NUMBER() OVER (ORDER BY id) AS rn FROM users WHERE role='dosen' AND aktif=1) d
--   ON d.rn = ((x.rn - 1) % (SELECT COUNT(*) FROM users WHERE role='dosen' AND aktif=1)) + 1
-- SET m.dosen_pa_id = d.id;

-- 3) Cek hasil
SELECT u.nama AS dosen_pa, COUNT(m.nim) AS jumlah_mahasiswa
FROM users u LEFT JOIN mahasiswa m ON m.dosen_pa_id = u.id
WHERE u.role = 'dosen' GROUP BY u.id, u.nama;
