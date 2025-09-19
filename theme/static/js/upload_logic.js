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

function parseJSONScript(id) {
  const el = document.getElementById(id);
  if (!el) return null;
  try {
    return JSON.parse(el.textContent || "null");
  } catch (err) {
    console.warn("Failed to parse JSON script", id, err);
    return null;
  }
}

const CONFIG = parseJSONScript("uploadConfigData") || {};

function escapeHtml(str) {
  return String(str || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function normalizeNameKey(name) {
  if (!name) return "";
  let s = String(name).trim();
  try {
    s = s.normalize("NFKD");
  } catch (err) {
    /* ignore */
  }
  s = s.replace(/[\u0300-\u036f]/g, "");
  return s
    .toLowerCase()
    .replace(/[^a-zа-я0-9%]/giu, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function slugifyIndicatorName(name) {
  const key = normalizeNameKey(name);
  if (!key) return "";
  return key
    .replace(/[^a-z0-9а-я%]+/giu, "-")
    .replace(/-+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function defaultMeasuredAt() {
  const eventDate = (ANALYSIS?.data?.event_date || ANALYSIS?.event_date || "").toString().trim();
  if (eventDate) {
    if (eventDate.includes("T")) return eventDate;
    return `${eventDate}T12:00:00`;
  }
  const now = new Date();
  now.setHours(12, 0, 0, 0);
  return now.toISOString();
}

function safeNumber(value) {
  if (value === null || value === undefined || value === "") return null;
  const num = Number(value);
  return Number.isFinite(num) ? num : null;
}

const LAB_INDEX = (() => {
  const data = parseJSONScript("labIndexData");
  if (!Array.isArray(data)) {
    return { canonical: {}, meta: {} };
  }
  const canonical = {};
  const meta = {};
  const store = (label, target) => {
    const key = normalizeNameKey(label);
    if (key) canonical[key] = target;
  };
  data.forEach((item) => {
    const main = (item?.name || "").toString().trim();
    if (!main) return;
    meta[main] = {
      unit: (item?.unit || "").toString().trim() || null,
      ref_low: safeNumber(item?.ref_low),
      ref_high: safeNumber(item?.ref_high),
    };
    store(main, main);
    const aliases = Array.isArray(item?.aliases) ? item.aliases : [];
    aliases.forEach((alias) => {
      const token = (alias || "").toString().trim();
      if (token) store(token, main);
    });
  });
  return { canonical, meta };
})();

function canonicalizeIndicatorName(rawName) {
  const name = (rawName || "").toString().trim();
  if (!name) {
    return { name: "", unit: null, ref_low: null, ref_high: null };
  }
  const key = normalizeNameKey(name);
  const canonical = (key && LAB_INDEX.canonical[key]) || name;
  const meta = LAB_INDEX.meta[canonical] || {};
  return {
    name: canonical,
    unit: meta.unit || null,
    ref_low: safeNumber(meta.ref_low),
    ref_high: safeNumber(meta.ref_high),
  };
}

function formatNumber(value) {
  if (value === null || value === undefined) return "";
  if (typeof value === "number") {
    if (Number.isInteger(value)) return String(value);
    const fixed = value.toFixed(2);
    return fixed.replace(/\.00$/, "").replace(/(\.[0-9]*[1-9])0+$/, "$1");
  }
  const asNum = Number(value);
  if (Number.isFinite(asNum)) return formatNumber(asNum);
  return String(value);
}
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
let OCR_TEXT_RAW = "";
let OCR_META = {};
let ANALYSIS = { summary: "", data: { tables: [], blood_test_results: [], suggested_tags: [] }, meta: {} };
let ANALYZED_READY = false;
let CLASS_LOCK = false;
let DOC_LOCK = false;
let FILE_KIND_LOCK = false;
let LAB_RESULTS = [];
let TABLE_EDIT_MODE = false;
let SUMMARY_MANUAL = false;
let SUMMARY_LOCKED = false;
let DUPLICATE_DETECTED = false;

const STEP_CONFIG = {
  1: { label: "Стъпка 1: OCR сканиране" },
  2: { label: "Стъпка 2: AI Анализ" },
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
  if (DUPLICATE_DETECTED) {
    bAna ? hide(bAna) : null;
    bCfm ? hide(bCfm) : null;
    return;
  }
  bOCR ? (s === "ocr" && pipelineReady() ? show(bOCR) : hide(bOCR)) : null;
  bAna ? (s === "analyze" && requiredTagsReady() && !ANALYZED_READY ? show(bAna) : hide(bAna)) : null;
  bCfm ? (ANALYZED_READY && requiredTagsReady() ? show(bCfm) : hide(bCfm)) : null;
}

function normalizeStepMeta(meta) {
  if (!meta || typeof meta !== "object") return {};
  const engine = meta.engine || meta.ocr_engine || meta.provider || meta.name || meta.used || "";
  const duration = meta.duration_ms ?? meta.duration ?? meta.time_ms ?? meta.dt_ms ?? meta.elapsed_ms;
  const detail = meta.detail || meta.note || meta.status || meta.message || "";
  const provider = meta.provider || meta.source || meta.vendor || meta.service || "";
  const status = meta.status_code ?? meta.statusCode ?? meta.http_status ?? null;
  const info = {};
  if (engine) info.engine = String(engine);
  if (duration != null && !Number.isNaN(Number(duration))) {
    info.duration_ms = Number(duration);
  }
  if (detail) info.detail = String(detail);
  if (provider && provider !== engine) info.provider = String(provider);
  if (status != null && status !== "") info.status_code = status;
  const docId = meta.document_id ?? meta.documentId ?? meta.id;
  if (docId != null && docId !== "") info.document_id = docId;
  const eventId = meta.event_id ?? meta.eventId;
  if (eventId != null && eventId !== "") info.event_id = eventId;
  return info;
}

function updateStepDisplay() {
  const labelNode = $("workLabel");
  const metaNode = $("workMeta");
  const info = STEP_CONFIG[CURRENT_STEP] || STEP_CONFIG[1];
  const meta = STEP_META[CURRENT_STEP] || {};
  const baseLabel = info?.label || "";
  const engineText = meta.engine ? String(meta.engine) : "";
  const labelText = engineText ? `${baseLabel} : ${engineText}` : `${baseLabel} : —`;
  if (labelNode) labelNode.textContent = labelText;
  if (metaNode) {
    const parts = [];
    if (engineText) parts.push(engineText);
    if (meta.provider) parts.push(meta.provider);
    if (meta.duration_ms != null && !Number.isNaN(meta.duration_ms)) {
      parts.push(`${meta.duration_ms} ms`);
    }
    if (meta.detail) parts.push(meta.detail);
    if (meta.document_id != null && meta.document_id !== "") {
      parts.push(`Документ №${meta.document_id}`);
    }
    if (meta.event_id != null && meta.event_id !== "") {
      parts.push(`Събитие №${meta.event_id}`);
    }
    if (meta.status_code) {
      parts.push(`HTTP ${meta.status_code}`);
    }
    const unique = [...new Set(parts.filter(Boolean))];
    if (!unique.length) {
      metaNode.textContent = "—";
      metaNode.classList?.remove("hidden");
    } else {
      metaNode.textContent = unique.join(" • ");
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
function showError(msg, opts = {}) {
  clearStatus();
  const box = $("errorBox");
  if (!box) return;
  if (opts.allowHTML) {
    box.innerHTML = msg || "Грешка.";
  } else {
    box.textContent = msg || "Грешка.";
  }
  show(box);
}
function clearError() {
  const box = $("errorBox");
  if (box) {
    box.textContent = "";
    box.innerHTML = "";
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
  OCR_TEXT_RAW = "";
  OCR_META = {};
  ANALYSIS = { summary: "", data: { tables: [], blood_test_results: [], suggested_tags: [] }, meta: {} };
  SUMMARY_MANUAL = false;
  setSummaryLocked(false);
  setSummaryNotice("");
  DUPLICATE_DETECTED = false;
  setWorkText("", { silent: true });
  renderLabTable([]);
  renderSummary("");
  renderSuggestedTags([], "");
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
  const seen = new Map();
  // Name may include " - % " or " - бр." suffixes. Value can be 1.23 or 4,04. Optional unit. Optional "min - max" at end with optional % signs.
  const rowRe = /^([A-Za-zА-Яа-я0-9\.\(\)\/\-\s%]+?)\s+([\-+]?\d+(?:[\.,]\d+)?)(?:\s*([A-Za-zμ%\/\.\-\^\d×GgLl]+))?(?:\s+(\d+(?:[\.,]\d+)?)(?:\s*[%-])?\s*[-–]\s*(\d+(?:[\.,]\d+)?)(?:\s*[%-])?)?$/u;
  const toNum = (raw) => safeNumber(String(raw || "").replace(",", "."));
  for (const ln of lines) {
    if (/^(tests|result|flag|units|reference|comp\.|panel)/i.test(ln)) continue;
    const m = ln.match(rowRe);
    if (!m) continue;
    let name = m[1].replace(/\s{2,}/g, " ").replace(/\s-\s*$/,"").trim();
    // Convert "Еозинофилни левкоцити-%" -> "Еозинофилни левкоцити %", and "-бр." -> " бр."
    name = name.replace(/\s*-\s*(%|бр\.?)\s*$/i, " $1").replace(/\s+/g, " ");
    const valNum = toNum(m[2]);
    const unitRaw = (m[3] || "").trim();
    const rlo = toNum(m[4]);
    const rhi = toNum(m[5]);
    const canon = canonicalizeIndicatorName(name);
    const keyName = canon.name || name;
    if (!keyName) continue;
    const entry = {
      name: keyName,
      value: valNum != null ? valNum : String(m[2] || "").trim(),
      unit: unitRaw || canon.unit || null,
      ref_low: rlo != null ? rlo : canon.ref_low,
      ref_high: rhi != null ? rhi : canon.ref_high,
    };
    if (entry.ref_low != null || entry.ref_high != null) {
      const lowTxt = entry.ref_low != null ? formatNumber(entry.ref_low) : "—";
      const highTxt = entry.ref_high != null ? formatNumber(entry.ref_high) : "—";
      entry.reference_range = `${lowTxt}-${highTxt}`;
    }
    if (seen.has(keyName)) {
      const prev = seen.get(keyName);
      if ((prev.value === null || prev.value === "") && entry.value) prev.value = entry.value;
      if (!prev.unit && entry.unit) prev.unit = entry.unit;
      if (prev.ref_low == null && entry.ref_low != null) prev.ref_low = entry.ref_low;
      if (prev.ref_high == null && entry.ref_high != null) prev.ref_high = entry.ref_high;
    } else {
      seen.set(keyName, entry);
      items.push(entry);
    }
  }
  return items;
}

function normalizeRows(rows) {
  const out = [];
  (rows || []).forEach((r) => {
    const name = (r.indicator_name || r.name || "").toString().trim();
    const canon = canonicalizeIndicatorName(name);
    const unitRaw = (r.unit || "").toString().trim() || null;
    const v = r.value;
    let value = typeof v === "number" ? v : parseFloat(String(v || "").replace(",", "."));
    if (Number.isNaN(value)) value = String(v || "").trim();
    const ref = (r.reference_range || "").toString().trim();
    let rl = r.reference_low;
    let rh = r.reference_high;
    if (typeof rl === "string") {
      const num = parseFloat(rl.replace(",", "."));
      if (!Number.isNaN(num)) rl = num;
    }
    if (typeof rh === "string") {
      const num = parseFloat(rh.replace(",", "."));
      if (!Number.isNaN(num)) rh = num;
    }
    if ((rl == null || rh == null) && ref && ref.includes("-")) {
      const [a, b] = ref.split("-").map((s) => s.trim().replace(",", "."));
      rl = rl ?? (isNaN(parseFloat(a)) ? null : parseFloat(a));
      rh = rh ?? (isNaN(parseFloat(b)) ? null : parseFloat(b));
    }
    if (rl == null) rl = canon.ref_low;
    if (rh == null) rh = canon.ref_high;
    const finalName = canon.name || name;
    const unit = unitRaw || canon.unit || null;
    let reference = null;
    if (rl != null || rh != null) {
      const lowTxt = rl != null ? formatNumber(rl) : "—";
      const highTxt = rh != null ? formatNumber(rh) : "—";
      reference = `${lowTxt}-${highTxt}`;
    }
    const measuredRaw = (r.measured_at || r.measuredAt || "").toString().trim();
    const measuredAt = measuredRaw || defaultMeasuredAt();
    out.push({
      name: finalName,
      slug: slugifyIndicatorName(finalName),
      value,
      unit,
      ref_low: rl ?? null,
      ref_high: rh ?? null,
      reference_range: reference,
      measured_at: measuredAt,
    });
  });
  return out;
}

function getLabResults() {
  return Array.isArray(LAB_RESULTS) ? LAB_RESULTS : [];
}

function applyLabResults(rows) {
  const normalized = normalizeRows(rows || []);
  LAB_RESULTS = normalized;
  if (!ANALYSIS.data) ANALYSIS.data = {};
  ANALYSIS.data.blood_test_results = normalized.map(row => ({
    indicator_name: row.name,
    indicator_slug: row.slug || slugifyIndicatorName(row.name),
    value: row.value,
    unit: row.unit || "",
    ref_low: row.ref_low,
    ref_high: row.ref_high,
    reference_range: row.reference_range || "",
    measured_at: row.measured_at || defaultMeasuredAt(),
  }));
  ANALYSIS.blood_test_results = ANALYSIS.data.blood_test_results;
  return normalized;
}

function collectTableEdits() {
  const slot = $("labTable");
  if (!slot) return getLabResults();
  const rows = [];
  slot.querySelectorAll("tbody tr").forEach((tr) => {
    const grab = (field) => {
      const el = tr.querySelector(`[data-field="${field}"]`);
      return el ? el.textContent || "" : "";
    };
    const name = grab("name").trim();
    if (!name) return;
    const valueText = grab("value").trim();
    const unitText = grab("unit").trim();
    const lowText = grab("ref_low").trim();
    const highText = grab("ref_high").trim();
    const valueNum = safeNumber(valueText.replace(",", "."));
    const lowNum = safeNumber(lowText.replace(",", "."));
    const highNum = safeNumber(highText.replace(",", "."));
    rows.push({
      name,
      value: valueNum !== null ? valueNum : valueText,
      unit: unitText || null,
      ref_low: lowNum !== null ? lowNum : (lowText || null),
      ref_high: highNum !== null ? highNum : (highText || null),
    });
  });
  return rows;
}

function syncTableEditButton() {
  const btn = $("btnToggleTableEdit");
  if (!btn) return;
  const hasRows = getLabResults().length > 0;
  btn.disabled = !hasRows;
  btn.classList.toggle("opacity-50", !hasRows);
  btn.classList.toggle("cursor-not-allowed", !hasRows);
  if (!hasRows) {
    btn.setAttribute("aria-disabled", "true");
    btn.setAttribute("aria-pressed", "false");
  } else {
    btn.removeAttribute("aria-disabled");
  }
  const defaultLabel = btn.dataset.labelDefault || btn.textContent.trim();
  if (!btn.dataset.labelDefault) btn.dataset.labelDefault = defaultLabel;
  const activeLabel = btn.dataset.activeLabel || defaultLabel;
  if (TABLE_EDIT_MODE && hasRows) {
    btn.textContent = activeLabel;
    btn.setAttribute("aria-pressed", "true");
    btn.classList.add("bg-primary/10");
  } else {
    btn.textContent = btn.dataset.labelDefault;
    btn.setAttribute("aria-pressed", "false");
    btn.classList.remove("bg-primary/10");
  }
}

function renderLabTable(rows = null) {
  const wrap = $("labWrap");
  const slot = $("labTable");
  const summary = $("labSummary");
  if (!wrap || !slot) return;
  if (rows !== null) {
    applyLabResults(rows);
  }
  const list = getLabResults();
  if (!list.length) {
    seth(slot, "");
    hide(wrap);
    TABLE_EDIT_MODE = false;
    if (summary) {
      summary.textContent = "";
      summary.classList.add("hidden");
    }
    syncTableEditButton();
    return;
  }
  let abnormal = 0;
  const bodyRows = list.map((x, i) => {
    const n = x.name || "";
    const valueNum = typeof x.value === "number" ? x.value : Number(x.value);
    const rlNum = typeof x.ref_low === "number" ? x.ref_low : Number(x.ref_low);
    const rhNum = typeof x.ref_high === "number" ? x.ref_high : Number(x.ref_high);
    const below = Number.isFinite(valueNum) && Number.isFinite(rlNum) && valueNum < rlNum;
    const above = Number.isFinite(valueNum) && Number.isFinite(rhNum) && valueNum > rhNum;
    if (below || above) abnormal += 1;
    const rowClass = below || above ? " bg-red-50" : "";
    const valueClass = below || above ? "px-2 py-1 font-semibold text-red-600" : "px-2 py-1";
    const flag = below ? "↓" : above ? "↑" : "";
    const displayValue = typeof x.value === "number" ? formatNumber(x.value) : (x.value || "");
    const displayUnit = x.unit || "";
    const lowText = x.ref_low != null ? formatNumber(x.ref_low) : "";
    const highText = x.ref_high != null ? formatNumber(x.ref_high) : "";
    const editAttr = TABLE_EDIT_MODE ? " contenteditable=\"true\"" : "";
    const flagHtml = !TABLE_EDIT_MODE && flag ? ` <span class="text-xs">${flag}</span>` : "";
    return `
      <tr data-idx="${i}" class="${rowClass.trim()}">
        <td class="px-2 py-1" data-field="name"${editAttr}>${escapeHtml(n)}</td>
        <td class="${valueClass}" data-field="value"${editAttr}>${escapeHtml(displayValue)}${flagHtml}</td>
        <td class="px-2 py-1" data-field="unit"${editAttr}>${escapeHtml(displayUnit)}</td>
        <td class="px-2 py-1" data-field="ref_low"${editAttr}>${escapeHtml(lowText)}</td>
        <td class="px-2 py-1" data-field="ref_high"${editAttr}>${escapeHtml(highText)}</td>
      </tr>`;
  }).join("");
  const tableClass = TABLE_EDIT_MODE ? "min-w-full text-sm table-fixed" : "min-w-full text-sm";
  const html = `
    <table class="${tableClass}" data-editing="${TABLE_EDIT_MODE ? "true" : "false"}">
      <thead>
        <tr>
          <th class="px-2 py-1 text-left">Показател</th>
          <th class="px-2 py-1 text-left">Стойност</th>
          <th class="px-2 py-1 text-left">Единици</th>
          <th class="px-2 py-1 text-left">Мин</th>
          <th class="px-2 py-1 text-left">Макс</th>
        </tr>
      </thead>
      <tbody>${bodyRows}</tbody>
    </table>`;
  seth(slot, html);
  show(wrap);
  if (summary) {
    const bits = [`${list.length} показателя`];
    if (abnormal > 0) bits.push(`${abnormal} извън норма`);
    summary.textContent = bits.join(" • ");
    summary.classList.remove("hidden");
  }
  syncTableEditButton();
}

function getSummaryWrap() { return $("summaryWrap"); }
function getSummaryField() { return $("summaryBox"); }
function getSummaryNotice() { return $("summaryNotice"); }
function getSummaryText() { return getSummaryField()?.value || ""; }
function setSummaryNotice(text) {
  const node = getSummaryNotice();
  if (!node) return;
  const value = (text || "").toString().trim();
  if (!value) {
    node.textContent = "";
    node.classList.add("hidden");
    return;
  }
  node.textContent = value;
  node.classList.remove("hidden");
}

function getAnalysisNoticeBox() { return $("analysisNotice"); }
function showAnalysisNotice(message) {
  const node = getAnalysisNoticeBox();
  if (!node) return;
  const value = (message || "").toString().trim();
  if (!value) {
    node.textContent = "";
    node.classList.add("hidden");
    return;
  }
  node.textContent = value;
  node.classList.remove("hidden");
}
function hideAnalysisNotice() {
  const node = getAnalysisNoticeBox();
  if (!node) return;
  node.textContent = "";
  node.classList.add("hidden");
  setRetryAnalyzeVisible(false);
}
function setRetryAnalyzeVisible(flag) {
  const btn = $("btnRetryAnalyze");
  if (!btn) return;
  if (flag) {
    btn.classList.remove("hidden");
  } else {
    btn.classList.add("hidden");
  }
}
function updateAnalysisStatus(meta = {}) {
  const notice = meta.notice || meta.detail || meta.message || "";
  if (notice) {
    showAnalysisNotice(notice);
  } else {
    hideAnalysisNotice();
  }
  const needsRetry = !!meta.retry_suggested;
  setRetryAnalyzeVisible(needsRetry);
  if (needsRetry) {
    ANALYZED_READY = false;
  }
}
function syncSummaryState(value) {
  const val = (value || "").toString();
  ANALYSIS.summary = val;
  ANALYSIS.summary_text = val;
  if (!ANALYSIS.data || typeof ANALYSIS.data !== "object") {
    ANALYSIS.data = { tables: [], blood_test_results: [], suggested_tags: [] };
  }
  ANALYSIS.data.summary = val;
}
function setSummaryLocked(flag) {
  SUMMARY_LOCKED = !!flag;
  const field = getSummaryField();
  if (field) {
    field.readOnly = SUMMARY_LOCKED;
    field.setAttribute("aria-readonly", SUMMARY_LOCKED ? "true" : "false");
    field.classList.toggle("bg-gray-100", SUMMARY_LOCKED);
    field.classList.toggle("text-primaryDark/70", SUMMARY_LOCKED);
  }
}
function renderSummary(text, opts = {}) {
  const wrap = getSummaryWrap();
  const field = getSummaryField();
  if (!wrap || !field) return;
  const value = (text || "").toString();
  if (!value.trim()) {
    field.value = "";
    hide(wrap);
    if (!opts.preserveManual) {
      SUMMARY_MANUAL = false;
    }
    syncSummaryState("");
    setSummaryNotice("");
    if (!SUMMARY_LOCKED) {
      field.readOnly = false;
      field.setAttribute("aria-readonly", "false");
    }
    return;
  }
  show(wrap);
  field.value = value;
  syncSummaryState(value);
  if (opts.fromAnalysis) {
    SUMMARY_MANUAL = false;
    setSummaryLocked(false);
    setSummaryNotice("Можете да редактирате резюмето преди запазване.");
  } else if (!SUMMARY_MANUAL) {
    setSummaryNotice("");
  }
  if (!SUMMARY_LOCKED) {
    field.readOnly = false;
    field.setAttribute("aria-readonly", "false");
  }
}

function renderSuggestedTags(tags, specialty) {
  const wrap = $("suggestedTagsWrap");
  const listNode = $("suggestedTagsList");
  const specialtyNode = $("detectedSpecialty");
  if (!wrap || !listNode || !specialtyNode) return;
  const arr = Array.isArray(tags) ? tags.map(t => (t == null ? "" : String(t))).filter(Boolean) : [];
  const specialtyText = (specialty || "").toString().trim();
  if (!arr.length && !specialtyText) {
    seth(listNode, "");
    specialtyNode.textContent = "";
    specialtyNode.classList.add("hidden");
    hide(wrap);
    return;
  }
  const chips = arr.map((tag) => `<span class="inline-flex items-center px-3 py-1 text-xs font-semibold bg-primary/10 text-primaryDark rounded-full">${escapeHtml(tag)}</span>`).join("");
  seth(listNode, chips);
  if (specialtyText) {
    specialtyNode.textContent = `Детектирана специалност: ${specialtyText}`;
    specialtyNode.classList.remove("hidden");
  } else {
    specialtyNode.textContent = "";
    specialtyNode.classList.add("hidden");
  }
  show(wrap);
}

function refreshTableFromText() {
  const text = getWorkText();
  TABLE_EDIT_MODE = false;
  const rows = parseLabs(text);
  renderLabTable(rows);
}

function toggleTableEditMode() {
  if (!getLabResults().length) {
    TABLE_EDIT_MODE = false;
    syncTableEditButton();
    return;
  }
  if (!TABLE_EDIT_MODE) {
    TABLE_EDIT_MODE = true;
    renderLabTable();
    return;
  }
  const rows = collectTableEdits();
  TABLE_EDIT_MODE = false;
  renderLabTable(rows);
}

function normalizeCurrentText() {
  const text = getWorkText();
  const normalized = cleanOCRText(text);
  if (normalized === text) {
    return;
  }
  setWorkText(normalized);
}

function restoreOriginalOCRText() {
  const original = OCR_TEXT_ORIG || OCR_TEXT_RAW || "";
  const current = getWorkText();
  if (!original && !current) {
    return;
  }
  if (original === current) {
    TABLE_EDIT_MODE = false;
    renderLabTable(parseLabs(original));
    return;
  }
  setWorkText(original);
  TABLE_EDIT_MODE = false;
  renderLabTable(parseLabs(original));
}

function renderOCRMeta(meta) {
  applyStepMeta(1, meta, CURRENT_STEP === 1);
}

function getWorkText() { return $("workText")?.value || ""; }
function markTextEdited() {
  ANALYZED_READY = false;
  STEP_META[2] = null;
  STEP_META[3] = null;
  setCurrentStep(1);
  ANALYSIS.summary = "";
  if (!ANALYSIS.data) {
    ANALYSIS.data = { tables: [], blood_test_results: [], suggested_tags: [] };
  }
  ANALYSIS.data.summary = "";
  ANALYSIS.data.suggested_tags = [];
  ANALYSIS.data.detected_specialty = "";
  ANALYSIS.data.lab_overview = "";
  ANALYSIS.suggested_tags = [];
  ANALYSIS.detected_specialty = "";
  ANALYSIS.lab_overview = "";
  SUMMARY_MANUAL = false;
  setSummaryLocked(false);
  setSummaryNotice("");
  renderSummary("");
  renderSuggestedTags([], "");
  const btn = $("btnConfirm");
  if (btn) {
    btn.removeAttribute("aria-disabled");
    dis(btn, false);
  }
  updateButtons();
}
function setWorkText(t, opts = {}) {
  const ta = $("workText");
  if (!ta) return;
  ta.value = t || "";
  if (!opts.silent) {
    markTextEdited();
  }
}

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
    const rawText = data?.ocr_text ?? data?.text ?? "";
    const normalizedText = data?.normalized_text || cleanOCRText(rawText);
    const meta = { ...(data?.meta || data?.ocr_meta || {}) };
    if (!meta.engine) meta.engine = data?.source || data?.engine || "OCR Service";
    OCR_META = meta || {};
    applyStepMeta(1, OCR_META, true);
    OCR_TEXT_RAW = rawText;
    OCR_TEXT_ORIG = normalizedText;
    setWorkText(normalizedText, { silent: true });
    markTextEdited();
    renderSummary("");
    updateButtons();
    renderSuggestedTags([], "");
    const labs = parseLabs(OCR_TEXT_ORIG);
    renderLabTable(labs);
  } catch {
    showError("OCR неуспешен.");
  } finally { setBusy(false); }
}

async function doAnalyze() {
  clearError();
  hideAnalysisNotice();
  const text = getWorkText();
  const p = picksPayload();
  if (!text.trim() || !requiredTagsReady()) { showError("Липсват данни за анализ."); return; }
  if (SUMMARY_MANUAL) {
    const ok = window.confirm("Резюмето е редактирано ръчно. Новият анализ ще го замени. Желаете ли да продължите?");
    if (!ok) {
      return;
    }
  }
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
    const payloadData = data && typeof data.data === "object" && data.data ? { ...data.data } : {};
    ANALYSIS = { ...data, data: payloadData, meta };
    updateAnalysisStatus(meta);
    const normalizedTextApi = (payloadData.normalized_text || data.normalized_text || "").toString();
    if (normalizedTextApi && normalizedTextApi !== text) {
      setWorkText(normalizedTextApi, { silent: true });
    }
    const summaryText = (
      data.summary ??
      payloadData.summary ??
      data.result?.summary ??
      data.summary_text ??
      ""
    ).toString();
    const labOverview = (
      payloadData.lab_overview ??
      data.lab_overview ??
      ""
    ).toString().trim();
    const summaryPieces = [];
    if (summaryText.trim()) summaryPieces.push(summaryText.trim());
    if (labOverview) summaryPieces.push(labOverview);
    const combinedSummary = summaryPieces.join("\n\n");
    ANALYSIS.summary = combinedSummary;
    ANALYSIS.summary_text = combinedSummary;
    if (!ANALYSIS.data) ANALYSIS.data = {};
    ANALYSIS.data.summary = combinedSummary;
    ANALYSIS.data.lab_overview = labOverview;
    if (normalizedTextApi) ANALYSIS.data.normalized_text = normalizedTextApi;
    renderSummary(combinedSummary, { fromAnalysis: true });
    const baseRows = Array.isArray(payloadData.blood_test_results)
      ? payloadData.blood_test_results
      : Array.isArray(data.blood_test_results)
        ? data.blood_test_results
        : Array.isArray(data.result?.blood_test_results)
          ? data.result.blood_test_results
          : [];
    let rows = normalizeRows(baseRows);
    if (!rows.length) {
      const fallbackText = normalizedTextApi || text;
      rows = parseLabs(fallbackText);
    }
    TABLE_EDIT_MODE = false;
    renderLabTable(rows);
    const rawTags = (
      payloadData.suggested_tags ??
      data.suggested_tags ??
      data.result?.suggested_tags ??
      []
    );
    const tags = Array.isArray(rawTags)
      ? Array.from(new Set(rawTags.map((t) => (t == null ? "" : String(t).trim())).filter(Boolean)))
      : [];
    const specialtyText = (
      payloadData.detected_specialty ??
      data.detected_specialty ??
      data.result?.detected_specialty ??
      ""
    ).toString();
    ANALYSIS.suggested_tags = tags;
    ANALYSIS.data.suggested_tags = tags;
    ANALYSIS.data.detected_specialty = specialtyText;
    ANALYSIS.detected_specialty = specialtyText;
    renderSuggestedTags(tags, specialtyText);
    ANALYSIS.normalized_text = normalizedTextApi;
    ANALYSIS.lab_overview = labOverview;
    ANALYZED_READY = !meta.retry_suggested;
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
  if (TABLE_EDIT_MODE) {
    const edited = collectTableEdits();
    TABLE_EDIT_MODE = false;
    renderLabTable(edited);
  }
  setBusy(true);
  try {
    const summaryText = getSummaryText().trim();
    syncSummaryState(summaryText);
    const fd = new FormData();
    fd.append("file", raw.file);
    fd.append("file_kind", raw.fileKind || FILE_KIND || "");
    fd.append("category_id", p.category_id || "");
    fd.append("specialty_id", p.specialty_id || "");
    fd.append("doc_type_id", p.doc_type_id || "");
    fd.append("ocr_text", OCR_TEXT_ORIG || text || "");
    fd.append("text", text || "");
    if (p.event_id) fd.append("event_id", p.event_id);
    if (summaryText) fd.append("summary", summaryText);
    const eventDate = ANALYSIS.data?.event_date || ANALYSIS.event_date || "";
    if (eventDate) {
      fd.append("event_date", eventDate);
      fd.append("document_date", eventDate);
    }
    const labsPayload = getLabResults();
    if (labsPayload.length) {
      fd.append("blood_test_results", JSON.stringify(labsPayload));
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
    let data = {};
    try { data = await res.json(); } catch {}
    if (res.status === 409) {
      const docId = data?.document_id;
      const historyUrl = data?.redirect_url || CONFIG.history_url || CONFIG.documents_url || "";
      const label = data?.redirect_url ? "Виж в историята" : (CONFIG.history_url ? "История" : "Документи");
      const linkHtml = historyUrl ? `<a class="underline font-semibold" href="${escapeHtml(historyUrl)}">${escapeHtml(label)}</a>` : "";
      const parts = [`Файлът вече е качен${docId ? ` (Документ №${docId})` : ""}.`];
      if (linkHtml) parts.push(linkHtml);
      showError(parts.join(" "), { allowHTML: true });
      DUPLICATE_DETECTED = true;
      ANALYZED_READY = false;
      updateButtons();
      return;
    }
    if (!res.ok) throw new Error("confirm_failed");
    let ok = res.ok;
    const meta = data?.meta || {};
    if (res.ok && (data?.ok || data?.success || data?.saved || data?.id || data?.document_id)) {
      ok = true;
    }
    if (ok) {
      const btn = $("btnConfirm");
      if (btn) { btn.setAttribute("aria-disabled","true"); dis(btn, true); }
      showStatus("Документът е записан успешно.");
      applyStepMeta(3, { ...meta, document_id: data?.document_id, event_id: data?.event_id }, true);
      setSummaryLocked(true);
      SUMMARY_MANUAL = false;
      setSummaryNotice("Документът е записан успешно.");
      DUPLICATE_DETECTED = false;
      const redirectTarget = data?.redirect_url || CONFIG.documents_url || "";
      if (redirectTarget) {
        setTimeout(() => {
          window.location.href = redirectTarget;
        }, 800);
      }
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
  const btnRefreshTable = $("btnRefreshTable");
  const btnToggleTableEdit = $("btnToggleTableEdit");
  const btnNormalizeText = $("btnNormalizeText");
  const btnRestoreText = $("btnRestoreText");
  const btnRetryAnalyze = $("btnRetryAnalyze");

  cat && cat.addEventListener("change", () => { updateDropdownFlow(); wireSuggest(); updateButtons(); });
  spc && spc.addEventListener("change", () => { updateDropdownFlow(); wireSuggest(); updateButtons(); });
  doc && doc.addEventListener("change", () => { updateDropdownFlow(); wireSuggest(); updateButtons(); });
  kind && kind.addEventListener("change", () => { if (!FILE_KIND_LOCK) FILE_KIND = kind.value || ""; updateDropdownFlow(); updateButtons(); });
  file && file.addEventListener("change", handleFileInputChange);
  btnChoose && btnChoose.addEventListener("click", () => { if (file && !file.disabled) file.click(); });
  btnOCR && btnOCR.addEventListener("click", doOCR);
  btnAnalyze && btnAnalyze.addEventListener("click", doAnalyze);
  btnRetryAnalyze && btnRetryAnalyze.addEventListener("click", doAnalyze);
  btnConfirm && btnConfirm.addEventListener("click", doConfirm);
  btnRefreshTable && btnRefreshTable.addEventListener("click", refreshTableFromText);
  btnToggleTableEdit && btnToggleTableEdit.addEventListener("click", toggleTableEditMode);
  btnNormalizeText && btnNormalizeText.addEventListener("click", normalizeCurrentText);
  btnRestoreText && btnRestoreText.addEventListener("click", restoreOriginalOCRText);

  const ta = $("workText");
  ta && ta.addEventListener("input", () => {
    markTextEdited();
  });
  const summaryField = getSummaryField();
  summaryField && summaryField.addEventListener("input", () => {
    SUMMARY_MANUAL = true;
    if (SUMMARY_LOCKED) {
      setSummaryLocked(false);
    }
    const value = summaryField.value || "";
    syncSummaryState(value);
    if (value.trim()) {
      setSummaryNotice("Резюмето е редактирано ръчно. Нов анализ ще го замени.");
    } else {
      setSummaryNotice("");
    }
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
