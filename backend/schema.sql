-- Jalankan sekali:  mysql -u root -p < schema.sql
CREATE DATABASE IF NOT EXISTS eduguard CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE eduguard;

-- Akun yang boleh masuk. Hanya akun di tabel ini yang bisa login.
CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(50) NOT NULL UNIQUE,
  nidn VARCHAR(10) NULL UNIQUE,            -- khusus dosen (10 digit); admin dikosongkan
  nama VARCHAR(100) NOT NULL,
  role ENUM('admin','dosen') NOT NULL,
  password_hash VARCHAR(100) NOT NULL,
  aktif TINYINT(1) NOT NULL DEFAULT 1,
  gagal_login INT NOT NULL DEFAULT 0,
  terkunci_hingga DATETIME NULL,
  last_login DATETIME NULL,
  dibuat DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Jejak akses: setiap percobaan login (berhasil atau gagal) tercatat.
CREATE TABLE IF NOT EXISTS login_log (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  waktu DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  username VARCHAR(50),
  ip VARCHAR(45),
  berhasil TINYINT(1) NOT NULL,
  keterangan VARCHAR(100),
  INDEX (waktu)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS mahasiswa (
  nim VARCHAR(20) PRIMARY KEY,
  nama VARCHAR(100) NOT NULL,
  prodi VARCHAR(80) NOT NULL,
  smt TINYINT UNSIGNED NOT NULL,
  hadir TINYINT UNSIGNED NOT NULL,
  tugas TINYINT UNSIGNED NOT NULL,
  sks_gagal TINYINT UNSIGNED NOT NULL,
  ukt TINYINT(1) NOT NULL DEFAULT 0,
  dosen_pa_id INT NULL,                    -- dosen PA pembimbing (users.id); NULL = belum ditentukan
  dibuat DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_mhs_dosen_pa (dosen_pa_id),
  CONSTRAINT fk_mhs_dosen_pa FOREIGN KEY (dosen_pa_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS ips_semester (
  nim VARCHAR(20) NOT NULL,
  semester TINYINT UNSIGNED NOT NULL,
  ips DECIMAL(3,2) NOT NULL,
  PRIMARY KEY (nim, semester),
  FOREIGN KEY (nim) REFERENCES mahasiswa(nim) ON DELETE CASCADE
) ENGINE=InnoDB;
