const API = {
  ocr: "/api/upload/ocr/",
  analyze: "/api/upload/analyze/",
  confirm: "/api/upload/confirm/",
  suggest: "/api/events/suggest/",
  doctorSuggest: "/api/doctors/suggest/"
};

function el(){ const ids=[...arguments]; for (let i=0;i<ids.length;i++){ const x=document.getElementById(ids[i]); if(x) return x; } return null; }
function show(x){ if(x) x.classList.remove("hidden"); }
function hide(x){ if(x) x.classList.add("hidden"); }
function setv(x,v){ if(x) x.value=v||""; }
function seth(x,h){ if(x) x.innerHTML=h||""; }

function dis(x,f){
  if(!x) return;
  x.disabled = !!f;
  if (f) {
    x.setAttribute("aria-disabled","true");
    x.style.opacity = "0.5";
    x.style.pointerEvents = "none";
  } else {
    x.removeAttribute("aria-disabled");
    x.style.opacity = "";
    x.style.pointerEvents = "";
  }
}

function getCSRF(){
  const inp=document.querySelector('input[name="csrfmiddlewaretoken"]');
  if (inp && inp.value) return inp.value;
  const m=document.cookie.match(/(?:^|;)\s*csrftoken=([^;]+)/);
  return m ? decodeURIComponent(m[1]) : "";
}

function picks(){
  return {
    category: (el("sel_category","categorySelect")||{}).value||"",
    specialty: (el("sel_specialty","specialtySelect")||{}).value||"",
    docType: (el("sel_doc_type","docTypeSelect")||{}).value||"",
    fileKind: (el("file_kind","fileKindSelect")||{}).value||"",
    file: (el("file_input","fileInput")||{}).files ? el("file_input","fileInput").files[0] : null,
    eventId: (el("existingEventSelect")||{}).value||""
  };
}

function stage(){
  const p=picks();
  const hasFile = !!p.file;
  const ocrVal = (el("ocrText","ocr_text")||{}).value || "";
  const sumVal = (el("summaryText","summary_text")||{}).value || "";
  if (!hasFile) return "choose_file";
  if (hasFile && !ocrVal.trim()) return "ocr";
  if (ocrVal.trim() && !sumVal.trim()) return "analyze";
  return "confirm";
}

function updateButtons(){
  const s=stage();
  const bOCR=el("btnOCR");
  const bAna=el("btnAnalyze");
  const bCfm=el("btnConfirm");
  if (bOCR) (s==="ocr") ? show(bOCR) : hide(bOCR);
  if (bAna) (s==="analyze") ? show(bAna) : hide(bAna);
  if (bCfm) (s==="confirm") ? show(bCfm) : hide(bCfm);
}

function setBusy(on){
  const form = el("uploadForm");
  const overlay = el("loadingOverlay");
  if (form) form.setAttribute("aria-busy", on ? "true" : "false");
  if (on) {
    if (form) form.classList.add("pointer-events-none");
    if (overlay) show(overlay);
  } else {
    if (form) form.classList.remove("pointer-events-none");
    if (overlay) hide(overlay);
  }
}

function showError(msg){
  const box=el("errorBox");
  if (box){ box.textContent = msg || "Възникна грешка. Опитайте отново."; show(box); }
}
function clearError(){
  const box=el("errorBox");
  if (box){ box.textContent=""; hide(box); }
}

function updateUI(){
  const p=picks();
  const spc=el("sel_specialty","specialtySelect");
  const doc=el("sel_doc_type","docTypeSelect");
  const kind=el("file_kind","fileKindSelect");
  const file=el("file_input","fileInput");
  const bOCR=el("btnOCR");
  const bAna=el("btnAnalyze");
  const bCfm=el("btnConfirm");

  dis(spc, !p.category); if (!p.category) setv(spc,"");
  dis(doc, !(p.category && p.specialty)); if (!(p.category && p.specialty)) setv(doc,"");

  const readyForKind = p.category && p.specialty && p.docType;
  dis(kind, !readyForKind); if (!readyForKind) setv(kind,"");

  const readyForFile = readyForKind && p.fileKind;
  dis(file, !readyForFile);
  // НИКОГА не нулирай file, ако вече има файл. Това предотвратява повторно отваряне на диалога.
  // if (!readyForFile) setv(file,"");  // премахнато

  const hasFile = readyForFile && p.file;
  if (bOCR) dis(bOCR, !hasFile);

  const ocrVal = (el("ocrText","ocr_text")||{}).value || "";
  const sumVal = (el("summaryText","summary_text")||{}).value || "";
  if (bAna) dis(bAna, !ocrVal.trim());
  if (bCfm) dis(bCfm, !(ocrVal.trim() && sumVal.trim()));

  updateButtons();
}

let _choosingFile = false;

async function suggestIfReady(){
  const wrap=el("existingEventWrap");
  const select=el("existingEventSelect");
  const p=picks();
  if (!(p.category && p.specialty && p.docType && p.fileKind)) {
    if (wrap) hide(wrap); if (select) seth(select,""); return;
  }
  try{
    const res = await fetch(API.suggest, {
      method:"POST",
      headers:{ "Content-Type":"application/json", "X-CSRFToken": getCSRF() },
      credentials:"same-origin",
      body: JSON.stringify({
        category_id: p.category,
        specialty_id: p.specialty,
        doc_type_id: p.docType,
        file_kind: p.fileKind
      })
    });
    if (!res.ok) throw new Error("suggest_failed");
    const data = await res.json();
    const items = data.events || [];
    if (!items.length) { if (wrap) hide(wrap); if (select) seth(select,""); return; }
    const opts=['<option value="">—</option>'].concat(items.map(x=>{
      const vid = x.id != null ? String(x.id) : "";
      const label = x.title || x.name || x.display_name || vid;
      return `<option value="${vid}">${label}</option>`;
    }));
    if (select) seth(select, opts.join("")); if (wrap) show(wrap);
  }catch(e){
    if (wrap) hide(wrap); if (select) seth(select,"");
  }
}

async function doOCR(){
  clearError();
  const p=picks(); if (!p.file) return;
  const ocrOut=el("ocrText","ocr_text"); const meta=el("ocrSourceInfo");
  const bOCR=el("btnOCR");

  const fd=new FormData();
  fd.append("file", p.file);
  fd.append("file_kind", p.fileKind || "");
  fd.append("med_category", p.category || "");
  fd.append("specialty", p.specialty || "");
  fd.append("doc_type", p.docType || "");

  setBusy(true); if (bOCR) dis(bOCR,true);
  try{
    const res = await fetch(API.ocr, { method:"POST", headers:{ "X-CSRFToken": getCSRF() }, credentials:"same-origin", body: fd });
    if (!res.ok) throw new Error("ocr_failed");

    let data;
    let text = "";
    const ct = (res.headers.get("content-type")||"").toLowerCase();
    if (ct.includes("application/json")) {
      data = await res.json();
      text = (data.ocr_text || data.text || (data.result && data.result.text) || (data.payload && data.payload.text) || "").toString();
      if (!text && (data.message || data.error)) showError(String(data.message || data.error));
    } else {
      const raw = await res.text();
      try { data = JSON.parse(raw); text = (data.ocr_text || data.text || ""); } catch(_){ text = raw || ""; }
    }

    if (!text.trim()) throw new Error("empty_ocr");

    if (ocrOut){ ocrOut.removeAttribute("disabled"); setv(ocrOut, text); }
    if (meta) meta.textContent = (data && (data.source || data.engine)) ? `OCR: ${data.source || data.engine}` : "";
  }catch(e){
    showError("OCR неуспешен или празен резултат. Опитайте отново.");
  }finally{
    if (bOCR) dis(bOCR,false);
    setBusy(false);
    updateUI();
  }
}

async function doAnalyze(){
  clearError();
  const ocrOut=el("ocrText","ocr_text");
  const sumOut=el("summaryText","summary_text");
  const bAna=el("btnAnalyze");
  const p=picks();
  const text = ocrOut ? (ocrOut.value || "") : "";
  if (!text.trim()) { showError("Липсва OCR текст за анализ."); updateUI(); return; }

  setBusy(true); if (bAna) dis(bAna,true);
  try{
    const res = await fetch(API.analyze, {
      method:"POST",
      headers:{ "Content-Type":"application/json", "X-CSRFToken": getCSRF() },
      credentials:"same-origin",
      body: JSON.stringify({ text, specialty_id: p.specialty })
    });
    if (!res.ok) throw new Error("analyze_failed");
    const data = await res.json();
    const summary = (data && (data.summary || (data.data && data.data.summary) || (data.result && data.result.summary) || "")) || "";
    if (!summary.trim()) throw new Error("empty_summary");
    if (sumOut){ sumOut.removeAttribute("disabled"); setv(sumOut, summary); }
    const meta = el("analysisMeta");
    if (meta){
      const evd = (data && data.data && data.data.event_date) || "";
      const det = (data && data.data && data.data.detected_specialty) || "";
      meta.textContent = [evd, det].filter(Boolean).join(" • ");
    }
    const payload = el("analysisPayload");
    if (payload) payload.setAttribute("data-json", JSON.stringify(data));
  }catch(e){
    showError("Анализът е неуспешен или сървърът не отговаря. Опитайте по-късно.");
  }finally{
    if (bAna) dis(bAna,false);
    setBusy(false);
    updateUI();
  }
}

function bindUI(){
  const cat=el("sel_category","categorySelect");
  const spc=el("sel_specialty","specialtySelect");
  const doc=el("sel_doc_type","docTypeSelect");
  const kind=el("file_kind","fileKindSelect");
  const file=el("file_input","fileInput");
  const choose=el("chooseFileBtn");
  const bOCR=el("btnOCR");
  const bAna=el("btnAnalyze");
  const bCfm=el("btnConfirm");

  if (cat)  cat.addEventListener("change", ()=>{ updateUI(); suggestIfReady(); clearError(); });
  if (spc)  spc.addEventListener("change", ()=>{ updateUI(); suggestIfReady(); clearError(); });
  if (doc)  doc.addEventListener("change", ()=>{ updateUI(); suggestIfReady(); clearError(); });
  if (kind) kind.addEventListener("change", ()=>{ updateUI(); suggestIfReady(); clearError(); });
  if (file) file.addEventListener("change", ()=>{
    _choosingFile = false;
    updateUI();
    clearError();
    const btn = el("chooseFileBtn");
    if (btn) btn.blur();
  });

  if (choose){
    choose.addEventListener("click", (e)=>{
      e.preventDefault();
      if (_choosingFile) return;
      _choosingFile = true;
      const f=el("file_input","fileInput");
      if (f) f.click();
    });
  }

  if (bOCR){ bOCR.addEventListener("click", (e)=>{ e.preventDefault(); doOCR(); }); }
  if (bAna){ bAna.addEventListener("click", (e)=>{ e.preventDefault(); doAnalyze(); }); }
  if (bCfm){ bCfm.addEventListener("click", (e)=>{ e.preventDefault(); /* doConfirm(); */ }); }

  updateUI();
  suggestIfReady();
}

document.addEventListener("DOMContentLoaded", bindUI);
