const API = {
  ocr: "/api/upload/ocr/",
  analyze: "/api/upload/analyze/",
  confirm: "/api/upload/confirm/",
  suggest: "/api/events/suggest/"
};

function el() {
  const ids = Array.from(arguments);
  for (let i = 0; i < ids.length; i++) {
    const x = document.getElementById(ids[i]);
    if (x) return x;
  }
  return null;
}

function show(x) { if (x) x.classList.remove("hidden"); }
function hide(x) { if (x) x.classList.add("hidden"); }
function setv(x, v) { if (x) x.value = v || ""; }
function seth(x, h) { if (x) x.innerHTML = h || ""; }
function dis(x, f) { if (x) x.disabled = !!f; }

function getCSRF() {
  const inps = document.querySelectorAll('input[name="csrfmiddlewaretoken"]');
  if (inps.length) return inps[0].value;
  const m = document.cookie.match(/csrftoken=([^;]+)/);
  return m ? m[1] : "";
}

async function toB64(f) {
  if (!f) return "";
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(String(r.result).split(",")[1] || "");
    r.onerror = reject;
    r.readAsDataURL(f);
  });
}

function picks() {
  return {
    category: (el("categorySelect","sel_category")||{}).value || "",
    specialty: (el("specialtySelect","sel_specialty")||{}).value || "",
    docType: (el("docTypeSelect","sel_doc_type")||{}).value || "",
    file: (el("fileInput","file_input")||{}).files ? el("fileInput","file_input").files[0] : null,
    fileKind: (el("fileKindSelect","file_kind")||{}).value || "",
    eventId: (el("existingEventSelect")||{}).value || ""
  };
}

async function suggestIfReady() {
  const wrap = el("existingEventWrap");
  const select = el("existingEventSelect");
  const p = picks();
  if (!(p.category && p.specialty && p.docType)) {
    if (wrap) hide(wrap);
    if (select) seth(select, "");
    return;
  }
  try {
    const u = `${API.suggest}?category_id=${encodeURIComponent(p.category)}&specialty_id=${encodeURIComponent(p.specialty)}&doc_type_id=${encodeURIComponent(p.docType)}`;
    const res = await fetch(u, { credentials: "same-origin" });
    if (!res.ok) throw new Error("suggest_failed");
    const data = await res.json();
    const items = data.events || [];
    if (!select) return;
    if (!items.length) {
      seth(select, '<option value="">—</option>');
      if (wrap) show(wrap);
      return;
    }
    const opts = ['<option value="">—</option>'].concat(items.map(x => `<option value="${x.id}">${x.event_date}</option>`));
    seth(select, opts.join(""));
    if (wrap) show(wrap);
  } catch(e) {
    if (select) seth(select, '<option value="">—</option>');
    if (wrap) show(wrap);
  }
}

async function doOCR() {
  const p = picks();
  const ocrBtn = el("btnOCR");
  const ocrOut = el("ocrText","ocr_text");
  if (!(p.file && p.fileKind && p.category && p.specialty && p.docType)) return;
  const fd = new FormData();
  fd.append("file", p.file);
  fd.append("file_kind", p.fileKind);
  fd.append("category_id", p.category);
  fd.append("specialty_id", p.specialty);
  fd.append("doc_type_id", p.docType);
  if (ocrBtn) dis(ocrBtn, true);
  try {
    const res = await fetch(API.ocr, { method: "POST", credentials: "same-origin", body: fd });
    if (!res.ok) throw new Error("ocr_failed");
    const data = await res.json();
    if (ocrOut) setv(ocrOut, data.ocr_text || "");
    const info = el("ocrSourceInfo");
    if (info) info.textContent = data.source ? `OCR: ${data.source}` : "";
    return data.ocr_text || "";
  } catch(e) {
    if (ocrOut) setv(ocrOut, "");
    return "";
  } finally {
    if (ocrBtn) dis(ocrBtn, false);
  }
}

async function doAnalyze() {
  const p = picks();
  const analyzeBtn = el("btnAnalyze");
  const ocrOut = el("ocrText","ocr_text");
  const summaryOut = el("summaryText","summary_text");
  const txt = ocrOut ? (ocrOut.value || "") : "";
  if (!(txt && p.specialty)) return;
  if (analyzeBtn) dis(analyzeBtn, true);
  try {
    const res = await fetch(API.analyze, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": getCSRF() },
      credentials: "same-origin",
      body: JSON.stringify({ text: txt, specialty_id: p.specialty })
    });
    if (!res.ok) throw new Error("analyze_failed");
    const data = await res.json();
    const s = (data && data.data && data.data.summary) || data.summary || "";
    if (summaryOut) setv(summaryOut, s || "");
    const meta = el("analysisMeta");
    if (meta) {
      const evd = (data && data.data && data.data.event_date) || "";
      const det = (data && data.data && data.data.detected_specialty) || "";
      meta.textContent = [evd, det].filter(Boolean).join(" • ");
    }
    const payload = el("analysisPayload");
    if (payload) payload.setAttribute("data-json", JSON.stringify(data));
    return data;
  } catch(e) {
    if (summaryOut) setv(summaryOut, "");
    const payload = el("analysisPayload");
    if (payload) payload.setAttribute("data-json", "{}");
    return null;
  } finally {
    if (analyzeBtn) dis(analyzeBtn, false);
  }
}

async function doConfirm() {
  const p = picks();
  const btn = el("btnConfirm","btn_upload");
  const ocrOut = el("ocrText","ocr_text");
  const summaryOut = el("summaryText","summary_text");
  if (!(p.file && p.category && p.specialty && p.docType)) return;
  let finalText = ocrOut ? (ocrOut.value || "") : "";
  if (!finalText) {
    const t = await doOCR();
    finalText = t || "";
  }
  const finalSummary = summaryOut ? (summaryOut.value || "") : "";
  const fileB64 = await toB64(p.file);
  const analysisPayloadEl = el("analysisPayload");
  let analysis = {};
  if (analysisPayloadEl) {
    try { analysis = JSON.parse(analysisPayloadEl.getAttribute("data-json") || "{}"); } catch(_){}
  }
  const payload = {
    category_id: p.category,
    specialty_id: p.specialty,
    doc_type_id: p.docType,
    event_id: p.eventId || null,
    final_text: finalText,
    final_summary: finalSummary,
    analysis: analysis,
    file_b64: fileB64,
    file_name: p.file.name || "document.bin",
    file_mime: p.file.type || "application/octet-stream",
    file_kind: p.fileKind || "other"
  };
  if (btn) dis(btn, true);
  try {
    const res = await fetch(API.confirm, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": getCSRF() },
      credentials: "same-origin",
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error("confirm_failed");
    const data = await res.json();
    window.location.href = "/upload/history/";
  } catch(e) {
  } finally {
    if (btn) dis(btn, false);
  }
}

function bindUI() {
  const cat = el("categorySelect","sel_category");
  const spc = el("specialtySelect","sel_specialty");
  const doc = el("docTypeSelect","sel_doc_type");
  if (cat) cat.addEventListener("change", suggestIfReady);
  if (spc) spc.addEventListener("change", suggestIfReady);
  if (doc) doc.addEventListener("change", suggestIfReady);

  const bOCR = el("btnOCR");
  const bAna = el("btnAnalyze");
  const bCfm = el("btnConfirm","btn_upload");
  if (bOCR) bOCR.addEventListener("click", e => { e.preventDefault(); doOCR(); });
  if (bAna) bAna.addEventListener("click", e => { e.preventDefault(); doAnalyze(); });
  if (bCfm) bCfm.addEventListener("click", e => { e.preventDefault(); doConfirm(); });
}

document.addEventListener("DOMContentLoaded", bindUI);
