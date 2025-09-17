const API = { ocr: "/api/upload/ocr/", analyze: "/api/upload/analyze/", confirm: "/api/upload/confirm/", suggest: "/api/events/suggest/" };

function el(id) { return document.getElementById(id); }
function show(x) { if (x) x.classList.remove("hidden"); }
function hide(x) { if (x) x.classList.add("hidden"); }
function seth(x, h) { if (x) x.innerHTML = h || ""; }
function setv(x, v) { if (x) x.value = v || ""; }
function dis(x, f) { if (!x) return; x.disabled = !!f; x.classList.toggle("opacity-50", !!f); x.classList.toggle("cursor-not-allowed", !!f); }
function getCSRF() { const t = document.querySelector('input[name="csrfmiddlewaretoken"]'); if (t && t.value) return t.value; const m = document.cookie.match(/(?:^|;)\s*csrftoken=([^;]+)/); return m ? decodeURIComponent(m[1]) : ""; }
function ensureUXStyles() { if (document.getElementById("uxUploadInject")) return; const s = document.createElement("style"); s.id = "uxUploadInject"; s.textContent = `.btn[aria-disabled="true"]{opacity:.5;cursor:not-allowed;pointer-events:none}.btn.btn-armed:hover{filter:brightness(1.05)}`; document.head.appendChild(s); }

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

function currentTags() { const p = picksPayload(); return { category_id: p.category_id, specialty_id: p.specialty_id, doc_type_id: p.doc_type_id, file_kind: p.file_kind }; }

function lockDocType() { DOC_LOCK = true; dis(el("sel_doc_type"), true); }
function lockClassification() { CLASS_LOCK = true; ["sel_category","sel_specialty","sel_doc_type","file_kind"].forEach(id => dis(el(id), true)); }

function stepLabelNode() {
  let n = document.querySelector('label[for="workText"]');
  if (!n) n = el("workLabel") || el("ocrLabel") || el("workMeta");
  if (!n) { const ta = el("workText"); if (ta && ta.parentElement) { n = document.createElement("div"); n.id = "workMeta"; n.className = "text-xs text-gray-600 mb-1"; ta.parentElement.insertBefore(n, ta); } }
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
  if (CURRENT_FILE_URL) { try { URL.revokeObjectURL(CURRENT_FILE_URL); } catch(_) {} CURRENT_FILE_URL = null; }
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
  const p = picksPayload();
  if (!(p.category_id && p.specialty_id && p.doc_type_id && p.file_kind)) { if (wrap) hide(wrap); if (select) seth(select, ""); return; }
  try {
    const qs = new URLSearchParams({ category_id: p.category_id, specialty_id: p.specialty_id, doc_type_id: p.doc_type_id, file_kind: p.file_kind });
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
      rl = rl != null ? rl : (isNaN(parseFloat(a)) ? null : parseFloat(a));
      rh = rh != null ? rh : (isNaN(parseFloat(b)) ? null : parseFloat(b));
    }
    out.push({ name, value, unit, ref_low: rl != null ? rl : null, ref_high: rh != null ? rh : null });
  });
  return out;
}

function renderLabTable(items) {
  const wrap = el("labWrap");
  const slot = el("labTableSlot");
  const sum = el("labSummary");
  if (!wrap || !slot) return;
  if (!items || !items.length) { hide(wrap); seth(slot, ""); if (sum) seth(sum, ""); return; }
  const rows = items.map(x => {
    const inRef = (x.ref_low != null && x.ref_high != null && typeof x.value === "number") ? (x.value >= x.ref_low && x.value <= x.ref_high) : null;
    const warn = inRef === false ? "font-semibold text-danger" : "";
    const unit = x.unit ? x.unit : "";
    const ref = (x.ref_low != null && x.ref_high != null) ? `${x.ref_low} - ${x.ref_high}` : "";
    return `
      <tr>
        <td class="border border-primaryDark bg-white px-3 py-2">${x.name}</td>
        <td class="border border-primaryDark bg-white px-3 py-2 ${warn}">${x.value}</td>
        <td class="border border-primaryDark bg-white px-3 py-2">${unit}</td>
        <td class="border border-primaryDark bg-white px-3 py-2">${ref}</td>
      </tr>`;
  }).join("");
  const html = `
    <table class="w-full border-separate border-spacing-0 text-primaryDark">
      <thead>
        <tr>
          <th class="border border-primaryDark bg-white px-3 py-2 text-left">Показател</th>
          <th class="border border-primaryDark bg-white px-3 py-2 text-left">Стойност</th>
          <th class="border border-primaryDark bg-white px-3 py-2 text-left">Ед.</th>
          <th class="border border-primaryDark bg-white px-3 py-2 text-left">Реф.</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>`;
  seth(slot, html);
  if (sum) seth(sum, `${items.length} показателя`);
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

function renderSummary(summary, data) {
  const box = el("analysisSummary") || el("summaryBox") || el("summaryPanel") || el("summarySlot");
  if (!box) return;
  const labs = normalizeRows((data && (data.blood_test_results || [])) || []);
  const tags = (data && data.suggested_tags) || [];
  const tableStats = labs.length ? `<div class="text-sm">Показатели: ${labs.length}</div>` : "";
  const tagsLine = tags.length ? `<div class="text-sm">Тагове: ${tags.join(", ")}</div>` : "";
  const text = (summary || "").trim();
  const body = text ? `<div class="whitespace-pre-line text-sm leading-6">${text}</div>` : `<div class="text-sm italic text-gray-600">Няма обобщение.</div>`;
  seth(box, `<div class="space-y-2">${body}${tableStats}${tagsLine}</div>`);
  show(box);
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
  const cls = "px-4 h-10 rounded-xl text-white bg-primaryDark hover:brightness-105";
  let bar = el("labControls");
  if (!bar) {
    bar = document.createElement("div");
    bar.id = "labControls";
    bar.className = "flex gap-2 mb-2";
    bar.innerHTML = `
      <button id="btnRefreshTable" class="${cls}">Обнови таблицата</button>
      <button id="btnEditTable" class="${cls}">Редакция на таблицата</button>
      <button id="btnSyncToText" class="${cls}">Синхронизирай към текст</button>
      <button id="btnRevertOCR" class="${cls}">Върни OCR текста</button>
    `;
    wrap.insertBefore(bar, wrap.firstChild);
  } else {
    ["btnRefreshTable","btnEditTable","btnSyncToText","btnRevertOCR"].forEach(id => { const b = el(id); if (b) b.className = cls; });
  }
  el("btnRefreshTable").onclick = (e) => { e.preventDefault(); refreshTableFromText(); ANALYZED_READY = false; updateButtons(); };
  el("btnEditTable").onclick = (e) => { e.preventDefault(); LAB_EDIT_MODE = !LAB_EDIT_MODE; setTableEditable(LAB_EDIT_MODE); ANALYZED_READY = false; updateButtons(); e.currentTarget.textContent = LAB_EDIT_MODE ? "Изход от редакция" : "Редакция на таблицата"; };
  el("btnSyncToText").onclick = (e) => { e.preventDefault(); syncTableToText(); ANALYZED_READY = false; updateButtons(); };
  el("btnRevertOCR").onclick = (e) => { e.preventDefault(); if (!ORIGINAL_OCR_TEXT) return; const ta = el("workText"); setv(ta, ORIGINAL_OCR_TEXT); renderLabTable(parseLabs(ORIGINAL_OCR_TEXT)); ANALYZED_READY = false; updateButtons(); };
}

function getSelectedLabel(selId) { const s = el(selId); if (!s) return ""; const o = s.options && s.options[s.selectedIndex]; return o ? (o.text || "").trim() : ""; }

function inferFormatHint() {
  const label = getSelectedLabel("sel_doc_type").toLowerCase();
  if (!label) return "";
  if (label.includes("кръв")) return "table";
  if (label.includes("епикриз")) return "paragraph";
  if (label.includes("рецепт")) return "list";
  return "";
}

function anonymizeText(src) {
  let text = src || "";
  let count = 0;
  const repl = (re) => { const before = text; text = text.replace(re, "[REDACTED]"); if (text !== before) count++; };
  repl(/\b(?:ЕГН|EGN)\s*[:\-]?\s*\d{10}\b/gi);
  repl(/\b\d{10}\b/g);
  repl(/\b(?:\+?359|0)\d{8,9}\b/g);
  repl(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi);
  repl(/№\s*\d+/g);
  return { text, meta: { redactions: count } };
}

function setMetaOCR(meta) {
  OCR_META = meta || {};
  const eng = (meta.engine || (meta.engines || [])[0] || "").toString();
  const method = (meta.method || "").toString();
  const lang = (meta.lang || (meta.langs || [])[0] || "").toString();
  const pages = meta.pages_total || meta.pages || "";
  const parts = [];
  parts.push("Стъпка 1: OCR сканиране");
  if (eng) parts.push(eng);
  if (method) parts.push(method);
  if (lang) parts.push(lang);
  if (pages) parts.push(`стр.${pages}`);
  setStepLabel(parts.join(" • "));
}

function setMetaAnalyze(data, payloadUsed) {
  const am = data.analysis_meta || data.meta || {};
  const provider = (am.provider || data.provider || data.vendor || "").toString();
  const model = (am.model || am.engine || data.model || data.engine || "").toString();
  const method = (am.method || am.strategy || "").toString();
  const lang = (am.lang || am.language || "").toString();
  const fmt = payloadUsed && payloadUsed.format_hint ? `format:${payloadUsed.format_hint}` : "";
  const parts = [];
  parts.push("Стъпка 2: AI Анализ");
  if (provider && model) parts.push(`${provider}:${model}`);
  else if (provider) parts.push(provider);
  else if (model) parts.push(model);
  if (method) parts.push(method);
  if (lang) parts.push(lang);
  if (fmt) parts.push(fmt);
  parts.push("anon");
  setStepLabel(parts.filter(Boolean).join(" • "));
}

async function doOCR() {
  clearError();
  if (!pipelineReady()) { showError("Задайте Категория, Специалност, Вид документ и Вид файл."); return; }
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
    const text = (data.ocr_text || data.text || "").toString();
    if (!text.trim()) { showError("Празен OCR резултат."); return; }
    const area = el("workText");
    if (area) area.removeAttribute("disabled");
    setv(area, text);
    ORIGINAL_OCR_TEXT = text;
    setMetaOCR(data.ocr_meta || {});
    renderLabTable(parseLabs(text));
    ANALYZED_READY = false;
    updateButtons();
  } catch (_) {
    showError("OCR грешка при заявката.");
  } finally {
    setBusy(false);
  }
}

async function doAnalyze() {
  clearError();
  if (!requiredTagsReady()) { showError("Изберете Категория, Специалност и Вид документ."); return; }
  const area = el("workText");
  const raw = (area ? area.value : "") || "";
  if (!raw.trim()) { showError("Липсва текст за анализ."); return; }
  setBusy(true);
  try {
    lockClassification();
    const p = picks();
    const anon = anonymizeText(raw);
    const payload = { text: anon.text, anonymized: true, anonymization_meta: anon.meta, ...currentTags() };
    const fmt = inferFormatHint();
    if (fmt) payload.format_hint = fmt;
    if (p.eventId) payload.event_id = p.eventId;
    const res = await fetch(API.analyze, { method: "POST", headers: { "Content-Type": "application/json", "X-CSRFToken": getCSRF() }, credentials: "same-origin", body: JSON.stringify(payload) });
    if (!res.ok) throw new Error("analyze_failed");
    const data = await res.json();
    const summary = (data.summary || "").toString();
    ANALYSIS = { summary, data: data.data || { tables: [], blood_test_results: [], suggested_tags: [] } };
    const tablesA = (ANALYSIS.data.tables || []).flatMap(t => normalizeRows(t.rows || t));
    const rowsFromBlood = normalizeRows(ANALYSIS.data.blood_test_results || []);
    const rows = tablesA.length ? tablesA : rowsFromBlood.length ? rowsFromBlood : parseLabs(raw);
    renderSummary(ANALYSIS.summary, ANALYSIS.data);
    renderLabTable(rows);
    setMetaAnalyze(data, payload);
    ANALYZED_READY = true;
    updateButtons();
  } catch (_) { showError("Грешка при анализ."); }
  finally { setBusy(false); }
}

async function doConfirm() {
  clearError();
  if (!requiredTagsReady()) { showError("Изберете Категория, Специалност и Вид документ."); return; }
  if (!ANALYZED_READY) { showError("Първо стартирайте AI анализ."); return; }
  const area = el("workText");
  const text = (area ? area.value : "") || "";
  if (!text.trim()) { showError("Няма данни за запис."); return; }
  setBusy(true);
  try {
    lockClassification();
    const body = { picks: picksPayload(), text, summary: ANALYSIS.summary || "", data: ANALYSIS.data || {}, ocr_meta: OCR_META || {}, suggested_tags: (ANALYSIS.data && ANALYSIS.data.suggested_tags) || [] };
    const res = await fetch(API.confirm, { method: "POST", headers: { "Content-Type": "application/json", "X-CSRFToken": getCSRF() }, credentials: "same-origin", body: JSON.stringify(body) });
    if (!res.ok) throw new Error("confirm_failed");
    const out = await res.json().catch(() => ({}));
    const msg = el("successBox");
    if (msg) {
      const eid = out.event_id ? `Събитие #${out.event_id}` : "";
      const did = out.document_id ? `Документ #${out.document_id}` : "";
      const labs = typeof out.labs_saved === "number" ? `Записани показатели: ${out.labs_saved}` : "";
      const lines = [eid, did, labs].filter(Boolean).join(" • ");
      msg.textContent = lines || "Записано.";
      show(msg);
    }
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
  updateDropdownFlow();
  updateButtons();
  suggestIfReady();
  const ta = el("workText");
  if (ta) ta.addEventListener("input", () => { ANALYZED_READY = false; updateButtons(); });
  setStepLabel("Стъпка 1: OCR сканиране");
}

document.addEventListener("DOMContentLoaded", bindUI);
