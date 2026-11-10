"use strict";
// ===== UTIL =====
const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = t => String(t ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const RM = matchMedia("(prefers-reduced-motion: reduce)").matches;
const LBL = { hi: "Tinggi", mid: "Sedang", lo: "Rendah" };
const ROLE = { admin: "Admin Akademik", dosen: "Dosen PA" };
const PRODI = ["Teknik Informatika", "Sistem Informasi", "Manajemen", "Akuntansi"];
const REC = {
  ipk: ["Konseling dengan dosen PA", "Susun rencana studi dan target IPS semester depan", "hi"],
  hadir: ["Pantau kehadiran mingguan", "Kirim pengingat ke mahasiswa dan dosen pengampu", "mid"],
  tugas: ["Bimbingan belajar mata kuliah lemah", "Ikutkan mentoring sebaya atau asistensi", "mid"],
  gagal: ["Rencana pengulangan mata kuliah", "Atur ulang beban SKS agar realistis", "hi"],
  tren: ["Tinjau penyebab penurunan nilai", "Diskusikan hambatan belajar atau kondisi pribadi", "mid"],
  ukt: ["Konsultasi keringanan atau cicilan UKT", "Arahkan ke bagian keuangan dan info beasiswa", "mid"]
};
const IC = {
  dash: "M3 3h8v8H3zM13 3h8v5h-8zM13 12h8v9h-8zM3 15h8v6H3z",
  list: "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8M22 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8",
  new: "M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9zM19 16l.8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8z",
  pa: "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8M16 11l2 2 4-4",
  akses: "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10zM9 12l2 2 4-4",
  out: "M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"
};
const ico = k => `<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="${IC[k]}"/></svg>`;
const tgl = d => d ? new Date(d).toLocaleString("id-ID", { dateStyle: "medium", timeStyle: "short" }) : "-";

let token = sessionStorage.getItem("eg_token"), me = null, DB = [], info = {}, view = "dash", sel = null, flt = { q: "", l: "", d: "" }, pflt = { q: "", d: "" }, PASEL = new Set(), DOSEN = { dosen: [], tanpa_dosen: 0 }, draft = null, peran = "dosen";
const isDosen = () => me && me.role === "dosen";

// ===== TEMA =====
function setTheme(t) { document.documentElement.dataset.theme = t; try { localStorage.setItem("eg_theme", t) } catch (e) { } $$("[data-act=theme]").forEach(b => b.textContent = t === "dark" ? "Mode terang" : "Mode gelap") }
let saved = null; try { saved = localStorage.getItem("eg_theme") } catch (e) { }
setTheme(saved || (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark"));

function toast(m) { const t = $("#toast"); t.textContent = m; t.classList.remove("hidden", "in"); void t.offsetWidth; t.classList.add("in"); clearTimeout(toast.h); toast.h = setTimeout(() => t.classList.add("hidden"), 2600) }

// ===== API =====
async function api(path, opt = {}) {
  const r = await fetch(path, {
    method: opt.method || "GET",
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: "Bearer " + token } : {}) },
    body: opt.body ? JSON.stringify(opt.body) : undefined
  });
  if (r.status === 401 && token && path !== "/auth/login") { logout("Sesi berakhir. Silakan masuk lagi."); throw new Error("Sesi berakhir.") }
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(typeof d.detail === "string" ? d.detail : "Periksa kembali isian Anda (" + r.status + ").");
  return d;
}

// ===== EKSPOR PDF =====
async function unduhPDF(path, nama, btn) {
  const lbl = btn && btn.textContent;
  if (btn) { btn.disabled = true; btn.textContent = "Membuat PDF..." }
  try {
    const r = await fetch(path, { headers: { Authorization: "Bearer " + token } });
    if (r.status === 401) { logout("Sesi berakhir. Silakan masuk lagi."); return }
    if (!r.ok) { const d = await r.json().catch(() => ({})); throw new Error(typeof d.detail === "string" ? d.detail : "Gagal membuat PDF (" + r.status + ").") }
    const url = URL.createObjectURL(await r.blob()), a = document.createElement("a");
    a.href = url; a.download = nama; document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 4000);
    toast("PDF berhasil diunduh");
  } catch (e) { toast(e.message === "Failed to fetch" ? "Server tidak dapat dihubungi." : e.message) }
  finally { if (btn) { btn.disabled = false; btn.textContent = lbl } }
}
function ekspor(btn) {
  const p = new URLSearchParams(); if (flt.l) p.set("level", flt.l); if (flt.q.trim()) p.set("q", flt.q.trim());
  const qs = p.toString();
  unduhPDF("/mahasiswa/export/pdf" + (qs ? "?" + qs : ""), "eduguard-prediksi-" + new Date().toISOString().slice(0, 10) + ".pdf", btn);
}

// ===== LOGIN / LOGOUT =====
function fail(m) { $("#err").textContent = m; const b = $(".box"); b.classList.remove("shake"); void b.offsetWidth; b.classList.add("shake") }
function pilihPeran(r) {
  peran = r;
  $$("[data-act=peran]").forEach(b => { const on = b.dataset.p === r; b.classList.toggle("on", on); b.setAttribute("aria-selected", on) });
  const u = $("#u"); u.value = ""; $("#err").textContent = "";
  if (r === "dosen") { $("#ulbl").textContent = "NIDN"; u.placeholder = "10 digit NIDN"; u.inputMode = "numeric"; u.maxLength = 10 }
  else { $("#ulbl").textContent = "Username"; u.placeholder = "username admin"; u.inputMode = "text"; u.maxLength = 50 }
  u.focus();
}
async function login() {
  const u = $("#u").value.trim(), p = $("#p").value;
  if (!u || !p) return fail(peran === "dosen" ? "Isi NIDN dan kata sandi." : "Isi username dan kata sandi.");
  if (peran === "dosen" && !/^\d{10}$/.test(u)) return fail("NIDN harus 10 digit angka.");
  const g = $("#go"); g.disabled = true; g.classList.add("busy"); $("#err").textContent = "";
  try {
    const d = await api("/auth/login", { method: "POST", body: { peran, identitas: u, password: p } });
    token = d.token; me = d.user; sessionStorage.setItem("eg_token", token); $("#p").value = ""; await enter();
  } catch (e) { fail(e.message === "Failed to fetch" ? "Server tidak dapat dihubungi. Pastikan backend berjalan." : e.message) }
  g.disabled = false; g.classList.remove("busy");
}
function logout(msg) {
  token = null; me = null; sessionStorage.removeItem("eg_token");
  DB = []; flt = { q: "", l: "", d: "" }; pflt = { q: "", d: "" }; PASEL.clear(); DOSEN = { dosen: [], tanpa_dosen: 0 };
  $("#app").classList.add("hidden"); $("#login").classList.remove("hidden"); $("#err").textContent = msg || "";
}
async function enter() {
  await Promise.all([loadDB(), loadDosen(), api("/health").then(h => info = h).catch(() => { })]);
  $("#login").classList.add("hidden"); $("#app").classList.remove("hidden");
  const items = [["dash", "Dashboard"], ["list", isDosen() ? "Mahasiswa Bimbingan" : "Data Mahasiswa"], ["new", "Prediksi Baru"]];
  if (me.role === "admin") items.push(["pa", "Pembagian Dosen PA"], ["akses", "Manajemen Akses"]);
  $("#nav").innerHTML = items.map(([k, l]) => `<button class="nav" data-v="${k}">${ico(k)}${l}</button>`).join("") +
    `<button class="nav" data-act="theme"></button><button class="nav" data-act="out">${ico("out")}Keluar</button>`;
  setTheme(document.documentElement.dataset.theme);
  const mt = info.metrik || {};
  $("#who").innerHTML = `<b>${esc(me.nama)}</b>${ROLE[me.role]}<br><span style="font-size:12px">Model: ${esc(info.model || "-")}${mt.akurasi ? " (akurasi " + Math.round(mt.akurasi * 100) + "%)" : ""}</span>`;
  go("dash");
}
async function loadDB() { DB = await api("/mahasiswa") }
async function loadDosen() { if (me && me.role === "admin") DOSEN = await api("/admin/dosen-pa") }
const optDosen = (sel, semua) => (semua ? `<option value="">${semua}</option>` : "") +
  (semua ? `<option value="none"${sel === "none" ? " selected" : ""}>Belum ditentukan</option>` : `<option value=""${!sel ? " selected" : ""}>Belum ditentukan</option>`) +
  DOSEN.dosen.map(d => `<option value="${d.id}"${String(sel) === String(d.id) ? " selected" : ""}>${esc(d.nama)}${d.aktif ? "" : " (nonaktif)"}</option>`).join("");

// ===== TABEL RESPONSIF: beri label tiap sel agar bisa tampil sebagai kartu di HP =====
function labelTables() {
  $$("table").forEach(t => {
    t.classList.add("rt");
    const h = [...t.querySelectorAll("thead th")].map(x => x.textContent.trim());
    t.querySelectorAll("tbody tr").forEach(r => [...r.children].forEach((c, i) => {
      if (c.colSpan > 1) return;
      c.dataset.label = h[i] === "Mahasiswa" ? "" : (h[i] || "");
    }));
  });
}
const refTb = () => { $("#tb").innerHTML = rows(); labelTables() };
const refPa = () => { $("#ptb").innerHTML = paRows(); labelTables() };

// ===== EVENT =====
document.addEventListener("click", e => {
  const t = e.target.closest("[data-go],[data-v],[data-act]"); if (!t) return;
  if (t.dataset.go) return go("detail", t.dataset.go);
  if (t.dataset.v) return go(t.dataset.v);
  const a = t.dataset.act;
  if (a === "peran") pilihPeran(t.dataset.p);
  else if (a === "theme") setTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
  else if (a === "out") logout();
  else if (a === "eye") { const p = $("#p"); p.type = p.type === "password" ? "text" : "password"; t.textContent = p.type === "password" ? "Lihat" : "Sembunyi" }
  else if (a === "back") go("list");
  else if (a === "pdf") ekspor(t);
  else if (a === "pdf1") unduhPDF("/mahasiswa/" + encodeURIComponent(t.dataset.nim) + "/pdf", "eduguard-" + t.dataset.nim + ".pdf", t);
  else if (a === "toggle") ubahUser(+t.dataset.id, { aktif: t.dataset.on === "1" });
  else if (a === "reset") { const pw = prompt("Kata sandi baru untuk " + t.dataset.u + " (minimal 8 karakter):"); if (pw) ubahUser(+t.dataset.id, { password: pw }) }
});
document.addEventListener("change", e => {
  const t = e.target;
  if (t.matches(".pachk")) { t.checked ? PASEL.add(t.dataset.nim) : PASEL.delete(t.dataset.nim); infoPilih() }
  else if (t.id === "pall") { $$(".pachk").forEach(c => { c.checked = t.checked; t.checked ? PASEL.add(c.dataset.nim) : PASEL.delete(c.dataset.nim) }); infoPilih() }
  else if (t.matches(".pasel")) tetapkan([t.dataset.nim], t.value);
});
document.addEventListener("mousemove", e => { const g = e.target.closest(".glass"); if (g) { const r = g.getBoundingClientRect(); g.style.setProperty("--mx", e.clientX - r.left + "px"); g.style.setProperty("--my", e.clientY - r.top + "px") } });
$("#go").onclick = login;
["u", "p"].forEach(i => $("#" + i).addEventListener("keydown", e => { if (e.key === "Enter") login() }));

// ===== NAVIGASI =====
const VIEWS = { dash, list, detail, new: newV, pa, akses };
async function go(v, i) {
  view = v; if (i !== undefined) sel = i;
  $$("[data-v]").forEach(b => b.classList.toggle("on", b.dataset.v === (v === "detail" ? "list" : v)));
  const m = $("#main");
  try { m.innerHTML = await VIEWS[v]() } catch (e) { m.innerHTML = `<div class="panel glass"><h2>Terjadi kesalahan</h2><p class="mut">${esc(e.message)}</p></div>` }
  m.classList.remove("enter"); void m.offsetWidth; m.classList.add("enter"); bind(); scrollTo(0, 0);
}
function bind() {
  animate(); typing(); labelTables();
  const q = $("#q"), l = $("#lv");
  if (q) { q.oninput = () => { flt.q = q.value; refTb() }; l.onchange = () => { flt.l = l.value; refTb() } }
  const fd = $("#fd"); if (fd) fd.onchange = () => { flt.d = fd.value; refTb() };
  const pq = $("#pq"); if (pq) { pq.oninput = () => { pflt.q = pq.value; refPa() }; $("#pf").onchange = e => { pflt.d = e.target.value; refPa() }; $("#pbulk").onclick = tetapkanTerpilih; infoPilih() }
  const h = $("#hit"); if (h) h.onclick = hitung;
  const sv = $("#save"); if (sv) sv.onclick = simpan;
  const au = $("#addu"); if (au) au.onclick = tambahUser;
  const nr = $("#nr"); if (nr) nr.onchange = () => { const d = nr.value === "dosen"; $("#wd").classList.toggle("hidden", !d); $("#wu").classList.toggle("hidden", d) };
  $$("[data-sim]").forEach(r => r.oninput = () => { $("#v_" + r.dataset.sim).textContent = r.value; clearTimeout(bind.t); bind.t = setTimeout(simulasi, 250) });
}

// ===== KOMPONEN =====
const C = 2 * Math.PI * 54;
function ring(p, cls = "") {
  return `<svg class="ring ${cls} ${p.lvl}" viewBox="0 0 140 140" role="img" aria-label="Skor risiko ${p.skor} persen"><circle cx="70" cy="70" r="54" fill="none" stroke="var(--bd)" stroke-width="14"/><circle cx="70" cy="70" r="54" fill="none" stroke="var(--c)" stroke-width="14" stroke-linecap="round" class="arc" style="stroke-dasharray:0 ${C}" data-d="${C * p.skor / 100} ${C}" transform="rotate(-90 70 70)"/><text x="70" y="79" text-anchor="middle" font-size="30" font-weight="800" fill="var(--c)" data-n="${p.skor}" data-s="%">0%</text></svg>`;
}
function facs(p) {
  const mx = Math.max(...p.f.map(x => x.pts), 1);
  return p.f.length ? p.f.map(x => `<div class="fac"><div class="top"><span>${esc(x.nama)}</span><b>+${Math.round(x.pts)}</b></div><div class="tr"><i style="width:0" data-w="${x.pts / mx * 100}%"></i></div></div>`).join("") : `<p class="mut">Tidak ada faktor risiko yang menonjol.</p>`;
}
function recs(p) {
  if (!p.f.length) return `<p class="mut">Pertahankan kinerja saat ini. Tidak ada intervensi khusus yang disarankan.</p>`;
  return p.f.map((x, i) => { const r = REC[x.key]; return `<div class="rec ${x.pts >= 12 ? "hi" : r[2]}" style="animation-delay:${i * .07}s"><b>${r[0]}</b><span>${r[1]}</span></div>` }).join("");
}
function spark(a) {
  if (a.length < 2) return `<p class="mut">Belum cukup riwayat semester.</p>`;
  const w = 300, h = 110, x = i => 20 + i * (w - 40) / (a.length - 1), y = v => h - 12 - (v / 4) * (h - 30);
  return `<svg viewBox="0 0 ${w} ${h}" style="width:100%" role="img" aria-label="Grafik IPS per semester"><polyline class="spark" pathLength="1" points="${a.map((v, i) => x(i) + "," + y(v)).join(" ")}" fill="none" stroke="var(--a)" stroke-width="3" stroke-linejoin="round"/>${a.map((v, i) => `<g class="dot"><circle cx="${x(i)}" cy="${y(v)}" r="4" fill="var(--a)"/><text x="${x(i)}" y="${y(v) - 9}" text-anchor="middle" font-size="11" fill="currentColor">${v}</text></g><text x="${x(i)}" y="${h - 1}" text-anchor="middle" font-size="10" fill="var(--mut)">S${i + 1}</text>`).join("")}</svg>`;
}
const ipk = s => (s.ips.reduce((a, b) => a + b, 0) / s.ips.length);
const aiBox = t => `<div class="glass ai"><span class="badge">AI Insight</span><p class="typing" data-type="${esc(t)}"></p></div>`;

// ===== HALAMAN =====
function dash() {
  const n = DB.length;

  // Hanya gunakan data yang memiliki hasil prediksi valid.
  const valid = DB.filter(
    x => x.p && ["hi", "mid", "lo"].includes(x.p.lvl)
  );

  const c = { hi: 0, mid: 0, lo: 0 };
  valid.forEach(x => c[x.p.lvl]++);

  const top = [...valid]
    .sort((a, b) => (b.p.skor ?? 0) - (a.p.skor ?? 0))
    .slice(0, 6);

  const smts = [...new Set(DB.map(x => x.smt))]
    .sort((a, b) => a - b);

  const bars = smts.map(m => {
    const g = valid.filter(x => x.smt === m);
    const k = t => g.filter(x => x.p.lvl === t).length;

    return `<div class="row">
      <span class="k">Smt ${m}</span>
      <div class="v">
        <div class="bar" title="${g.length} mahasiswa">
          ${["hi", "mid", "lo"].map(t =>
            `<i class="${t}" style="width:0"
            data-w="${g.length ? k(t) / g.length * 100 : 0}%"></i>`
          ).join("")}
        </div>
      </div>
      <span class="mut" style="width:24px">${g.length}</span>
    </div>`;
  }).join("");

  let off = 0;

  const donut = `<svg class="donut" viewBox="0 0 140 140"
      role="img" aria-label="Sebaran risiko">
    <circle cx="70" cy="70" r="54" fill="none"
      stroke="var(--bd)" stroke-width="16"/>
    ${["hi", "mid", "lo"].map(t => {
      const len = valid.length ? c[t] / valid.length * C : 0;

      const s = `<circle class="${t}" cx="70" cy="70" r="54"
        fill="none" stroke="var(--c)" stroke-width="16"
        style="stroke-dasharray:0 ${C}"
        data-d="${Math.max(len - 2, 0)} ${C}"
        transform="rotate(${-90 + off / C * 360} 70 70)">`;

      off += len;
      return s;
    }).join("")}
    <text x="70" y="77" text-anchor="middle"
      font-size="26" font-weight="800" fill="currentColor"
      data-n="${valid.length}">0</text>
  </svg>`;

  const cnt = {};

  valid
    .filter(x => x.p.lvl === "hi" && x.p.f?.[0])
    .forEach(x => {
      const key = x.p.f[0].key;
      cnt[key] = (cnt[key] || 0) + 1;
    });

  const dom = Object.entries(cnt)
    .sort((a, b) => b[1] - a[1])[0];

  const NM = {
    ipk: "IPK rendah",
    hadir: "kehadiran rendah",
    tugas: "nilai tugas rendah",
    gagal: "SKS tidak lulus",
    tren: "penurunan IPS",
    ukt: "tunggakan UKT"
  };

  const belumPrediksi = n - valid.length;

  const insight = !n
    ? (isDosen() ? "Anda belum memiliki mahasiswa bimbingan. Hubungi Admin Akademik untuk penugasan dosen PA, atau tambahkan lewat menu Prediksi Baru." : "Belum ada data mahasiswa.")
    : !valid.length
      ? `Terdapat ${n} mahasiswa, tetapi belum ada hasil prediksi yang valid.`
      : `${c.hi} dari ${valid.length} mahasiswa yang memiliki hasil prediksi (${Math.round(c.hi / valid.length * 100)}%) berisiko tinggi.` +
        (dom
          ? ` Penyebab utama yang paling sering: ${NM[dom[0]] || dom[0]} (${dom[1]} mahasiswa).`
          : " Tidak ada pola penyebab dominan.") +
        (belumPrediksi
          ? ` ${belumPrediksi} mahasiswa belum memiliki hasil prediksi.`
          : "");

  return `<h1>${isDosen() ? "Dashboard Bimbingan Saya" : "Dashboard"}</h1>
    <p class="sub">${isDosen() ? `Ringkasan risiko akademik ${n} mahasiswa bimbingan Anda, dihitung model AI dari data MySQL.` : `Ringkasan risiko akademik ${n} mahasiswa, dihitung model AI dari data MySQL.`}</p>

    ${aiBox(insight)}

    <div class="stats">
      <div class="glass stat" style="--c:var(--a)">
        <b data-n="${n}">0</b><span>${isDosen() ? "Mahasiswa bimbingan" : "Total mahasiswa"}</span>
      </div>
      <div class="glass stat hi">
        <b data-n="${c.hi}">0</b><span>Risiko tinggi</span>
      </div>
      <div class="glass stat mid">
        <b data-n="${c.mid}">0</b><span>Risiko sedang</span>
      </div>
      <div class="glass stat lo">
        <b data-n="${c.lo}">0</b><span>Risiko rendah</span>
      </div>
    </div>

    <div class="grid2">
      <div class="glass panel">
        <h2>Sebaran risiko</h2>
        <div class="donutwrap">
          ${donut}
          <div class="legend">
            ${["hi", "mid", "lo"].map(t =>
              `<div class="${t}"><i></i>${LBL[t]}: <b>${c[t]}</b></div>`
            ).join("")}
          </div>
        </div>
        <h2 style="margin-top:18px">Per semester</h2>
        ${bars}
      </div>

      <div class="glass panel list">
        <h2>Mahasiswa prioritas</h2>
        ${top.map(x =>
          `<button class="item" data-go="${esc(x.nim)}">
            <div class="nm">${esc(x.nama)}
              <span>${esc(x.prodi)}, semester ${x.smt}</span>
            </div>
            <span class="tag ${x.p.lvl}">${x.p.skor}%</span>
          </button>`
        ).join("") ||
          `<p class="mut">Belum ada hasil prediksi yang valid.</p>`}
      </div>
    </div>`;
}



function rows() {
  return DB
    .filter(x =>
      (!flt.q ||
        (String(x.nama ?? "") + String(x.nim ?? ""))
          .toLowerCase()
          .includes(flt.q.toLowerCase())) &&
      (!flt.l || x.p?.lvl === flt.l) &&
      (!flt.d || (flt.d === "none" ? x.dosen_pa_id == null : String(x.dosen_pa_id) === flt.d))
    )
    .sort((a, b) =>
      (b.p?.skor ?? -1) - (a.p?.skor ?? -1)
    )
    .map((x, i) => {
      const ips = Array.isArray(x.ips) ? x.ips : [];

      const nilaiIPK = ips.length
        ? (
            ips.reduce((a, b) => a + Number(b), 0) /
            ips.length
          ).toFixed(2)
        : "-";

      const risiko =
        x.p && ["hi", "mid", "lo"].includes(x.p.lvl)
          ? `<span class="tag ${x.p.lvl}">
              ${LBL[x.p.lvl]} ${x.p.skor}%
            </span>`
          : `<span class="tag mid">Belum diprediksi</span>`;

      return `<tr class="click" data-go="${esc(x.nim)}"
          style="animation-delay:${Math.min(i, 15) * 0.025}s">
        <td>${esc(x.nama)}
          <div class="mut">${esc(x.nim)}</div>
        </td>
        <td>${esc(x.prodi)}</td>
        <td>${x.smt ?? "-"}</td>
        ${isDosen() ? "" : `<td>${x.dosen_pa ? esc(x.dosen_pa) : '<span class="mut">Belum ditentukan</span>'}</td>`}
        <td>${nilaiIPK}</td>
        <td>${x.hadir == null ? "-" : x.hadir + "%"}</td>
        <td>${risiko}</td>
      </tr>`;
    })
    .join("") ||
    `<tr>
      <td colspan="${isDosen() ? 6 : 7}" class="mut">
        ${!DB.length && isDosen() ? "Belum ada mahasiswa bimbingan. Hubungi Admin Akademik untuk penugasan." : "Tidak ada mahasiswa yang cocok."}
      </td>
    </tr>`;
}

async function list() {
  if (!isDosen()) await loadDosen();
  const jd = isDosen() ? `<h1>Mahasiswa Bimbingan</h1><p class="sub">Hanya mahasiswa yang dibimbing oleh Anda (${DB.length}). Klik baris untuk melihat detail, rekomendasi, dan simulasi.</p>`
    : `<h1>Data Mahasiswa</h1><p class="sub">Klik baris untuk melihat detail, rekomendasi, dan simulasi.</p>`;
  const fdosen = isDosen() ? "" : `<select id="fd" aria-label="Filter dosen PA">${optDosen(flt.d, "Semua dosen PA")}</select>`;
  return `${jd}
  <div class="tools"><input id="q" placeholder="Cari nama atau NIM" value="${esc(flt.q)}" aria-label="Cari"><select id="lv" aria-label="Filter risiko"><option value="">Semua level</option>${["hi", "mid", "lo"].map(t => `<option value="${t}"${flt.l === t ? " selected" : ""}>Risiko ${LBL[t].toLowerCase()}</option>`).join("")}</select>${fdosen}<button class="btn sec sm" data-act="pdf">Ekspor PDF</button><button class="btn sm" data-v="new">Prediksi baru</button></div>
  <div class="glass panel scroll"><table><thead><tr><th>Mahasiswa</th><th>Program studi</th><th>Smt</th>${isDosen() ? "" : "<th>Dosen PA</th>"}<th>IPK</th><th>Hadir</th><th>Risiko</th></tr></thead><tbody id="tb">${rows()}</tbody></table></div>`;
}

function detail() {
  const s = DB.find(x => x.nim === sel);

  if (!s) {
    return `<p class="mut">Mahasiswa tidak ditemukan.</p>`;
  }

  const ini = s.nama
    .split(" ")
    .map(w => w[0])
    .slice(0, 2)
    .join("");

  // Periksa apakah mahasiswa sudah memiliki hasil prediksi AI
  const p = s.p;
  const paTxt = isDosen() ? "" : `, Dosen PA: ${s.dosen_pa ? esc(s.dosen_pa) : "belum ditentukan"}`;

  if (!p) {
    return `
      <button class="btn sec sm" data-act="back">
        Kembali ke daftar
      </button>

      <div class="glass panel">
        <h2>Prediksi belum tersedia</h2>
        <p class="mut">
          Mahasiswa ini belum memiliki hasil prediksi AI.
          Pastikan data IPS per semester tersedia di database,
          atau lakukan prediksi baru.
        </p>

        <div class="head">
          <div class="av">${esc(ini)}</div>
          <div>
            <h3 style="margin:0">${esc(s.nama)}</h3>
            <span class="mut">
              ${esc(s.nim)}, ${esc(s.prodi)},
              semester ${s.smt}${s.ips.length ? ", IPK " + ipk(s).toFixed(2) : ""}${paTxt}
            </span>
          </div>
        </div>
      </div>
    `;
  }

  const sl = (k, l, v, mx, st) => `
    <div class="sl">
      <div class="top">
        <label for="s_${k}" style="margin:0">${l}</label>
        <b id="v_${k}">${v}</b>
      </div>
      <input
        id="s_${k}"
        data-sim="${k}"
        type="range"
        min="0"
        max="${mx}"
        step="${st}"
        value="${v}"
      >
    </div>
  `;

  const ipsTerakhir = s.ips?.length
    ? s.ips[s.ips.length - 1]
    : 0;

  return `
    <button class="btn sec sm" data-act="back">
      Kembali ke daftar
    </button>

    <div class="head">
      <div class="av">${esc(ini)}</div>

      <div style="flex:1">
        <h1 style="margin:0">${esc(s.nama)}</h1>
        <span class="mut">
          ${esc(s.nim)}, ${esc(s.prodi)},
          semester ${s.smt}, IPK ${ipk(s).toFixed(2)}${paTxt}
        </span>
      </div>

      <span class="tag ${p.lvl}" style="font-size:15px;padding:5px 15px">
        Risiko ${LBL[p.lvl].toLowerCase()} ${p.skor}%
      </span>

      <button
        class="btn sec sm"
        data-act="pdf1"
        data-nim="${esc(s.nim)}"
      >
        Unduh PDF
      </button>
    </div>

    ${aiBox(p.narasi)}

    <div class="grid2">
      <div class="glass panel">
        <h2>IPS per semester</h2>
        ${spark(s.ips || [])}

        <h2 style="margin-top:16px">
          Faktor penyebab (dijelaskan SHAP)
        </h2>
        ${facs(p)}
      </div>

      <div class="glass panel">
        <h2>Rekomendasi intervensi</h2>
        ${recs(p)}
      </div>
    </div>

    <div class="glass panel">
      <h2>Simulasi What-If</h2>
      <p class="mut" style="margin:0 0 6px">
        Geser untuk melihat bagaimana perubahan perilaku
        akan memengaruhi skor risiko.
      </p>

      <div class="fgrid">
        ${sl("hadir", "Kehadiran (%)", s.hadir ?? 0, 100, 1)}
        ${sl("tugas", "Nilai tugas", s.tugas ?? 0, 100, 1)}
        ${sl("sks_gagal", "SKS tidak lulus", s.sks_gagal ?? 0, 30, 1)}
        ${sl("ips_terakhir", "IPS semester terakhir", ipsTerakhir, 4, 0.05)}
      </div>

      <div class="sim" id="sim">
        ${ring(p, "sm")}
        <div>
          <div class="mut">Skor saat ini ${p.skor}%</div>
          <div>Geser slider untuk mensimulasikan.</div>
        </div>
      </div>
    </div>
  `;
}

async function simulasi() {
  const s = DB.find(x => x.nim === sel); if (!s) return;
  const body = {}; $$("[data-sim]").forEach(r => body[r.dataset.sim] = +r.value);
  try {
    const p = await api(`/mahasiswa/${encodeURIComponent(s.nim)}/simulasi`, { method: "POST", body }), d = p.skor - s.p.skor;
    $("#sim").innerHTML = `${ring(p, "sm")}<div><div class="mut">Skor simulasi (sebelumnya ${s.p.skor}%)</div><div class="delta ${d > 0 ? "up" : "down"}">${d === 0 ? "Tidak berubah" : (d > 0 ? "Naik " : "Turun ") + Math.abs(d) + " poin"}</div><span class="tag ${p.lvl}">Risiko ${LBL[p.lvl].toLowerCase()}</span></div>`;
    animate();
  } catch (e) { toast(e.message) }
}
async function newV() {
  if (!isDosen()) await loadDosen();
  const F = (id, l, v, t = "text", ex = "") => `<div><label for="${id}">${l}</label><input id="${id}" type="${t}" value="${v}" ${ex}></div>`;
  return `<h1>Prediksi Baru</h1><p class="sub">Isi data akademik, hitung risiko dengan model AI, lalu simpan ke database MySQL.${isDosen() ? " Mahasiswa yang disimpan otomatis menjadi bimbingan Anda." : ""}</p>
  <div class="grid2"><div class="glass panel"><h2>Data mahasiswa</h2><div class="fgrid">
  ${F("fn", "Nama", "")}${F("fm", "NIM (angka)", "", "text", 'inputmode="numeric"')}
  <div><label for="fp">Program studi</label><select id="fp">${PRODI.map(p => `<option>${p}</option>`).join("")}</select></div>${F("fs", "Semester saat ini", 4, "number", 'min="1" max="14"')}
  <div style="grid-column:1/-1">${F("fi", "IPS per semester (pisahkan koma)", "2.4, 2.1, 1.8")}</div>
  ${F("fh", "Kehadiran (%)", 62, "number", 'min="0" max="100"')}${F("ft", "Nilai tugas rata-rata", 58, "number", 'min="0" max="100"')}
  ${isDosen() ? "" : `<div style="grid-column:1/-1"><label for="fpa">Dosen PA pembimbing</label><select id="fpa">${optDosen("")}</select></div>`}
  ${F("fg", "SKS tidak lulus", 6, "number", 'min="0"')}<div><label for="fu">Tunggakan UKT</label><select id="fu"><option value="1">Ya</option><option value="0">Tidak</option></select></div></div>
  <div class="err" id="ferr" role="alert"></div><button class="btn" id="hit"><span>Hitung risiko</span></button></div>
  <div class="glass panel" id="res"><h2>Hasil prediksi</h2><p class="mut">Hasil, penjelasan, dan rekomendasi muncul di sini.</p></div></div>`;
}
async function hitung() {
  const g = id => $("#" + id).value.trim(), ips = g("fi").split(/[,\s;]+/).filter(Boolean).map(Number);
  const a = { ips, hadir: +g("fh"), tugas: +g("ft"), sks_gagal: +g("fg"), ukt: +g("fu") };
  if (!ips.length || ips.some(v => isNaN(v) || v < 0 || v > 4) || [a.hadir, a.tugas].some(v => isNaN(v) || v < 0 || v > 100) || isNaN(a.sks_gagal) || a.sks_gagal < 0)
    return $("#ferr").textContent = "Periksa isian: IPS 0-4, kehadiran dan tugas 0-100, SKS tidak boleh kosong.";
  $("#ferr").textContent = "";
  try {
    const p = await api("/predict", { method: "POST", body: a });
    draft = { nim: g("fm"), nama: g("fn"), prodi: g("fp"), smt: +g("fs"), ...a, p };
    if (!isDosen()) draft.dosen_pa_id = $("#fpa").value ? +$("#fpa").value : null;
    $("#res").innerHTML = `<h2>Hasil prediksi</h2>${ring(p)}<p class="c" style="margin:8px 0 12px"><span class="tag ${p.lvl}" style="font-size:15px;padding:4px 14px">Risiko ${LBL[p.lvl].toLowerCase()}</span></p>${aiBox(p.narasi)}<h2>Faktor penyebab utama</h2>${facs(p)}<h2 style="margin-top:14px">Rekomendasi</h2>${recs(p)}<button class="btn sm" id="save" style="margin-top:8px"><span>Simpan ke database</span></button>`;
    bind();
  } catch (e) { $("#ferr").textContent = e.message }
}
async function simpan() {
  const { p, ...body } = draft;
  try { await api("/mahasiswa", { method: "POST", body }); await loadDB(); toast("Tersimpan ke database MySQL"); go("detail", body.nim) }
  catch (e) { toast(e.message) }
}

// ===== PEMBAGIAN DOSEN PA (admin) =====
function paRows() {
  const k = pflt.q.trim().toLowerCase();
  const data = DB.filter(x => (!k || (x.nama + x.nim).toLowerCase().includes(k)) &&
    (!pflt.d || (pflt.d === "none" ? x.dosen_pa_id == null : String(x.dosen_pa_id) === pflt.d)));
  return data.map(x => `<tr>
    <td><input type="checkbox" class="pachk" data-nim="${esc(x.nim)}" aria-label="Pilih ${esc(x.nama)}"${PASEL.has(x.nim) ? " checked" : ""}></td>
    <td>${esc(x.nama)}<div class="mut">${esc(x.nim)}</div></td>
    <td>${esc(x.prodi)}</td><td>${x.smt}</td>
    <td><select class="pasel" data-nim="${esc(x.nim)}" aria-label="Dosen PA ${esc(x.nama)}">${optDosen(x.dosen_pa_id)}</select></td>
  </tr>`).join("") || `<tr><td colspan="5" class="mut">Tidak ada mahasiswa yang cocok.</td></tr>`;
}
function infoPilih() { const e = $("#pinfo"); if (e) e.textContent = PASEL.size + " mahasiswa dipilih" }
async function pa() {
  await Promise.all([loadDB(), loadDosen()]);
  const kartu = DOSEN.dosen.map(d => `<div class="glass stat" style="--c:var(--a)"><b data-n="${d.jumlah}">0</b><span>${esc(d.nama)}${d.aktif ? "" : " (nonaktif)"}<br>NIDN ${esc(d.nidn || "-")}</span></div>`).join("") +
    `<div class="glass stat mid"><b data-n="${DOSEN.tanpa_dosen}">0</b><span>Belum ada dosen PA</span></div>`;
  return `<h1>Pembagian Dosen PA</h1><p class="sub">Tetapkan dosen PA untuk tiap mahasiswa. Dosen hanya dapat melihat dan mengelola mahasiswa bimbingannya sendiri.</p>
  <div class="stats" style="grid-template-columns:repeat(auto-fit,minmax(190px,1fr))">${kartu}</div>
  <div class="glass panel">
    <div class="tools"><input id="pq" placeholder="Cari nama atau NIM" value="${esc(pflt.q)}" aria-label="Cari"><select id="pf" aria-label="Filter dosen PA">${optDosen(pflt.d, "Semua mahasiswa")}</select></div>
    <div class="tools" style="align-items:center"><label style="margin:0;display:flex;gap:8px;align-items:center"><input type="checkbox" id="pall" style="width:auto"> Pilih semua yang tampil</label><span class="mut" id="pinfo"></span>
      <select id="pbulkd" aria-label="Dosen PA tujuan">${optDosen("")}</select><button class="btn sm" id="pbulk">Tetapkan ke yang dipilih</button></div>
    <div class="scroll"><table><thead><tr><th></th><th>Mahasiswa</th><th>Program studi</th><th>Smt</th><th>Dosen PA</th></tr></thead><tbody id="ptb">${paRows()}</tbody></table></div>
  </div>`;
}
async function tetapkan(nims, val) {
  try {
    const dosen_pa_id = val ? +val : null;
    if (nims.length === 1) await api("/admin/mahasiswa/" + encodeURIComponent(nims[0]) + "/dosen-pa", { method: "PATCH", body: { dosen_pa_id } });
    else await api("/admin/mahasiswa/dosen-pa", { method: "POST", body: { nim: nims, dosen_pa_id } });
    toast("Dosen PA diperbarui"); PASEL.clear(); go("pa");
  } catch (e) { toast(e.message); go("pa") }
}
function tetapkanTerpilih() {
  if (!PASEL.size) return toast("Pilih mahasiswa terlebih dahulu.");
  const v = $("#pbulkd").value;
  if (!v && !confirm("Lepas dosen PA dari " + PASEL.size + " mahasiswa terpilih?")) return;
  tetapkan([...PASEL], v);
}

// ===== MANAJEMEN AKSES (admin) =====
async function akses() {
  const [us, lg] = await Promise.all([api("/admin/users"), api("/admin/log")]);
  return `<h1>Manajemen Akses</h1><p class="sub">Hanya akun di daftar ini yang bisa masuk. Setiap percobaan masuk tercatat.</p>
  <div class="glass panel"><h2>Tambah akun</h2><div class="addu">
  <div><label for="nr">Peran</label><select id="nr"><option value="dosen">Dosen</option><option value="admin">Admin Akademik</option></select></div>
  <div id="wd"><label for="nd">NIDN (10 digit)</label><input id="nd" inputmode="numeric" maxlength="10" autocomplete="off"></div><div id="wu" class="hidden"><label for="nu">Username</label><input id="nu" autocomplete="off"></div>
  <div><label for="nn">Nama lengkap</label><input id="nn"></div>
  <div><label for="np">Kata sandi (min. 8)</label><input id="np" type="password" autocomplete="new-password"></div><button class="btn sm" id="addu">Tambah</button></div><div class="err" id="uerr"></div></div>
  <div class="glass panel scroll" style="margin-top:16px"><h2>Akun terdaftar</h2><table><thead><tr><th>Username</th><th>NIDN</th><th>Nama</th><th>Peran</th><th>Status</th><th>Terakhir masuk</th><th></th></tr></thead><tbody>${us.map(u => `<tr><td>${esc(u.username)}</td><td>${esc(u.nidn || "-")}</td><td>${esc(u.nama)}</td><td>${ROLE[u.role]}</td><td><span class="tag ${u.aktif ? "lo" : "hi"}">${u.aktif ? "Aktif" : "Nonaktif"}</span>${u.terkunci_hingga && new Date(u.terkunci_hingga) > new Date() ? ' <span class="tag mid">Terkunci</span>' : ""}</td><td>${tgl(u.last_login)}</td><td style="white-space:nowrap"><button class="btn sec sm" data-act="reset" data-id="${u.id}" data-u="${esc(u.username)}">Reset sandi</button> <button class="btn sec sm" data-act="toggle" data-id="${u.id}" data-on="${u.aktif ? 0 : 1}">${u.aktif ? "Nonaktifkan" : "Aktifkan"}</button></td></tr>`).join("")}</tbody></table></div>
  <div class="glass panel scroll" style="margin-top:16px"><h2>Log akses (100 terakhir)</h2><table><thead><tr><th>Waktu</th><th>Username</th><th>IP</th><th>Hasil</th><th>Keterangan</th></tr></thead><tbody>${lg.map(l => `<tr><td>${tgl(l.waktu)}</td><td>${esc(l.username)}</td><td>${esc(l.ip)}</td><td><span class="tag ${l.berhasil ? "lo" : "hi"}">${l.berhasil ? "Berhasil" : "Gagal"}</span></td><td>${esc(l.keterangan)}</td></tr>`).join("")}</tbody></table></div>`;
}
async function tambahUser() {
  const g = id => $("#" + id).value, r = g("nr");
  if (r === "dosen" && !/^\d{10}$/.test(g("nd").trim())) return $("#uerr").textContent = "NIDN harus 10 digit angka.";
  const body = { role: r, nama: g("nn").trim(), password: g("np"), ...(r === "dosen" ? { nidn: g("nd").trim() } : { username: g("nu").trim() }) };
  try { await api("/admin/users", { method: "POST", body }); toast("Akun ditambahkan"); go("akses") }
  catch (e) { $("#uerr").textContent = e.message }
}
async function ubahUser(id, body) {
  try { await api("/admin/users/" + id, { method: "PATCH", body }); toast("Perubahan disimpan"); go("akses") } catch (e) { toast(e.message) }
}

// ===== ANIMASI =====
function animate() {
  $$("[data-w]").forEach(e => { const w = e.dataset.w; delete e.dataset.w; RM ? e.style.width = w : requestAnimationFrame(() => requestAnimationFrame(() => e.style.width = w)) });
  $$("[data-d]").forEach(e => { const d = e.dataset.d; delete e.dataset.d; RM ? e.style.strokeDasharray = d : requestAnimationFrame(() => requestAnimationFrame(() => e.style.strokeDasharray = d)) });
  $$("[data-n]").forEach(e => {
    const n = +e.dataset.n, s = e.dataset.s || ""; delete e.dataset.n;
    if (RM) { e.textContent = n + s; return }
    const t0 = performance.now();
    (function f(t) { const k = Math.min(1, (t - t0) / 900); e.textContent = Math.round(n * (1 - Math.pow(1 - k, 3))) + s; if (k < 1) requestAnimationFrame(f) })(t0);
  });
}
function typing() {
  $$("[data-type]").forEach(e => {
    const t = e.dataset.type; delete e.dataset.type;
    if (RM) { e.textContent = t; e.classList.remove("typing"); return }
    let i = 0; (function f() { e.textContent = t.slice(0, ++i); if (i < t.length) setTimeout(f, 14); else e.classList.remove("typing") })();
  });
}

// ===== PARTIKEL LATAR (halaman login) =====
(function () {
  const cv = $("#bg"), cx = cv.getContext("2d"); if (RM) return;
  let w, h, P = [];
  const size = () => { w = cv.width = innerWidth; h = cv.height = innerHeight; P = Array.from({ length: Math.min(70, Math.floor(w * h / 18000)) }, () => ({ x: Math.random() * w, y: Math.random() * h, vx: (Math.random() - .5) * .35, vy: (Math.random() - .5) * .35 })) };
  size(); addEventListener("resize", size);
  (function loop() {
    if (!document.hidden) {
      cx.clearRect(0, 0, w, h);
      const dark = document.documentElement.dataset.theme !== "light", col = dark ? "150,200,255" : "60,90,160";
      P.forEach((a, i) => {
        a.x = (a.x + a.vx + w) % w; a.y = (a.y + a.vy + h) % h;
        cx.fillStyle = `rgba(${col},.55)`; cx.beginPath(); cx.arc(a.x, a.y, 1.6, 0, 7); cx.fill();
        for (let j = i + 1; j < P.length; j++) { const b = P[j], d = Math.hypot(a.x - b.x, a.y - b.y); if (d < 120) { cx.strokeStyle = `rgba(${col},${.16 * (1 - d / 120)})`; cx.beginPath(); cx.moveTo(a.x, a.y); cx.lineTo(b.x, b.y); cx.stroke() } }
      });
    }
    requestAnimationFrame(loop);
  })();
})();

// ===== MULAI =====
if (token) api("/auth/me").then(u => { me = u; return enter() }).catch(() => logout());


