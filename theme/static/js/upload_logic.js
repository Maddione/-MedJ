const API = { ocr: "/api/upload/ocr/", analyze: "/api/upload/analyze/", confirm: "/api/upload/confirm/", suggest: "/api/events/suggest/" };

function el(id) { return document.getElementById(id); }
function show(x) { if (x) x.classList.remove("hidden"); }
function hide(x) { if (x) x.classList.add("hidden"); }
function seth(x, h) { if (x) x.innerHTML = h || ""; }
function setv(x, v) { if (x) x.value = v || ""; }
function dis(x, f) { if (!x) return; x.disabled = !!f; x.classList.toggle("opacity-50", !!f); x.classList.toggle("cursor-not-allowed", !!f); }
function getCSRF() { const t = document.querySelector('input[name="csrfmiddlewaretoken"]'); if (t && t.value) return t.value; const m = document.cookie.match(/(?:^|;)\s*csrftoken=([^;]+)/); return m ? decodeURIComponent(m[1]) : ""; }

let CURRENT_FILE = null;
let CURRENT_FILE_KIND = "";
let CURRENT_FILE_URL = null;
let ORIGINAL_OCR_TEXT = "";
let OCR_META = {};
let ANALYSIS = { summary: "", data: { tables: [], blood_test_results: [], suggested_tags: [] } };
let LAB_EDIT_MODE = false;
let CLASS_LOCK = false;
let DOC_LOCK = false;
let FILE_KIND_LOCK = false;
let ANALYZED_READY = false;

function ensureUXStyles() {
  if (document.getElementById("uxUploadInject")) return;
  const s = document.createElement("style");
  s.id = "uxUploadInject";
  s.textContent = ".btn[aria-disabled=\"true\"]{opacity:.5;cursor:not-allowed;pointer-events:none}.btn.btn-armed:hover{filter:brightness(1.05)}";
  document.head.appendChild(s);
}

function picks() {
  return {
    category: (el("sel_category") || {}).value || "",
    specialty: (el("sel_specialty") || {}).value || "",
    docType: (el("sel_doc_type") || {}).value || "",
    fileKind: (el("file_kind") || {}).value || "",
    file: (el("file_input") && el("file_input").files ? el("file_input").files[0] : null) || CURRENT_FILE,
    eventId: (el("existingEventSelect") || {}).value || ""
  };
}

function picksPayload() {
  const p = picks();
  return { category_id: p.category || "", specialty_id: p.specialty || "", doc_type_id: p.docType || "", file_kind: p.fileKind || "", event_id: p.eventId || "" };
}

function requiredTagsReady() { const p = picks(); return !!(p.category && p.specialty && p.docType); }
function pipelineReady() { const p = picks(); return !!(p.category && p.specialty && p.docType && p.fileKind); }

function lockDocType() { DOC_LOCK = true; dis(el("sel_doc_type"), true); }
function lockClassification() { CLASS_LOCK = true; ["sel_category","sel_specialty","sel_doc_type","file_kind"].forEach(id => dis(el(id), true)); }

function stepLabelNode() {
  let n = document.querySelector('label[for="workText"]');
  if (!n) n = el("workMeta");
  if (!n) {
    const ta = el("workText");
    if (ta && ta.parentElement) {
      n = document.createElement("div");
      n.id = "workMeta";
      n.className = "text-xs text-gray-600 mb-1";
      ta.parentElement.insertBefore(n, ta);
    }
  }
  return n;
}

function setStepLabel(text) { const n = stepLabelNode(); if (n) n.textContent = text || ""; }

function stage() {
  const p = picks();
  if (!p.file) return "choose";
  const text = (el("workText") || {}).value || "";
  if (!text.trim()) return "ocr";
  return "analyze";
}

function updateButtons() {
  const s = stage();
  const bOCR = el("btnOCR");
  const bAna = el("btnAnalyze");
  const bCfm = el("btnConfirm");
  if (bOCR) (s === "ocr" && pipelineReady()) ? show(bOCR) : hide(bOCR);
  if (bAna) (s === "analyze" && requiredTagsReady() && !ANALYZED_READY) ? show(bAna) : hide(bAna);
  if (bCfm) (ANALYZED_READY && requiredTagsReady()) ? show(bCfm) : hide(bCfm);
}

function setBusy(on) { const o = el("loadingOverlay"); if (o) { if (on) show(o); else hide(o); } }
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
  if (CURRENT_FILE_URL) { try { URL.revokeObjectURL(CURRENT_FILE_URL); } catch(_) {} CURRENT_FILE_URL = null; }
  CURRENT_FILE_URL = URL.createObjectURL(CURRENT_FILE);
  const name = CURRENT_FILE.name || "file";
  const type = (CURRENT_FILE.type || "").toLowerCase();
  const sizeKB = Math.round((CURRENT_FILE.size || 0) / 1024);
  if (type.startsWith("image/")) { if (img) { img.src = CURRENT_FILE_URL; show(img); } hide(pdf); }
  else if (type === "application/pdf" || name.toLowerCase().endsWith(".pdf")) { if (emb) emb.src = CURRENT_FILE_URL; hide(img); show(pdf); }
  else { hide(img); hide(pdf); }
  show(wrap);
  if (meta) meta.textContent = name + " • " + sizeKB + " KB • " + (type || "unknown");
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
  const p = picksPayload();
  if (!(p.category_id && p.specialty_id && p.doc_type_id && p.file_kind)) { if (wrap) hide(wrap); if (select) seth(select, ""); return; }
  try {
    const qs = new URLSearchParams({ category_id: p.category_id, specialty_id: p.specialty_id, doc_type_id: p.doc_type_id, file_kind: p.file_kind });
    const res = await fetch(API.suggest + "?" + qs.toString(), { method: "GET", credentials: "same-origin" });
    if (!res.ok) throw new Error("suggest_failed");
    const data = await res.json();
    const items = data.events || [];
    if (!items.length) { if (wrap) hide(wrap); if (select) seth(select, ""); return; }
    const opts = ['<option value="">—</option>'].concat(items.map(x => { const vid = x.id != null ? String(x.id) : ""; const label = x.title || x.name || x.display_name || vid; return "<option value=\"" + vid + "\">" + label + "</option>"; }));
    if (select) seth(select, opts.join(""));
    if (wrap) show(wrap);
  } catch (_) { if (wrap) hide(wrap); if (select) seth(select, ""); }
}

function cleanOCRText(text) {
  let s = (text || "").replace(/\r\n/g, "\n");
  s = s.replace(/[‐‒–—−]/g, "-");
  s = s.replace(/-\s?96(?=\s|$)/g, "-%");
  s = s.replace(/[|¦]/g, " ");
  s = s.replace(/\s{2,}/g, " ");
  return s;
}

function parseLabs(text) {
  const src = cleanOCRText(text);
  const lines = (src || "").split(/\r?\n/).map(s => s.trim()).filter(Boolean);
  const items = [];
  const rowRe = /^([A-Za-zА-Яа-я0-9\.\(\)\/\-\s%]+?)\s+([\-+]?\d+(?:[\.,]\d+)?)(?:\s*([A-Za-zμ%\/\.\-\^\d×GgLl]+))?(?:\s+(\d+(?:[\.,]\d+)?)(?:\s*[%-])?\s*[-–]\s*(\d+(?:[\.,]\d+)?)(?:\s*[%-])?)?$/;
  for (const ln of lines) {
    if (/^(tests|result|flag|units|reference|comp\.|panel)/i.test(ln)) continue;
    const m = ln.match(rowRe);
    if (!m) continue;
    let name = m[1].replace(/\s{2,}/g, " ").replace(/\s-\s*$/,"").trim();
    name = name.replace(/\s*-\s*(%|бр\.?)\s*$/i, " $1").replace(/\s+/g, " ");
    const val = m[2].replace(",", ".");
    const unit = (m[3] || "").trim() || null;
    const rlo = m[4] ? parseFloat(String(m[4]).replace(",", ".")) : null;
    const rhi = m[5] ? parseFloat(String(m[5]).replace(",", ".")) : null;
    items.push({ name, value: parseFloat(val), unit, ref_low: isFinite(rlo) ? rlo : null, ref_high: isFinite(rhi) ? rhi : null });
  }
  return items;
}

function normalizeRows(rows) {
  const out = [];
  (rows || []).forEach(r => {
    const name = (r.indicator_name || r.name || "").toString().trim();
    const unit = (r.unit || "").toString().trim() || null;
    const v = r.value;
    let value = typeof v === "number" ? v : parseFloat(String(v || "").replace(",", "."));
    if (Number.isNaN(value)) value = String(v || "").trim();
    const ref = (r.reference_range || "").toString().trim();
    let rl = r.reference_low, rh = r.reference_high;
    if ((rl == null || rh == null) && ref && ref.includes("-")) {
      const parts = ref.split("-");
      const a = (parts[0] || "").trim().replace(",", ".");
      const b = (parts[1] || "").trim().replace(",", ".");
      rl = rl != null ? rl : (isNaN(parseFloat(a)) ? null : parseFloat(a));
      rh = rh != null ? rh : (isNaN(parseFloat(b)) ? null : parseFloat(b));
    }
    out.push({ name, value, unit, ref_low: rl != null ? rl : null, ref_high: rh != null ? rh : null });
  });
  return out;
}

function renderLabTable(items) {
  const wrap = el("labWrap");
  const slot = el("labTable");
  if (!wrap || !slot) return;
  const rows = (items || []).map((x, i) => {
    const n = x.name || "";
    const v = x.value != null ? String(x.value) : "";
    const u = x.unit || "";
    const rl = x.ref_low != null ? String(x.ref_low) : "";
    const rh = x.ref_high != null ? String(x.ref_high) : "";
    return "<tr data-idx=\"" + i + "\"><td class=\"px-2 py-1\">" + n + "</td><td class=\"px-2 py-1\">" + v + "</td><td class=\"px-2 py-1\">" + u + "</td><td class=\"px-2 py-1\">" + rl + "</td><td class=\"px-2 py-1\">" + rh + "</td></tr>";
  }).join("");
  const html = "<table class=\"min-w-full text-sm\"><thead><tr><th class=\"px-2 py-1 text-left\">Показател</th><th class=\"px-2 py-1 text-left\">Стойност</th><th class=\"px-2 py-1 text-left\">Единици</th><th class=\"px-2 py-1 text-left\">Мин</th><th class=\"px-2 py-1 text-left\">Макс</th></tr></thead><tbody>" + rows + "</tbody></table>";
  seth(slot, html);
  show(wrap);
}

function renderSummary(text) {
  const box = el("summaryBox");
  if (box) { box.textContent = text || ""; show(box); }
}

function renderOCRMeta(meta) {
  const n = stepLabelNode();
  let s = "";
  if (meta && typeof meta === "object") {
    const eng = meta.engine || meta.ocr_engine || meta.provider || meta.name || meta.used || "";
    const dur = meta.duration_ms || meta.dt_ms || meta.time_ms || meta.elapsed_ms || meta.duration || "";
    s = eng ? "OCR: " + eng : "";
    if (dur) s = s ? s + " • " + dur + " ms" : dur + " ms";
  }
  if (n) n.textContent = s;
}

function getWorkText() {
  const ta = el("workText");
  return ta ? ta.value || "" : "";
}

function setWorkText(t) {
  const ta = el("workText");
  if (ta) ta.value = t || "";
}

async function doOCR() {
  clearError();
  const p = picks();
  if (!p.file || !pipelineReady()) { showError("Липсват задължителни полета."); return; }
  const fd = new FormData();
  fd.append("file", p.file);
  fd.append("file_kind", p.fileKind);
  fd.append("category_id", p.category);
  fd.append("specialty_id", p.specialty);
  fd.append("doc_type_id", p.docType);
  if (p.eventId) fd.append("event_id", p.eventId);
  setBusy(true);
  try {
    const res = await fetch(API.ocr, { method: "POST", body: fd, credentials: "same-origin", headers: { "X-CSRFToken": getCSRF() } });
    if (!res.ok) throw new Error("ocr_failed");
    const data = await res.json();
    const text = (data && (data.text || data.ocr_text)) || "";
    const meta = (data && (data.meta || data.ocr_meta)) || {};
    OCR_META = meta || {};
    renderOCRMeta(OCR_META);
    ORIGINAL_OCR_TEXT = text || "";
    setWorkText(ORIGINAL_OCR_TEXT);
    ANALYZED_READY = false;
    updateButtons();
    const labs = parseLabs(ORIGINAL_OCR_TEXT);
    renderLabTable(labs);
  } catch (e) {
    showError("OCR неуспешен.");
  } finally {
    setBusy(false);
  }
}

async function doAnalyze() {
  clearError();
  const text = getWorkText();
  const p = picksPayload();
  if (!text.trim() || !requiredTagsReady()) { showError("Липсват данни за анализ."); return; }
  setBusy(true);
  try {
    const res = await fetch(API.analyze, { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json", "X-CSRFToken": getCSRF() }, body: JSON.stringify({ text, category_id: p.category_id, specialty_id: p.specialty_id, doc_type_id: p.doc_type_id, file_kind: p.file_kind, event_id: p.event_id || "" }) });
    if (!res.ok) throw new Error("analyze_failed");
    let data = {};
    try { data = await res.json(); } catch(_) { data = {}; }
    ANALYSIS = data || {};
    const summary = (ANALYSIS.summary || ANALYSIS.result?.summary || ANALYSIS.data?.summary || ANALYSIS.summary_text || "").toString();
    renderSummary(summary);
    const rows = normalizeRows(ANALYSIS.blood_test_results || ANALYSIS.result?.blood_test_results || ANALYSIS.data?.blood_test_results || []);
    if (rows.length) renderLabTable(rows);
    ANALYZED_READY = true;
    updateButtons();
  } catch (e) {
    showError("Анализът неуспешен.");
  } finally {
    setBusy(false);
  }
}

async function doConfirm() {
  clearError();
  const text = getWorkText();
  const p = picksPayload();
  if (!ANАЛYZED_READY || !requiredTagsReady()) { showError("Анализът не е завършен."); return; }
  setBusy(true);
  try {
    const payload = { text, category_id: p.category_id, specialty_id: p.specialty_id, doc_type_id: p.doc_type_id, file_kind: p.file_kind, event_id: p.event_id || "", analysis: ANALYSIS || {} };
    const res = await fetch(API.confirm, { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json", "X-CSRFToken": getCSRF() }, body: JSON.stringify(payload) });
    if (!res.ok) throw new Error("confirm_failed");
    let ok = res.ok;
    try {
      const j = await res.json();
      ok = ok || !!(j && (j.ok || j.success || j.saved || j.id));
    } catch(_) {}
    if (ok) {
      const btn = el("btnConfirm");
      if (btn) { btn.setAttribute("aria-disabled","true"); dis(btn, true); }
    }
  } catch (e) {
    showError("Записът е неуспешен.");
  } finally {
    setBusy(false);
  }
}

function bindEvents() {
  ensureUXStyles();
  const cat = el("sel_category");
  const spc = el("sel_specialty");
  const doc = el("sel_doc_type");
  const kind = el("file_kind");
  const file = el("file_input");
  const btnChoose = el("chooseFileBtn");
  const btnOCR = el("btnOCR");
  const btnAnalyze = el("btnAnalyze");
  const btnConfirm = el("btnConfirm");
  if (cat) cat.addEventListener("change", () => { updateDropdownFlow(); suggestIfReady(); updateButtons(); });
  if (spc) spc.addEventListener("change", () => { updateDropdownFlow(); suggestIfReady(); updateButtons(); });
  if (doc) doc.addEventListener("change", () => { updateDropdownFlow(); suggestIfReady(); updateButtons(); });
  if (kind) kind.addEventListener("change", () => { if (!FILE_KIND_LOCK) CURRENT_FILE_KIND = kind.value || ""; updateDropdownFlow(); updateButtons(); });
  if (file) file.addEventListener("change", handleFileInputChange);
  if (btnChoose) btnChoose.addEventListener("click", () => { if (file && !file.disabled) file.click(); });
  if (btnOCR) btnOCR.addEventListener("click", doOCR);
  if (btnAnalyze) btnAnalyze.addEventListener("click", doAnalyze);
  if (btnConfirm) btnConfirm.addEventListener("click", doConfirm);
  const ta = el("workText");
  if (ta) ta.addEventListener("input", () => { ANALYZED_READY = false; updateButtons(); });
}

function init() {
  bindEvents();
  updateDropdownFlow();
  updateButtons();
  renderOCRMeta(OCR_META || {});
}

document.addEventListener("DOMContentLoaded", init);
