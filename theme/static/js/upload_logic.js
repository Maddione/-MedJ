const API = { ocr: "/api/upload/ocr/", analyze: "/api/upload/analyze/", confirm: "/api/upload/confirm/", suggest: "/api/events/suggest/" };

function el(id) { return document.getElementById(id); }
function show(x) { if (x) x.classList.remove("hidden"); }
function hide(x) { if (x) x.classList.add("hidden"); }
function seth(x, h) { if (x) x.innerHTML = h || ""; }
function setv(x, v) { if (x) x.value = v || ""; }
function dis(x, f) { if (!x) return; x.disabled = !!f; x.classList.toggle("opacity-50", !!f); x.classList.toggle("cursor-not-allowed", !!f); }
function getCSRF() { const t = document.querySelector('input[name="csrfmiddlewaretoken"]'); if (t && t.value) return t.value; const m = document.cookie.match(/(?:^|;)\s*csrftoken=([^;]+)/); return m ? decodeURIComponent(m[1]) : ""; }
function ensureMeta() { let m = el("workMeta"); if (!m) { const ta = el("workText"); if (ta && ta.parentElement) { m = document.createElement("div"); m.id = "workMeta"; m.className = "text-xs text-gray-500 mt-1"; ta.parentElement.insertBefore(m, ta); } } return m; }
function ensureUXStyles() { if (document.getElementById("uxUploadInject")) return; const s = document.createElement("style"); s.id = "uxUploadInject"; s.textContent = `.btn[aria-disabled="true"]{opacity:.5;cursor:not-allowed;pointer-events:none}.btn.btn-armed:hover{filter:brightness(1.05)}`; document.head.appendChild(s); }

let CURRENT_FILE = null;
let CURRENT_FILE_KIND = "";
let CURRENT_FILE_URL = null;
let ORIGINAL_OCR_TEXT = "";
let LAB_EDIT_MODE = false;
let CLASS_LOCK = false;
let DOC_LOCK = false;
let FILE_KIND_LOCK = false;
let ANALYZED_READY = false;

function picks() {
  return {
    category: (el("sel_category") || {}).value || "",
    specialty: (el("sel_specialty") || {}).value || "",
    docType: (el("sel_doc_type") || {}).value || "",
    fileKind: CURRENT_FILE_KIND || "",
    file: CURRENT_FILE,
    eventId: (el("existingEventSelect") || {}).value || ""
  };
}
function currentTags() { const p = picks(); return { category_id: p.category || "", specialty_id: p.specialty || "", doc_type_id: p.docType || "", file_kind: p.fileKind || "" }; }

function lockDocType() { DOC_LOCK = true; dis(el("sel_doc_type"), true); }
function lockClassification() { CLASS_LOCK = true; ["sel_category","sel_specialty","sel_doc_type","file_kind"].forEach(id => dis(el(id), true)); }

function stage() { const p = picks(); if (!p.file) return "choose_file"; const text = (el("workText") || {}).value || ""; if (!text.trim()) return "ocr"; return "analyze"; }
function updateButtons() { const s = stage(); const bOCR = el("btnOCR"); const bAna = el("btnAnalyze"); const bCfm = el("btnConfirm"); if (bOCR) (s === "ocr") ? show(bOCR) : hide(bOCR); if (bAna) (s !== "ocr") ? show(bAna) : hide(bAna); if (bCfm) (ANALYZED_READY ? show(bCfm) : hide(bCfm)); }

function setBusy(on) { const o = el("loadingOverlay"); if (on) show(o); else hide(o); }
function showError(msg) { const box = el("errorBox"); if (box) { box.textContent = msg || "Грешка."; show(box); } }
function clearError() { const box = el("errorBox"); if (box) { box.textContent = ""; hide(box); } }

function renderPreview() {
  const wrap = el("previewBlock");
  const img = el("previewImg");
  const pdf = el("previewPDF");
  const emb = el("previewEmbed");
  const meta = el("fileMeta");
  const badge = el("fileNameBadge");
  if (!CURRENT_FILE) { hide(wrap); if (meta) seth(meta, ""); if (badge) badge.classList.add("hidden"); return; }
  if (CURRENT_FILE_URL) { URL.revokeObjectURL(CURRENT_FILE_URL); CURRENT_FILE_URL = null; }
  CURRENT_FILE_URL = URL.createObjectURL(CURRENT_FILE);
  const name = CURRENT_FILE.name || "file";
  const type = (CURRENT_FILE.type || "").toLowerCase();
  const sizeKB = Math.round((CURRENT_FILE.size || 0) / 1024);
  if (type.startsWith("image/")) { if (img) { img.src = CURRENT_FILE_URL; show(img); } hide(pdf); }
  else if (type === "application/pdf" || name.toLowerCase().endsWith(".pdf")) { if (emb) emb.src = CURRENT_FILE_URL; hide(img); show(pdf); }
  else { hide(img); hide(pdf); }
  show(wrap);
  if (meta) meta.textContent = `${name} • ${sizeKB} KB • ${type || "unknown"}`;
  if (badge) { badge.textContent = name; badge.classList.remove("hidden"); }
}

function handleFileInputChange() {
  const fi = el("file_input");
  const kind = el("file_kind");
  CURRENT_FILE = fi && fi.files ? fi.files[0] : null;
  CURRENT_FILE_KIND = (kind && kind.value) || "";
  FILE_KIND_LOCK = true;
  dis(kind, true);
  ANALYZED_READY = false;
  renderPreview();
  lockDocType();
  updateDropdownFlow();
  updateButtons();
}

function updateDropdownFlow() {
  const p = picks();
  const cat = el("sel_category");
  const spc = el("sel_specialty");
  const doc = el("sel_doc_type");
  const kind = el("file_kind");
  const file = el("file_input");
  const choose = el("chooseFileBtn");
  if (CLASS_LOCK) { dis(cat, true); dis(spc, true); dis(doc, true); dis(kind, true); dis(file, false); if (choose) { choose.setAttribute("aria-disabled","true"); choose.classList.remove("btn-armed"); } updateButtons(); return; }
  const readySpc = !!p.category;
  const readyDoc = readySpc && !!p.specialty;
  const readyKind = readyDoc && !!p.docType;
  const readyFile = readyKind && !!p.fileKind;
  dis(cat, false);
  dis(spc, !readySpc); if (!readySpc) setv(spc, "");
  dis(doc, !readyDoc || DOC_LOCK); if (!readyDoc && !DOC_LOCK) setv(doc, "");
  if (FILE_KIND_LOCK) dis(kind, true); else { dis(kind, !readyKind); if (!readyKind) { setv(kind, ""); CURRENT_FILE_KIND = ""; } }
  dis(file, !readyFile);
  if (choose) { if (readyFile) { choose.removeAttribute("aria-disabled"); choose.classList.add("btn-armed"); } else { choose.setAttribute("aria-disabled","true"); choose.classList.remove("btn-armed"); } }
  updateButtons();
}

async function suggestIfReady() {
  const wrap = el("existingEventWrap");
  const select = el("existingEventSelect");
  const p = picks();
  if (!(p.category && p.specialty && p.docType && p.fileKind)) { if (wrap) hide(wrap); if (select) seth(select, ""); return; }
  try {
    const qs = new URLSearchParams({ category_id: p.category, specialty_id: p.specialty, doc_type_id: p.docType, file_kind: p.fileKind });
    const res = await fetch(API.suggest + "?" + qs.toString(), { method: "GET", credentials: "same-origin" });
    if (!res.ok) throw new Error("suggest_failed");
    const data = await res.json();
    const items = data.events || [];
    if (!items.length) { if (wrap) hide(wrap); if (select) seth(select, ""); return; }
    const opts = ['<option value="">—</option>'].concat(items.map(x => { const vid = x.id != null ? String(x.id) : ""; const label = x.title || x.name || x.display_name || vid; return `<option value="${vid}">${label}</option>`; }));
    if (select) seth(select, opts.join(""));
    if (wrap) show(wrap);
  } catch (_) { if (wrap) hide(wrap); if (select) seth(select, ""); }
}

function parseLabs(text) {
  const lines = (text || "").split(/\r?\n/).map(s => s.trim()).filter(Boolean);
  const items = [];
  const kvRe = /^([A-Za-zА-Яа-я0-9\.\(\)\/\-\s]+?)\s+([\-+]?\d+(?:[\.,]\d+)?)(?:\s*([A-Za-zμ%\/\.\-\^\d×]+))?$/;
  const refRe = /^(\d+(?:[\.,]\d+)?)\s*[-–]\s*(\d+(?:[\.,]\d+)?)/;
  let refBlock = [];
  for (let i = 0; i < lines.length; i++) { if (/REFERENCE\s*INTERVAL/i.test(lines[i])) { refBlock = lines.slice(i + 1); break; } }
  for (const ln of lines) {
    if (/^(tests|result|flag|units|reference|comp\.|panel)/i.test(ln)) continue;
    const m = ln.match(kvRe);
    if (!m) continue;
    const name = m[1].replace(/\s{2,}/g, " ").trim();
    const val = m[2].replace(",", ".");
    const unit = (m[3] || "").trim();
    items.push({ name, value: parseFloat(val), unit: unit || null, ref_low: null, ref_high: null });
  }
  if (refBlock.length) {
    const refs = refBlock.map(s => s.match(refRe)?.slice(1, 3) || null).filter(Boolean);
    for (let i = 0; i < items.length && i < refs.length; i++) {
      const [low, high] = refs[i];
      items[i].ref_low = parseFloat(String(low).replace(",", "."));
      items[i].ref_high = parseFloat(String(high).replace(",", "."));
    }
  }
  return items;
}

function renderLabTable(items) {
  const wrap = el("labWrap");
  const slot = el("labTableSlot");
  const sum = el("labSummary");
  if (!wrap || !slot) return;
  const rows = (items || []).map(x => {
    const inRef = (x.ref_low != null && x.ref_high != null && typeof x.value === "number") ? (x.value >= x.ref_low && x.value <= x.ref_high) : null;
    const cls = inRef === false ? ' style="color:#b91c1c;font-weight:600;"' : "";
    const unit = x.unit ? x.unit : "";
    const ref = (x.ref_low != null && x.ref_high != null) ? `${x.ref_low} - ${x.ref_high}` : "";
    return `<tr><td>${x.name}</td><td${cls}>${x.value}</td><td>${unit}</td><td>${ref}</td></tr>`;
  });
  const html = `<table class="tbl"><thead><tr><th>Показател</th><th>Стойност</th><th>Ед.</th><th>Реф.</th></tr></thead><tbody>${rows.join("")}</tbody></table>`;
  seth(slot, rows.length ? html : "");
  if (sum) seth(sum, rows.length ? `${rows.length} показателя` : "");
  show(wrap);
  setTableEditable(LAB_EDIT_MODE);
}

function setTableEditable(on) {
  const tbl = document.querySelector("#labTableSlot table");
  if (!tbl) return;
  const rows = tbl.querySelectorAll("tbody tr");
  rows.forEach((r) => {
    [...r.cells].forEach((c, idx) => {
      if (idx <= 3) {
        c.contentEditable = on ? "true" : "false";
        c.classList.toggle("ring", on);
        c.classList.toggle("ring-1", on);
        c.classList.toggle("ring-offset-1", on);
      }
    });
  });
}

function getLabTableData() {
  const tbl = document.querySelector("#labTableSlot table");
  if (!tbl) return [];
  const rows = tbl.querySelectorAll("tbody tr");
  const out = [];
  rows.forEach((r) => {
    const name = (r.cells[0]?.innerText || "").trim();
    const valRaw = (r.cells[1]?.innerText || "").trim().replace(",", ".");
    const value = valRaw && !isNaN(Number(valRaw)) ? Number(valRaw) : valRaw;
    const unit = (r.cells[2]?.innerText || "").trim();
    const ref = (r.cells[3]?.innerText || "").trim();
    let ref_low = null, ref_high = null;
    if (ref && /-/.test(ref)) {
      const [lo, hi] = ref.split("-").map((s) => s.trim().replace(",", "."));
      const loN = Number(lo), hiN = Number(hi);
      ref_low = isNaN(loN) ? null : loN;
      ref_high = isNaN(hiN) ? null : hiN;
    }
    out.push({ name, value, unit, ref_low, ref_high });
  });
  return out;
}

function refreshTableFromText() {
  const t = (el("workText")?.value || "");
  const items = parseLabs(t);
  renderLabTable(items);
}

function syncTableToText() {
  const items = getLabTableData();
  const lines = items.map((x) => {
    const v = (typeof x.value === "number" && isFinite(x.value)) ? x.value : (x.value || "");
    const u = x.unit ? ` ${x.unit}` : "";
    const ref = (x.ref_low != null && x.ref_high != null) ? ` ${x.ref_low}-${x.ref_high}` : "";
    return `${x.name} ${v}${u}${ref}`;
  });
  const ta = el("workText");
  if (ta) ta.value = lines.join("\n");
}

function ensureLabControls() {
  const wrap = el("labWrap");
  if (!wrap) return;
  let bar = el("labControls");
  if (!bar) {
    bar = document.createElement("div");
    bar.id = "labControls";
    bar.className = "flex gap-2 mb-2";
    bar.innerHTML = `
      <button id="btnRefreshTable" class="btn">Обнови таблицата</button>
      <button id="btnEditTable" class="btn">Редакция на таблицата</button>
      <button id="btnSyncToText" class="btn">Синхронизирай към текст</button>
      <button id="btnRevertOCR" class="btn">Върни OCR текста</button>
    `;
    wrap.insertBefore(bar, wrap.firstChild);
  }
  el("btnRefreshTable").onclick = (e) => { e.preventDefault(); refreshTableFromText(); };
  el("btnEditTable").onclick = (e) => { e.preventDefault(); LAB_EDIT_MODE = !LAB_EDIT_MODE; setTableEditable(LAB_EDIT_MODE); e.currentTarget.textContent = LAB_EDIT_MODE ? "Изход от редакция" : "Редакция на таблицата"; };
  el("btnSyncToText").onclick = (e) => { e.preventDefault(); syncTableToText(); };
  el("btnRevertOCR").onclick = (e) => { e.preventDefault(); if (!ORIGINAL_OCR_TEXT) return; const ta = el("workText"); setv(ta, ORIGINAL_OCR_TEXT); renderLabTable(parseLabs(ORIGINAL_OCR_TEXT)); ANALYZED_READY = false; updateButtons(); };
}

async function doOCR() {
  clearError();
  const p = picks();
  if (!p.file) { showError("Моля изберете файл."); return; }
  setBusy(true);
  const fd = new FormData();
  fd.append("file", p.file);
  fd.append("file_kind", p.fileKind || "");
  try {
    const res = await fetch(API.ocr, { method: "POST", headers: { "X-CSRFToken": getCSRF() }, credentials: "same-origin", body: fd });
    const ct = (res.headers.get("content-type") || "").toLowerCase();
    const data = ct.includes("application/json") ? await res.json() : { error: "invalid_response" };
    if (data.error) { showError("OCR неуспешен: " + (data.detail || data.error)); return; }
    const text = (data.ocr_text || "").toString();
    if (!text.trim()) { showError("Празен OCR резултат."); return; }
    const area = el("workText");
    area.removeAttribute("disabled");
    setv(area, text);
    ORIGINAL_OCR_TEXT = text;
    const metaEl = ensureMeta();
    const engine = (data?.telemetry?.engine_chosen) || data.engine || "";
    const rid = data.rid || data?.telemetry?.rid || "";
    if (metaEl) metaEl.textContent = engine ? `OCR: ${engine}${rid ? " • " + rid : ""}` : "";
    const labs = parseLabs(text);
    renderLabTable(labs);
    ANALYZED_READY = false;
    updateButtons();
  } catch (_) { showError("OCR грешка при заявката."); }
  finally { setBusy(false); }
}

async function doAnalyze() {
  clearError();
  const area = el("workText");
  const text = (area ? area.value : "") || "";
  if (!text.trim()) { showError("Липсва текст за анализ."); return; }
  setBusy(true);
  try {
    lockClassification();
    const res = await fetch(API.analyze, { method: "POST", headers: { "Content-Type": "application/json", "X-CSRFToken": getCSRF() }, credentials: "same-origin", body: JSON.stringify({ text, ...currentTags() }) });
    const data = await res.json();
    const summary = (data.summary || "").toString();
    if (!summary.trim()) { showError("Празен резултат от анализ."); return; }
    setv(area, summary);
    const labs = parseLabs(summary);
    renderLabTable(labs);
    ANALYZED_READY = true;
    updateButtons();
  } catch (_) { showError("Грешка при анализ."); }
  finally { setBusy(false); }
}

async function doConfirm() {
  clearError();
  const area = el("workText");
  const text = (area ? area.value : "") || "";
  if (!text.trim()) { showError("Няма данни за запис."); return; }
  setBusy(true);
  try {
    lockClassification();
    const res = await fetch(API.confirm, { method: "POST", headers: { "Content-Type": "application/json", "X-CSRFToken": getCSRF() }, credentials: "same-origin", body: JSON.stringify({ text, ...currentTags() }) });
    if (!res.ok) throw new Error("confirm_failed");
  } catch (_) { showError("Грешка при запис."); }
  finally { setBusy(false); }
}

function bindUI() {
  ensureUXStyles();
  const form = el("uploadForm");
  if (form) {
    form.setAttribute("action", "#");
    form.setAttribute("method", "post");
    form.setAttribute("novalidate", "novalidate");
    form.addEventListener("submit", (e) => { e.preventDefault(); return false; });
  }
  const cat = el("sel_category");
  const spc = el("sel_specialty");
  const doc = el("sel_doc_type");
  const kind = el("file_kind");
  const fi = el("file_input");
  const choose = el("chooseFileBtn");
  if (cat) cat.addEventListener("change", () => { updateDropdownFlow(); suggestIfReady(); clearError(); });
  if (spc) spc.addEventListener("change", () => { updateDropdownFlow(); suggestIfReady(); clearError(); });
  if (doc) doc.addEventListener("change", () => { updateDropdownFlow(); suggestIfReady(); clearError(); });
  if (kind) kind.addEventListener("change", () => { if (!FILE_KIND_LOCK) { CURRENT_FILE_KIND = kind.value || ""; updateDropdownFlow(); suggestIfReady(); clearError(); } });
  if (choose) choose.addEventListener("click", (e) => { e.preventDefault(); if (choose.getAttribute("aria-disabled")==="true") return; if (fi) fi.click(); });
  if (fi) fi.addEventListener("change", handleFileInputChange);
  const bOCR = el("btnOCR");
  const bAna = el("btnAnalyze");
  const bCfm = el("btnConfirm");
  if (bOCR) bOCR.addEventListener("click", (e) => { e.preventDefault(); doOCR(); });
  if (bAna) bAna.addEventListener("click", (e) => { e.preventDefault(); doAnalyze(); });
  if (bCfm) bCfm.addEventListener("click", (e) => { e.preventDefault(); doConfirm(); });
  ensureLabControls();
  ensureMeta();
  updateDropdownFlow();
  updateButtons();
}

document.addEventListener("DOMContentLoaded", bindUI);
