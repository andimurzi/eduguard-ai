"""Ekspor PDF EduGuard AI: laporan daftar mahasiswa terprediksi dan laporan detail per mahasiswa."""
from datetime import datetime
from io import BytesIO
from typing import List, Optional
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle)

LABEL = {"hi": "Tinggi", "mid": "Sedang", "lo": "Rendah"}
WARNA = {"hi": colors.HexColor("#dc2626"), "mid": colors.HexColor("#d97706"), "lo": colors.HexColor("#059669")}
NAVY, ABU, GARIS = colors.HexColor("#1e2a4a"), colors.HexColor("#64748b"), colors.HexColor("#cbd5e1")
BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus",
         "September", "Oktober", "November", "Desember"]

# Rekomendasi intervensi per faktor (selaras dengan tampilan web)
REC = {
    "ipk": ("Konseling dengan dosen PA", "Susun rencana studi dan target IPS semester depan"),
    "hadir": ("Pantau kehadiran mingguan", "Kirim pengingat ke mahasiswa dan dosen pengampu"),
    "tugas": ("Bimbingan belajar mata kuliah lemah", "Ikutkan mentoring sebaya atau asistensi"),
    "gagal": ("Rencana pengulangan mata kuliah", "Atur ulang beban SKS agar realistis"),
    "tren": ("Tinjau penyebab penurunan nilai", "Diskusikan hambatan belajar atau kondisi pribadi"),
    "ukt": ("Konsultasi keringanan atau cicilan UKT", "Arahkan ke bagian keuangan dan info beasiswa"),
}

_ss = getSampleStyleSheet()
H1 = ParagraphStyle("h1", parent=_ss["Title"], fontSize=18, textColor=NAVY, alignment=0, spaceAfter=2, leading=22)
H2 = ParagraphStyle("h2", parent=_ss["Heading2"], fontSize=11.5, textColor=NAVY, spaceBefore=8, spaceAfter=4)
BODY = ParagraphStyle("body", parent=_ss["BodyText"], fontSize=9.2, leading=12.6)
MUT = ParagraphStyle("mut", parent=BODY, fontSize=8.5, textColor=ABU)
CELL = ParagraphStyle("cell", parent=BODY, fontSize=8, leading=10)
CELLC = ParagraphStyle("cellc", parent=CELL, alignment=TA_CENTER)
TH = ParagraphStyle("th", parent=CELLC, textColor=colors.white, fontName="Helvetica-Bold")


def tanggal(dt: Optional[datetime] = None) -> str:
    dt = dt or datetime.now()
    return f"{dt.day} {BULAN[dt.month - 1]} {dt.year}, {dt:%H:%M}"


def _ipk(s: dict) -> float:
    return sum(s["ips"]) / len(s["ips"])


def _p(t, st=CELL) -> Paragraph:
    return Paragraph(escape(str(t)), st)


def _footer(judul: str):
    def f(canvas, doc):
        canvas.saveState()
        w, _ = doc.pagesize
        canvas.setStrokeColor(GARIS)
        canvas.line(doc.leftMargin, 14 * mm, w - doc.rightMargin, 14 * mm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(ABU)
        canvas.drawString(doc.leftMargin, 9 * mm, f"EduGuard AI  |  {judul}  |  Rahasia, hanya untuk keperluan akademik")
        canvas.drawRightString(w - doc.rightMargin, 9 * mm, f"Halaman {doc.page}")
        canvas.restoreState()
    return f


def _kotak_ringkasan(hitung: dict, total: int, lebar: float) -> Table:
    sel = [[_p(total, ParagraphStyle("n", parent=CELLC, fontSize=16, leading=20, fontName="Helvetica-Bold")),
            *[_p(hitung[k], ParagraphStyle("n" + k, parent=CELLC, fontSize=16, leading=20, fontName="Helvetica-Bold",
                                           textColor=WARNA[k])) for k in ("hi", "mid", "lo")]],
           [_p("Total mahasiswa", CELLC), _p("Risiko tinggi", CELLC), _p("Risiko sedang", CELLC), _p("Risiko rendah", CELLC)]]
    t = Table(sel, colWidths=[lebar / 4] * 4)
    t.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), .6, GARIS), ("INNERGRID", (0, 0), (-1, -1), .6, GARIS),
                           ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                           ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    return t


def pdf_daftar(data: List[dict], pembuat: str, filter_ket: str = "") -> bytes:
    """Laporan semua mahasiswa terprediksi (urut skor risiko tertinggi)."""
    data = sorted(data, key=lambda s: -s["p"]["skor"])
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=14 * mm, rightMargin=14 * mm,
                            topMargin=14 * mm, bottomMargin=20 * mm, title="Laporan Prediksi Risiko Akademik",
                            author="EduGuard AI")
    lebar = doc.width
    hitung = {k: sum(1 for s in data if s["p"]["lvl"] == k) for k in ("hi", "mid", "lo")}

    el = [Paragraph("Laporan Prediksi Risiko Akademik Mahasiswa", H1),
          Paragraph(escape(f"Dibuat {tanggal()} oleh {pembuat}" + (f"  |  Filter: {filter_ket}" if filter_ket else "")), MUT),
          Spacer(1, 8), _kotak_ringkasan(hitung, len(data), lebar), Spacer(1, 10)]

    kepala = ["No", "NIM", "Nama", "Program studi", "Smt", "IPK", "Hadir", "Tugas", "SKS gagal", "UKT", "Risiko", "Faktor utama"]
    lb = [9, 25, 40, 34, 12, 11, 13, 13, 14, 12, 22]
    lb = [x * mm for x in lb]
    lb.append(lebar - sum(lb))
    rows = [[_p(h, TH) for h in kepala]]
    gaya = [("BACKGROUND", (0, 0), (-1, 0), NAVY), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LINEBELOW", (0, 0), (-1, -1), .4, GARIS), ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("REPEATROWS", (0, 0), (0, 0))]
    for i, s in enumerate(data, 1):
        p = s["p"]
        fak = "; ".join(f["nama"] for f in p["f"][:2]) or "-"
        rows.append([_p(i, CELLC), _p(s["nim"]), _p(s["nama"]), _p(s["prodi"]), _p(s["smt"], CELLC),
                     _p(f"{_ipk(s):.2f}", CELLC), _p(f"{s['hadir']:.0f}%", CELLC), _p(f"{s['tugas']:.0f}", CELLC),
                     _p(f"{s['sks_gagal']:.0f}", CELLC), _p("Ya" if s["ukt"] else "Tidak", CELLC),
                     _p(f"{LABEL[p['lvl']]} {p['skor']}%", ParagraphStyle("r", parent=CELLC, textColor=colors.white,
                                                                       fontName="Helvetica-Bold")), _p(fak)])
        gaya.append(("BACKGROUND", (10, i), (10, i), WARNA[p["lvl"]]))
        if i % 2 == 0:
            gaya.append(("BACKGROUND", (0, i), (9, i), colors.HexColor("#f8fafc")))
            gaya.append(("BACKGROUND", (11, i), (11, i), colors.HexColor("#f8fafc")))
    if not data:
        rows.append([_p("Tidak ada data mahasiswa yang sesuai filter.")] + [""] * 11)
        gaya.append(("SPAN", (0, 1), (-1, 1)))
    t = Table(rows, colWidths=lb, repeatRows=1)
    t.setStyle(TableStyle(gaya))
    el += [t, Spacer(1, 8),
           Paragraph("Skor risiko (0-100) dihitung model AI dari IPK, tren IPS, kehadiran, nilai tugas, SKS tidak lulus, "
                     "dan status UKT. Hasil bersifat pendukung keputusan, bukan vonis akademik.", MUT)]
    f = _footer("Laporan Prediksi Risiko Akademik")
    doc.build(el, onFirstPage=f, onLaterPages=f)
    return buf.getvalue()


def pdf_detail(s: dict, pembuat: str) -> bytes:
    """Laporan satu mahasiswa: skor, narasi AI, faktor penyebab, riwayat IPS, rekomendasi."""
    p = s["p"]
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=13 * mm,
                            bottomMargin=18 * mm, title=f"Laporan Risiko {s['nama']}", author="EduGuard AI")
    w = doc.width
    warna = WARNA[p["lvl"]]
    el = [Paragraph("Laporan Risiko Akademik Mahasiswa", H1),
          Paragraph(escape(f"Dibuat {tanggal()} oleh {pembuat}"), MUT), Spacer(1, 6)]

    # identitas + skor
    idn = [[_p("Nama", BODY), _p(s["nama"], BODY)], [_p("NIM", BODY), _p(s["nim"], BODY)],
           [_p("Program studi", BODY), _p(s["prodi"], BODY)], [_p("Semester", BODY), _p(s["smt"], BODY)],
           [_p("IPK", BODY), _p(f"{_ipk(s):.2f}", BODY)]]
    ti = Table(idn, colWidths=[28 * mm, w * .55 - 28 * mm])
    ti.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("TEXTCOLOR", (0, 0), (0, -1), ABU),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 2), ("TOPPADDING", (0, 0), (-1, -1), 2)]))
    skor = Table([[_p(f"{p['skor']}%", ParagraphStyle("sk", parent=CELLC, fontSize=28, leading=32, fontName="Helvetica-Bold", textColor=colors.white))],
                  [_p(f"Risiko {LABEL[p['lvl']].lower()}", ParagraphStyle("sl", parent=CELLC, fontSize=10, textColor=colors.white))]],
                 colWidths=[w * .38])
    skor.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), warna), ("TOPPADDING", (0, 0), (-1, 0), 10),
                              ("BOTTOMPADDING", (0, -1), (-1, -1), 10), ("ROUNDEDCORNERS", [8, 8, 8, 8])]))
    atas = Table([[ti, skor]], colWidths=[w * .58, w * .42])
    atas.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    el += [atas]

    # data akademik
    el.append(Paragraph("Data akademik", H2))
    da = Table([[_p(h, TH) for h in ("Kehadiran", "Nilai tugas", "SKS tidak lulus", "Tunggakan UKT")],
                [_p(f"{s['hadir']:.0f}%", CELLC), _p(f"{s['tugas']:.0f}", CELLC), _p(f"{s['sks_gagal']:.0f}", CELLC),
                 _p("Ya" if s["ukt"] else "Tidak", CELLC)]], colWidths=[w / 4] * 4)
    da.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("BOX", (0, 0), (-1, -1), .5, GARIS),
                            ("INNERGRID", (0, 0), (-1, -1), .5, GARIS), ("TOPPADDING", (0, 0), (-1, -1), 5),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    el.append(da)

    el.append(Paragraph("IPS per semester", H2))
    n = len(s["ips"])
    ips = Table([[_p(f"S{i + 1}", TH) for i in range(n)], [_p(f"{v:.2f}", CELLC) for v in s["ips"]]],
                colWidths=[min(w / n, 22 * mm)] * n, hAlign="LEFT")
    ips.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("BOX", (0, 0), (-1, -1), .5, GARIS),
                             ("INNERGRID", (0, 0), (-1, -1), .5, GARIS), ("TOPPADDING", (0, 0), (-1, -1), 4),
                             ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    el.append(ips)

    # narasi AI
    el.append(Paragraph("Analisis AI", H2))
    for para in p["narasi"].split("\n\n"):
        el += [Paragraph(escape(para), BODY), Spacer(1, 2)]

    # faktor
    el.append(Paragraph("Faktor penyebab (dijelaskan SHAP)", H2))
    if p["f"]:
        mx = max(f["pts"] for f in p["f"]) or 1
        rows = [[_p(f["nama"], BODY), _p(f"+{f['pts']:.0f} poin", BODY), ""] for f in p["f"]]
        st = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LINEBELOW", (0, 0), (-1, -1), .4, GARIS)]
        # batang proporsional digambar lewat sel bersarang
        for i, f in enumerate(p["f"]):
            bar = Table([[""]], colWidths=[max(f["pts"] / mx * w * .33, 2)], rowHeights=[6])
            bar.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), WARNA["hi"] if f["pts"] >= 12 else WARNA["mid"])]))
            rows[i][2] = bar
        tf = Table(rows, colWidths=[w * .5, w * .15, w * .35])
        tf.setStyle(TableStyle(st))
        el.append(tf)
    else:
        el.append(Paragraph("Tidak ada faktor risiko yang menonjol.", BODY))

    # rekomendasi
    blok = [Paragraph("Rekomendasi intervensi", H2)]
    if p["f"]:
        for f in p["f"]:
            judul, isi = REC.get(f["key"], ("Tindak lanjut", ""))
            r = Table([[Paragraph(f"<b>{escape(judul)}</b><br/><font size=8.5 color='#64748b'>{escape(isi)}</font>", BODY)]],
                      colWidths=[w])
            r.setStyle(TableStyle([("LINEBEFORE", (0, 0), (0, -1), 3, WARNA["hi"] if f["pts"] >= 12 else WARNA["mid"]),
                                   ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                                   ("LEFTPADDING", (0, 0), (-1, -1), 9), ("TOPPADDING", (0, 0), (-1, -1), 3),
                                   ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
            blok += [r, Spacer(1, 3)]
    else:
        blok.append(Paragraph("Pertahankan kinerja saat ini. Tidak ada intervensi khusus yang disarankan.", BODY))
    el.append(KeepTogether(blok))

    f = _footer(f"{s['nama']} ({s['nim']})")
    doc.build(el, onFirstPage=f, onLaterPages=f)
    return buf.getvalue()
