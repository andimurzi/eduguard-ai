"""Definisi fitur yang dipakai model. Dipakai bersama oleh training dan API."""
import pandas as pd

FITUR = ["ipk", "hadir", "tugas", "sks_gagal", "tren", "ukt"]


def buat_fitur(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    out["ipk"] = df["ipk"]
    out["hadir"] = df["hadir"]
    out["tugas"] = df["tugas"]
    out["sks_gagal"] = df["sks_gagal"]
    out["tren"] = (df["ips_sebelumnya"] - df["ips_terakhir"]).clip(0, 1)  # penurunan IPS
    out["ukt"] = df["ukt"]
    return out[FITUR]
