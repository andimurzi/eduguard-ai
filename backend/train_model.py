"""Melatih model, memilih yang terbaik (cross-validation), simpan ke model.joblib.

Catatan: hanya model berbasis pohon yang didukung SHAP untuk 3 kelas (rendah/sedang/tinggi)
yang boleh jadi kandidat. GradientBoostingClassifier sengaja TIDAK dipakai karena
shap.TreeExplainer hanya mendukungnya untuk klasifikasi biner, sehingga main.py akan crash.
"""
import joblib
import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.utils.class_weight import compute_sample_weight

from features import FITUR, buat_fitur

df = pd.read_csv("data_mahasiswa.csv")
X, y = buat_fitur(df), df["risiko"]
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

kandidat = {
    "RandomForest": RandomForestClassifier(n_estimators=300, min_samples_leaf=3, class_weight="balanced",
                                           random_state=42, n_jobs=-1),
    "ExtraTrees": ExtraTreesClassifier(n_estimators=300, min_samples_leaf=3, class_weight="balanced",
                                       random_state=42, n_jobs=-1),
}

skor = {}
for nama, m in kandidat.items():
    skor[nama] = cross_val_score(m, X_tr, y_tr, cv=5, scoring="f1_macro", n_jobs=-1).mean()
    print(f"{nama}: F1-macro CV = {skor[nama]:.3f}")

terbaik = max(skor, key=skor.get)
model = kandidat[terbaik]
model.fit(X_tr, y_tr, sample_weight=compute_sample_weight("balanced", y_tr))
pred = model.predict(X_te)
print(f"\nModel terpilih: {terbaik}\n", classification_report(y_te, pred))

metrik = {"akurasi": round(float(accuracy_score(y_te, pred)), 3),
          "f1_macro": round(float(f1_score(y_te, pred, average="macro")), 3)}
joblib.dump({"model": model, "fitur": FITUR, "nama": terbaik, "metrik": metrik}, "model.joblib")
print("Model tersimpan: model.joblib", metrik)