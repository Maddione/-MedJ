// MedJ upload logic — aligned to backend contracts from README
// Flow: Upload → OCR → Analyze → Confirm. Endpoints under /api/upload/*. :contentReference[oaicite:1]{index=1}
const API = {
  ocr: "/api/upload/ocr/",
  analyze: "/api/upload/analyze/",
  confirm: "/api/upload/confirm/",
  suggest: "/api/events/suggest/",
};

const $ = (id) => document.getElementById(id);
const show = (x) => x && x.classList.remove("hidden");
const hide = (x) => x && x.classList.add("hidden");
const seth = (x, h) => x && (x.innerHTML = h || "");
const setv = (x, v) => x && (x.value = v || "");
const dis = (x, f) => {
  if (!x) return;
  x.disabled = !!f;
  x.classList.toggle("opacity-50", !!f);
  x.classList.toggle("cursor-not-allowed", !!f);
};
const clearStatus = () => {
  const box = $("statusBox");
  if (box) {
    box.textContent = "";
    hide(box);
  }
};
const getCSRF = () => {
  const t = document.querySelector('input[name="csrfmiddlewaretoken"]');
  if (t && t.value) return t.value;
  const m = document.cookie.match(/(?:^|;)\s*csrftoken=([^;]+)/);
  return m ? decodeURIComponent(m[1]) : "";
};

// runtime state
let FILE = null;
let FILE_KIND = "";
let FILE_URL = null;
let OCR_TEXT_ORIG = "";
let OCR_META = {};
let ANALYSIS = { summary: "", data: { tables: [], blood_test_results: [], suggested_tags: [] }, meta: {} };
let ANALYZED_READY = false;
let CLASS_LOCK = false;
let DOC_LOCK = false;
let FILE_KIND_LOCK = false;

const STEP_CONFIG = {
  1: { label: "Стъпка 1: Екстракт на текст" },
  2: { label: "Стъпка 2: Анализ" },
  3: { label: "Стъпка 3: Запазване" },
};
let CURRENT_STEP = 1;
const STEP_META = { 1: null, 2: null, 3: null };

function ensureStyles() {
  if ($("uxUploadInject")) return;
  const s = document.createElement("style");
  s.id = "uxUploadInject";
  s.textContent = '.btn[aria-disabled="true"]{opacity:.5;cursor:not-allowed;pointer-events:none}.btn.btn-armed:hover{filter:brightness(1.05)}';
  document.head.appendChild(s);
}

function picks() {
  return {
    category: ($("sel_category") || {}).value || "",
    specialty: ($("sel_specialty") || {}).value || "",
    docType: ($("sel_doc_type") || {}).value || "",
    fileKind: ($("file_kind") || {}).value || "",
    file: ($("file_input")?.files ? $("file_input").files[0] : null) || FILE,
    eventId: ($("existingEventSelect") || {}).value || "",
  };
}

function picksPayload() {
  const p = picks();
  return {
    category_id: p.category || "",
    specialty_id: p.specialty || "",
    doc_type_id: p.docType || "",
    file_kind: p.fileKind || "",
    event_id: p.eventId || "",
  };
}

const requiredTagsReady = () => {
  const p = picks();
  return !!(p.category && p.specialty && p.docType);
};
const pipelineReady = () => {
  const p = picks();
  return !!(p.category && p.specialty && p.docType && p.fileKind);
};

function stage() {
  const p = picks();
  if (!p.file) return "choose";
  const text = ($("workText") || {}).value || "";
  if (!text.trim()) return "ocr";
  return "analyze";
}

function updateButtons() {
  const s = stage();
  const bOCR = $("btnOCR");
  const bAna = $("btnAnalyze");
  const bCfm = $("btnConfirm");
  bOCR ? (s === "ocr" && pipelineReady() ? show(bOCR) : hide(bOCR)) : null;
  bAna ? (s === "analyze" && requiredTagsReady() && !ANALYZED_READY ? show(bAna) : hide(bAna)) : null;
  bCfm ? (ANALYZED_READY && requiredTagsReady() ? show(bCfm) : hide(bCfm)) : null;
}

function normalizeStepMeta(meta) {
  if (!meta || typeof meta !== "object") return {};
  const engine = meta.engine || meta.ocr_engine || meta.provider || meta.name || meta.used || "";
  const duration = meta.duration_ms ?? meta.duration ?? meta.time_ms ?? meta.dt_ms ?? meta.elapsed_ms;
  const detail = meta.detail || meta.note || meta.status || meta.message || "";
  const info = {};
  if (engine) info.engine = String(engine);
  if (duration != null && !Number.isNaN(Number(duration))) {
    info.duration_ms = Number(duration);
  }
  if (detail) info.detail = String(detail);
  if (meta.document_id != null) info.document_id = meta.document_id;
  if (meta.event_id != null) info.event_id = meta.event_id;
  return info;
}

function updateStepDisplay() {
  const labelNode = $("workLabel");
  const metaNode = $("workMeta");
  const info = STEP_CONFIG[CURRENT_STEP] || STEP_CONFIG[1];
  const meta = STEP_META[CURRENT_STEP] || {};
  const baseLabel = info?.label || "";
  const text = meta.engine ? `${baseLabel} : ${meta.engine}` : baseLabel;
  if (labelNode) labelNode.textContent = text;
  if (metaNode) {
    const parts = [];
    if (meta.duration_ms != null && !Number.isNaN(meta.duration_ms)) {
      parts.push(`${meta.duration_ms} ms`);
    }
    if (meta.detail) parts.push(meta.detail);
    if (!parts.length) {
      metaNode.textContent = "";
      metaNode.classList?.add("hidden");
    } else {
      metaNode.textContent = parts.join(" • ");
      metaNode.classList?.remove("hidden");
    }
  }
}

function applyStepMeta(step, meta, makeCurrent = false) {
  const idx = Number(step);
  if (![1, 2, 3].includes(idx)) return;
  if (meta) {
    STEP_META[idx] = normalizeStepMeta(meta);
  }
  if (makeCurrent) {
    CURRENT_STEP = idx;
  }
  if (makeCurrent || idx === CURRENT_STEP) {
    updateStepDisplay();
  }
}

function setCurrentStep(step) {
  const idx = Number(step);
  CURRENT_STEP = [1, 2, 3].includes(idx) ? idx : 1;
  updateStepDisplay();
}

function resetSteps() {
  STEP_META[1] = null;
  STEP_META[2] = null;
  STEP_META[3] = null;
  CURRENT_STEP = 1;
  updateStepDisplay();
}

function setBusy(on) {
  const o = $("loadingOverlay");
  if (o) (on ? show(o) : hide(o));
}
function showError(msg) {
  clearStatus();
  const box = $("errorBox");
  if (box) {
    box.textContent = msg || "Грешка.";
    show(box);
  }
}
function clearError() {
  const box = $("errorBox");
  if (box) {
    box.textContent = "";
    hide(box);
  }
}

function showStatus(msg) {
  const box = $("statusBox");
  if (box) {
    if (msg) {
      box.textContent = msg;
      show(box);
    } else {
      clearStatus();
    }
  }
}

function renderPreview() {
  const wrap = $("previewBlock");
  const img = $("previewImg");
  const pdf = $("previewPDF");
  const emb = $("previewEmbed");
  const meta = $("fileMeta");
  const badge = $("fileNameBadge");
  if (!FILE) {
    hide(wrap);
    meta && seth(meta, "");
    badge && badge.classList.add("hidden");
    return;
  }
  if (FILE_URL) {
    try { URL.revokeObjectURL(FILE_URL); } catch {}
    FILE_URL = null;
  }
  FILE_URL = URL.createObjectURL(FILE);
  const name = FILE.name || "file";
  const type = (FILE.type || "").toLowerCase();
  const sizeKB = Math.round((FILE.size || 0) / 1024);
  if (type.startsWith("image/")) {
    if (img) { img.src = FILE_URL; show(img); }
    hide(pdf);
  } else if (type === "application/pdf" || name.toLowerCase().endsWith(".pdf")) {
    if (emb) emb.src = FILE_URL;
    hide(img); show(pdf);
  } else {
    hide(img); hide(pdf);
  }
  show(wrap);
  meta && (meta.textContent = `${name} • ${sizeKB} KB • ${type || "unknown"}`);
  if (badge) { badge.textContent = name; badge.classList.remove("hidden"); }
}

function lockDocType() { DOC_LOCK = true; dis($("sel_doc_type"), true); }
function lockClassification() { CLASS_LOCK = true; ["sel_category","sel_specialty","sel_doc_type","file_kind"].forEach(id => dis($(id), true)); }

function handleFileInputChange() {
  const fi = $("file_input");
  const kind = $("file_kind");
  FILE = fi?.files ? fi.files[0] : null;
  FILE_KIND = (kind && kind.value) || "";
  FILE_KIND_LOCK = true;
  dis(kind, true);
  ANALYZED_READY = false;
  OCR_TEXT_ORIG = "";
  OCR_META = {};
  ANALYSIS = { summary: "", data: { tables: [], blood_test_results: [], suggested_tags: [] }, meta: {} };
  setWorkText("");
  renderLabTable([]);
  renderSummary("");
  clearStatus();
  clearError();
  resetSteps();
  renderPreview();
  const btnConfirm = $("btnConfirm");
  if (btnConfirm) {
    btnConfirm.removeAttribute("aria-disabled");
    dis(btnConfirm, false);
  }
  lockDocType();
  updateDropdownFlow();
  updateButtons();
}

function updateDropdownFlow() {
  const p = picks();
  const cat = $("sel_category");
  const spc = $("sel_specialty");
  const doc = $("sel_doc_type");
  const kind = $("file_kind");
  const file = $("file_input");
  const choose = $("chooseFileBtn");
  if (CLASS_LOCK) {
    dis(cat, true); dis(spc, true); dis(doc, true); dis(kind, true); dis(file, false);
    if (choose) { choose.setAttribute("aria-disabled","true"); choose.classList.remove("btn-armed"); }
    updateButtons(); return;
  }
  const readySpc = !!p.category;
  const readyDoc = readySpc && !!p.specialty;
  const readyKind = readyDoc && !!p.docType;
  const readyFile = readyKind && !!p.fileKind;
  dis(cat, false);
  dis(spc, !readySpc); if (!readySpc) setv(spc, "");
  dis(doc, !readyDoc || DOC_LOCK); if (!readyDoc && !DOC_LOCK) setv(doc, "");
  if (FILE_KIND_LOCK) {
    dis(kind, true);
  } else {
    dis(kind, !readyKind);
    if (!readyKind) { setv(kind, ""); FILE_KIND = ""; }
  }
  dis(file, !readyFile);
  if (choose) {
    if (readyFile) { choose.removeAttribute("aria-disabled"); choose.classList.add("btn-armed"); }
    else { choose.setAttribute("aria-disabled","true"); choose.classList.remove("btn-armed"); }
  }
  updateButtons();
}

async function suggestIfReady() {
  const wrap = $("existingEventWrap");
  const select = $("existingEventSelect");
  const p = picksPayload();
  if (!(p.category_id && p.specialty_id && p.doc_type_id && p.file_kind)) { wrap && hide(wrap); select && seth(select, ""); return; }
  try {
    const qs = new URLSearchParams(p).toString();
    const res = await fetch(`${API.suggest}?${qs}`, { method: "GET", credentials: "same-origin" });
    if (!res.ok) throw new Error("suggest_failed");
    const data = await res.json();
    const items = data.events || [];
    if (!items.length) { wrap && hide(wrap); select && seth(select, ""); return; }
    const opts = ['<option value="">—</option>'].concat(items.map(x => {
      const vid = x.id != null ? String(x.id) : "";
      const label = x.title || x.name || x.display_name || vid;
      return `<option value="${vid}">${label}</option>`;
    }));
    select && seth(select, opts.join(""));
    wrap && show(wrap);
  } catch {
    wrap && hide(wrap); select && seth(select, "");
  }
}

// ---------- OCR parsing fixes ----------
function cleanOCRText(text) {
  // Normalize dashes and fix OCR artifact where '%' is read as '96' after a '-'
  let s = String(text || "").replace(/\r\n/g, "\n");
  s = s.replace(/[‐‒–—−]/g, "-");
  // If we see "... -96 1.93", that should be "... % 1.93"
  s = s.replace(/-\s*96(?=\s*\d)/g, " %");
  // Also handle "...-96" directly following a word
  s = s.replace(/([\p{L}])\s*-\s*96\b/gu, "$1 %");
  // If we see "... -% 54.10", fix spacing
  s = s.replace(/-\s*%(?=\s*\d)/g, " %");
  // Vertical bars from tables
  s = s.replace(/[|¦]/g, " ");
  // Collapse excessive whitespace
  s = s.replace(/\s{2,}/g, " ");
  return s;
}

function parseLabs(text) {
  const src = cleanOCRText(text);
  const lines = src.split(/\r?\n/).map(s => s.trim()).filter(Boolean);
  const items = [];
  // Name may include " - % " or " - бр." suffixes. Value can be 1.23 or 4,04. Optional unit. Optional "min - max" at end with optional % signs.
  const rowRe = /^([A-Za-zА-Яа-я0-9\.\(\)\/\-\s%]+?)\s+([\-+]?\d+(?:[\.,]\d+)?)(?:\s*([A-Za-zμ%\/\.\-\^\d×GgLl]+))?(?:\s+(\d+(?:[\.,]\d+)?)(?:\s*[%-])?\s*[-–]\s*(\d+(?:[\.,]\d+)?)(?:\s*[%-])?)?$/u;
  for (const ln of lines) {
    if (/^(tests|result|flag|units|reference|comp\.|panel)/i.test(ln)) continue;
    const m = ln.match(rowRe);
    if (!m) continue;
    let name = m[1].replace(/\s{2,}/g, " ").replace(/\s-\s*$/,"").trim();
    // Convert "Еозинофилни левкоцити-%" -> "Еозинофилни левкоцити %", and "-бр." -> " бр."
    name = name.replace(/\s*-\s*(%|бр\.?)\s*$/i, " $1").replace(/\s+/g, " ");
    const val = parseFloat(String(m[2]).replace(",", "."));
    const unit = (m[3] || "").trim() || null;
    const rlo = m[4] ? parseFloat(String(m[4]).replace(",", ".")) : null;
    const rhi = m[5] ? parseFloat(String(m[5]).replace(",", ".")) : null;
    items.push({ name, value: isFinite(val) ? val : null, unit, ref_low: isFinite(rlo) ? rlo : null, ref_high: isFinite(rhi) ? rhi : null });
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
      const [a, b] = ref.split("-").map(s => s.trim().replace(",", "."));
      rl = rl ?? (isNaN(parseFloat(a)) ? null : parseFloat(a));
      rh = rh ?? (isNaN(parseFloat(b)) ? null : parseFloat(b));
    }
    out.push({ name, value, unit, ref_low: rl ?? null, ref_high: rh ?? null });
  });
  return out;
}

function renderLabTable(items) {
  const wrap = $("labWrap");
  const slot = $("labTableSlot");
  if (!wrap || !slot) return;
  const list = Array.isArray(items) ? items : [];
  if (!list.length) {
    seth(slot, "");
    hide(wrap);
    return;
  }
  const rows = list.map((x, i) => {
    const n = x.name || "";
    const v = x.value != null ? String(x.value) : "";
    const u = x.unit || "";
    const rl = x.ref_low != null ? String(x.ref_low) : "";
    const rh = x.ref_high != null ? String(x.ref_high) : "";
    return `<tr data-idx="${i}"><td class="px-2 py-1">${n}</td><td class="px-2 py-1">${v}</td><td class="px-2 py-1">${u}</td><td class="px-2 py-1">${rl}</td><td class="px-2 py-1">${rh}</td></tr>`;
  }).join("");
  const html = `<table class="min-w-full text-sm"><thead><tr><th class="px-2 py-1 text-left">Показател</th><th class="px-2 py-1 text-left">Стойност</th><th class="px-2 py-1 text-left">Единици</th><th class="px-2 py-1 text-left">Мин</th><th class="px-2 py-1 text-left">Макс</th></tr></thead><tbody>${rows}</tbody></table>`;
  seth(slot, html);
  show(wrap);
}

function renderSummary(text) {
  const box = $("summaryBox");
  if (!box) return;
  const value = (text || "").toString().trim();
  if (!value) {
    box.textContent = "";
    hide(box);
    return;
  }
  box.textContent = value;
  show(box);
}

function renderOCRMeta(meta) {
  applyStepMeta(1, meta, CURRENT_STEP === 1);
}

function getWorkText() { return $("workText")?.value || ""; }
function setWorkText(t) { const ta = $("workText"); if (ta) ta.value = t || ""; }

async function doOCR() {
  clearError();
  clearStatus();
  const p = picks();
  if (!p.file || !pipelineReady()) { showError("Липсват задължителни полета."); return; }
  STEP_META[2] = null;
  STEP_META[3] = null;
  setCurrentStep(1);
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
    const text = data?.text || data?.ocr_text || "";
    const meta = data?.meta || data?.ocr_meta || {};
    OCR_META = meta || {};
    applyStepMeta(1, OCR_META, true);
    const cleaned = cleanOCRText(text);
    OCR_TEXT_ORIG = cleaned;
    setWorkText(cleaned);
    ANALYZED_READY = false;
    renderSummary("");
    updateButtons();
    const labs = parseLabs(OCR_TEXT_ORIG);
    renderLabTable(labs);
  } catch {
    showError("OCR неуспешен.");
  } finally { setBusy(false); }
}

async function doAnalyze() {
  clearError();
  const text = getWorkText();
  const p = picksPayload();
  if (!text.trim() || !requiredTagsReady()) { showError("Липсват данни за анализ."); return; }
  setBusy(true);
  try {
    const body = { text, ...p };
    const res = await fetch(API.analyze, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": getCSRF() },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error("analyze_failed");
    let data = {};
    try { data = await res.json(); } catch {}
    const meta = data?.meta || {};
    ANALYSIS = { ...(data || {}), meta };
    const summary = (ANALYSIS.summary || ANALYSIS.result?.summary || ANALYSIS.data?.summary || ANALYSIS.summary_text || "").toString();
    renderSummary(summary);
    const rows = normalizeRows(
      ANALYSIS.blood_test_results ||
      ANALYSIS.result?.blood_test_results ||
      ANALYSIS.data?.blood_test_results ||
      []
    );
    renderLabTable(rows);
    ANALYZED_READY = true;
    applyStepMeta(2, meta, true);
    updateButtons();
  } catch {
    showError("Анализът неуспешен.");
  } finally { setBusy(false); }
}

async function doConfirm() {
  clearError();
  clearStatus();
  const text = getWorkText();
  const p = picksPayload();
  const raw = picks();
  if (!ANALYZED_READY || !requiredTagsReady()) { showError("Анализът не е завършен."); return; }
  if (!raw.file) { showError("Липсва файл за запис."); return; }
  setBusy(true);
  try {
    const fd = new FormData();
    fd.append("file", raw.file);
    fd.append("file_kind", raw.fileKind || FILE_KIND || "");
    fd.append("category_id", p.category_id || "");
    fd.append("specialty_id", p.specialty_id || "");
    fd.append("doc_type_id", p.doc_type_id || "");
    fd.append("ocr_text", OCR_TEXT_ORIG || text || "");
    fd.append("text", text || "");
    if (p.event_id) fd.append("event_id", p.event_id);
    const summary = (ANALYSIS.summary || ANALYSIS.result?.summary || ANALYSIS.data?.summary || ANALYSIS.summary_text || "").toString();
    if (summary) fd.append("summary", summary);
    const eventDate = ANALYSIS.data?.event_date || ANALYSIS.event_date || "";
    if (eventDate) {
      fd.append("event_date", eventDate);
      fd.append("document_date", eventDate);
    }
    if (OCR_META && Object.keys(OCR_META).length) fd.append("ocr_meta", JSON.stringify(OCR_META));
    if (ANALYSIS && Object.keys(ANALYSIS).length) fd.append("analysis", JSON.stringify(ANALYSIS));
    if (ANALYSIS?.meta && Object.keys(ANALYSIS.meta || {}).length) {
      fd.append("analysis_meta", JSON.stringify(ANALYSIS.meta));
    }
    const res = await fetch(API.confirm, {
      method: "POST",
      credentials: "same-origin",
      headers: { "X-CSRFToken": getCSRF() },
      body: fd,
    });
    if (!res.ok) throw new Error("confirm_failed");
    let ok = res.ok;
    let data = {};
    try { data = await res.json(); } catch {}
    const meta = data?.meta || {};
    if (res.ok && (data?.ok || data?.success || data?.saved || data?.id || data?.document_id)) {
      ok = true;
    }
    if (ok) {
      const btn = $("btnConfirm");
      if (btn) { btn.setAttribute("aria-disabled","true"); dis(btn, true); }
      showStatus("Документът е записан успешно.");
      applyStepMeta(3, { ...meta, document_id: data?.document_id, event_id: data?.event_id }, true);
    }
  } catch {
    showError("Записът е неуспешен.");
  } finally { setBusy(false); }
}

async function wireSuggest() {
  await suggestIfReady();
}

function bindEvents() {
  ensureStyles();
  const cat = $("sel_category");
  const spc = $("sel_specialty");
  const doc = $("sel_doc_type");
  const kind = $("file_kind");
  const file = $("file_input");
  const btnChoose = $("chooseFileBtn");
  const btnOCR = $("btnOCR");
  const btnAnalyze = $("btnAnalyze");
  const btnConfirm = $("btnConfirm");

  cat && cat.addEventListener("change", () => { updateDropdownFlow(); wireSuggest(); updateButtons(); });
  spc && spc.addEventListener("change", () => { updateDropdownFlow(); wireSuggest(); updateButtons(); });
  doc && doc.addEventListener("change", () => { updateDropdownFlow(); wireSuggest(); updateButtons(); });
  kind && kind.addEventListener("change", () => { if (!FILE_KIND_LOCK) FILE_KIND = kind.value || ""; updateDropdownFlow(); updateButtons(); });
  file && file.addEventListener("change", handleFileInputChange);
  btnChoose && btnChoose.addEventListener("click", () => { if (file && !file.disabled) file.click(); });
  btnOCR && btnOCR.addEventListener("click", doOCR);
  btnAnalyze && btnAnalyze.addEventListener("click", doAnalyze);
  btnConfirm && btnConfirm.addEventListener("click", doConfirm);

  const ta = $("workText");
  ta && ta.addEventListener("input", () => {
    ANALYZED_READY = false;
    STEP_META[2] = null;
    STEP_META[3] = null;
    setCurrentStep(1);
    const btn = $("btnConfirm");
    if (btn) { btn.removeAttribute("aria-disabled"); dis(btn, false); }
    updateButtons();
  });
}

function init() {
  bindEvents();
  updateDropdownFlow();
  updateButtons();
  resetSteps();
  renderOCRMeta(OCR_META || {});
}

document.addEventListener("DOMContentLoaded", init);
