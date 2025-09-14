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
  if (f) { x.setAttribute("aria-disabled","true"); x.style.opacity="0.5"; x.style.pointerEvents="none"; }
  else { x.removeAttribute("aria-disabled"); x.style.opacity=""; x.style.pointerEvents=""; }
}
function getCSRF(){
  const inp=document.querySelector('input[name="csrfmiddlewaretoken"]');
  if (inp && inp.value) return inp.value;
  const m=document.cookie.match(/(?:^|;)\s*csrftoken=([^;]+)/);
  return m ? decodeURIComponent(m[1]) : "";
}

let _choosingFile = false;
let _fileURL = null; // for preview revoke

function picks(){
  return {
    category: (el("sel_category")||{}).value||"",
    specialty: (el("sel_specialty")||{}).value||"",
    docType: (el("sel_doc_type")||{}).value||"",
    fileKind: (el("file_kind")||{}).value||"",
    file: (el("file_input")||{}).files ? el("file_input").files[0] : null,
    eventId: (el("existingEventSelect")||{}).value||""
  };
}

function stage(){
  const p=picks();
  const hasFile = !!p.file;
  const text = (el("workText")||{}).value || "";
  if (!hasFile) return "choose_file";
  if (hasFile && !text.trim()) return "ocr";
  return "analyze"; // след OCR имаме текст → следва Analyze и Confirm
}

function updateButtons(){
  const s=stage();
  const bOCR=el("btnOCR"), bAna=el("btnAnalyze"), bCfm=el("btnConfirm");
  if (bOCR) (s==="ocr") ? show(bOCR) : hide(bOCR);
  if (bAna) (s!=="ocr") ? show(bAna) : hide(bAna);
  if (bCfm) (s!=="ocr") ? show(bCfm) : hide(bCfm);
}

function setBusy(on){
  const form = el("uploadForm");
  const overlay = el("loadingOverlay");
  if (form) form.setAttribute("aria-busy", on ? "true" : "false");
  if (on) { if (form) form.classList.add("pointer-events-none"); if (overlay) show(overlay); }
  else { if (form) form.classList.remove("pointer-events-none"); if (overlay) hide(overlay); }
}

function showError(msg){
  const box=el("errorBox"); if (box){ box.textContent = msg || "Възникна грешка."; show(box); }
}
function clearError(){ const box=el("errorBox"); if (box){ box.textContent=""; hide(box); } }

function renderPreview(file){
  const wrap = el("previewWrap"), slot = el("previewSlot"), meta = el("fileMeta");
  if (!file || !wrap || !slot) { if (wrap) hide(wrap); return; }
  if (_fileURL){ URL.revokeObjectURL(_fileURL); _fileURL=null; }
  const name = file.name || "file";
  const sizeKB = Math.round((file.size||0)/1024);
  const type = (file.type||"").toLowerCase();
  _fileURL = URL.createObjectURL(file);

  let html = "";
  if (type.startsWith("image/")){
    html = `<img src="${_fileURL}" alt="preview" class="max-h-[320px] rounded">`;
  } else if (type==="application/pdf" || name.toLowerCase().endsWith(".pdf")) {
    html = `<embed src="${_fileURL}" type="application/pdf" class="w-full h-[320px] rounded" />`;
  } else {
    html = `<div class="text-slate-600"><i class="fa-regular fa-file mr-2"></i>${name}</div>`;
  }
  seth(slot, html);
  if (meta) meta.textContent = `${name} • ${sizeKB} KB • ${type||"unknown"}`;
  show(wrap);
}

function parseLabs(text){

  const lines = (text||"").split(/\r?\n/).map(s=>s.trim()).filter(Boolean);
  const items = [];
  const kvRe = /^([A-Za-zА-Яа-я0-9\.\(\)\/\-\s]+?)\s+([\-+]?\d+(?:[\.,]\d+)?)(?:\s*([A-Za-zμ%\/\.\-\^\d]+))?$/;
  const refRe = /^(\d+(?:[\.,]\d+)?)\s*[-–]\s*(\d+(?:[\.,]\d+)?)/;

  let refBlock = [];
  for (let i=0;i<lines.length;i++){
    if (/REFERENCE\s*INTERVAL/i.test(lines[i])) { refBlock = lines.slice(i+1); break; }
  }

  for (const ln of lines){

    if (/^(tests|result|flag|units|reference|comp\.|panel)/i.test(ln)) continue;
    const m = ln.match(kvRe);
    if (!m) continue;
    const name = m[1].replace(/\s{2,}/g,' ').trim();
    const val = m[2].replace(',','.');
    const unit = (m[3]||"").trim();
    items.push({ name, value: parseFloat(val), unit: unit || null, ref_low: null, ref_high: null });
  }

  if (refBlock.length){
    const refs = refBlock.map(s=>s.match(refRe)?.slice(1,3) || null).filter(Boolean);
    for (let i=0;i<items.length && i<refs.length;i++){
      const [low,high]=refs[i]; items[i].ref_low=parseFloat(String(low).replace(',','.')); items[i].ref_high=parseFloat(String(high).replace(',','.'));
    }
  }
  return items;
}

function renderLabTable(items){
  const wrap=el("labWrap"), slot=el("labTableSlot"), sum=el("labSummary");
  if (!wrap || !slot){ return; }
  if (!items || !items.length){ hide(wrap); seth(slot,""); if (sum) seth(sum,""); return; }
  const rows = items.map(x=>{
    const inRef = (x.ref_low!=null && x.ref_high!=null && typeof x.value==="number")
      ? (x.value>=x.ref_low && x.value<=x.ref_high) : null;
    const cls = inRef===false ? ' style="color:#b91c1c;font-weight:600;"' : '';
    const unit = x.unit ? x.unit : '';
    const ref = (x.ref_low!=null && x.ref_high!=null) ? `${x.ref_low} - ${x.ref_high}` : '';
    return `<tr>
      <td>${x.name}</td>
      <td${cls}>${x.value}</td>
      <td>${unit}</td>
      <td>${ref}</td>
    </tr>`;
  });
  const html = `<table class="tbl">
    <thead><tr><th>Показател</th><th>Стойност</th><th>Ед.</th><th>Реф.</th></tr></thead>
    <tbody>${rows.join("")}</tbody>
  </table>`;
  seth(slot, html);
  if (sum) seth(sum, `${items.length} показателя`);
  show(wrap);
}

function updateUI(){
  const p=picks();
  const spc=el("sel_specialty"); const doc=el("sel_doc_type"); const kind=el("file_kind"); const file=el("file_input");
  const readySpc = !!p.category;
  const readyDoc = p.category && p.specialty;
  const readyKind = readyDoc && !!p.docType;
  const readyFile = readyKind && !!p.fileKind;

  dis(spc, !readySpc); if (!readySpc) setv(spc,"");
  dis(doc, !readyDoc); if (!readyDoc) setv(doc,"");
  dis(kind, !readyKind); if (!readyKind) setv(kind,"");
  dis(file, !readyFile);

  const s=stage();
  const label = el("workLabel");
  const meta = el("workMeta");
  if (label) label.textContent = (s==="ocr") ? "OCR текст" : "Резюме / анализ";
  if (meta) meta.textContent = "";

  updateButtons();
}

async function suggestIfReady(){
  const wrap=el("existingEventWrap");
  const select=el("existingEventSelect");
  const p=picks();
  if (!(p.category && p.specialty && p.docType && p.fileKind)) {
    if (wrap) hide(wrap); if (select) seth(select,""); return;
  }
  try{
    const qs = new URLSearchParams({ category_id: p.category, specialty_id: p.specialty, doc_type_id: p.docType, file_kind: p.fileKind });
    const res = await fetch(API.suggest + "?" + qs.toString(), { method:"GET", credentials:"same-origin" });
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
  const bOCR=el("btnOCR"); const area=el("workText"); const meta=el("workMeta");

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

    let data, text="", ct=(res.headers.get("content-type")||"").toLowerCase();
    if (ct.includes("application/json")) { data=await res.json(); text=(data.ocr_text||data.text||"").toString(); }
    else { const raw=await res.text(); try{ data=JSON.parse(raw); text=(data.ocr_text||data.text||""); }catch(_){ text=raw||""; } }

    if (!text.trim()) throw new Error("empty_ocr");
    area.removeAttribute("disabled"); setv(area,text);
    if (meta) meta.textContent = (data && (data.source||data.engine)) ? `OCR: ${data.source||data.engine}` : "";

    const labs = parseLabs(text);
    renderLabTable(labs);
  }catch(e){
    showError("OCR неуспешен или празен резултат.");
  }finally{
    if (bOCR) dis(bOCR,false);
    setBusy(false);
    updateUI();
  }
}

async function doAnalyze(){
  clearError();
  const area=el("workText"); const meta=el("workMeta");
  const p=picks();
  const text = area ? (area.value || "") : "";
  if (!text.trim()) { showError("Липсва OCR текст за анализ."); updateUI(); return; }

  setBusy(true); const bAna=el("btnAnalyze"); if (bAna) dis(bAna,true);
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
    setv(area, summary);
    if (meta){
      const evd = (data && data.data && data.data.event_date) || "";
      const det = (data && data.data && data.data.detected_specialty) || "";
      meta.textContent = [evd, det].filter(Boolean).join(" • ");
    }

    const labs = parseLabs(summary);
    renderLabTable(labs);
  }catch(e){
    showError("Анализът е неуспешен или сървърът не отговаря.");
  }finally{
    if (bAna) dis(bAna,false);
    setBusy(false);
    updateUI();
  }
}

async function doConfirm(){
  clearError();
  const p=picks();
  const area=el("workText");
  const text = area ? (area.value||"") : "";
  if (!text.trim()){ showError("Няма данни за запис."); return; }
  setBusy(true);
  try{
    const res = await fetch(API.confirm, {
      method:"POST",
      headers:{ "Content-Type":"application/json", "X-CSRFToken": getCSRF() },
      credentials:"same-origin",
      body: JSON.stringify({
        category_id: p.category, specialty_id: p.specialty, doc_type_id: p.docType,
        file_kind: p.fileKind, event_id: p.eventId || null, text
      })
    });
    if (!res.ok) throw new Error("confirm_failed");

  }catch(e){
    showError("Записът е неуспешен.");
  }finally{
    setBusy(false);
  }
}

function bindUI(){
  const form=el("uploadForm");
  if (form){
    form.addEventListener("submit", (e)=>{ e.preventDefault(); return false; }); // без reload
  }
  const cat=el("sel_category"), spc=el("sel_specialty"), doc=el("sel_doc_type"), kind=el("file_kind"), file=el("file_input"), choose=el("chooseFileBtn");
  const bOCR=el("btnOCR"), bAna=el("btnAnalyze"), bCfm=el("btnConfirm");

  if (cat)  cat.addEventListener("change", ()=>{ updateUI(); suggestIfReady(); clearError(); });
  if (spc)  spc.addEventListener("change", ()=>{ updateUI(); suggestIfReady(); clearError(); });
  if (doc)  doc.addEventListener("change", ()=>{ updateUI(); suggestIfReady(); clearError(); });
  if (kind) kind.addEventListener("change", ()=>{ updateUI(); suggestIfReady(); clearError(); });

  if (file) file.addEventListener("change", ()=>{
    _choosingFile = false;
    clearError();
    const f = picks().file;
    if (f) renderPreview(f);
    updateUI();
    const btn = el("chooseFileBtn"); if (btn) btn.blur();
  });

  if (choose){
    choose.addEventListener("click", (e)=>{
      e.preventDefault();
      if (_choosingFile) return;
      _choosingFile = true;
      const f=el("file_input"); if (f) f.click();
    });
  }

  if (bOCR) bOCR.addEventListener("click", (e)=>{ e.preventDefault(); doOCR(); });
  if (bAna) bAna.addEventListener("click", (e)=>{ e.preventDefault(); doAnalyze(); });
  if (bCfm) bCfm.addEventListener("click", (e)=>{ e.preventDefault(); doConfirm(); });

  updateUI();
  suggestIfReady();
}

document.addEventListener("DOMContentLoaded", bindUI);
