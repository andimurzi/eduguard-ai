"""Membuat dataset SINTETIS untuk melatih model EduGuard AI.

Ganti file hasilnya (data_mahasiswa.csv) dengan data historis asli kampus
(kolom yang sama) saat data tersedia.
"""
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
N = 4000

# Profil dasar mahasiswa (0 = kesulitan, 1 = sangat baik)
kemampuan = rng.beta(2.4, 2, N)

ipk = np.clip(1.4 + kemampuan * 2.6 + rng.normal(0, .25, N), 0.8, 4.0)
ips_sebelumnya = np.clip(ipk + rng.normal(0, .2, N), 0.5, 4.0)
ips_terakhir = np.clip(ips_sebelumnya + rng.normal(0, .35, N), 0.0, 4.0)
hadir = np.clip(45 + kemampuan * 50 + rng.normal(0, 10, N), 30, 100)
tugas = np.clip(40 + kemampuan * 50 + rng.normal(0, 11, N), 10, 100)
sks_gagal = np.clip(np.round((1 - kemampuan) * 10 * rng.random(N)), 0, 20)
ukt = (rng.random(N) < np.where(kemampuan < .4, .3, .06)).astype(int)

# Skor risiko "sebenarnya" (dipakai hanya untuk memberi label pada data sintetis)
tren = np.clip(ips_sebelumnya - ips_terakhir, 0, 1)
skor = (np.clip((3 - ipk) / 1.2, 0, 1) * 32 + np.clip((85 - hadir) / 40, 0, 1) * 26
        + np.clip((75 - tugas) / 40, 0, 1) * 16 + np.clip(sks_gagal / 10, 0, 1) * 12
        + tren * 8 + ukt * 6 + rng.normal(0, 5, N))
risiko = np.where(skor >= 55, "tinggi", np.where(skor >= 30, "sedang", "rendah"))

df = pd.DataFrame({"ipk": ipk.round(2), "ips_terakhir": ips_terakhir.round(2),
                   "ips_sebelumnya": ips_sebelumnya.round(2), "hadir": hadir.round(0),
                   "tugas": tugas.round(0), "sks_gagal": sks_gagal, "ukt": ukt,
                   "risiko": risiko})
df.to_csv("data_mahasiswa.csv", index=False)
print(df.risiko.value_counts())
print("Tersimpan: data_mahasiswa.csv", df.shape)
