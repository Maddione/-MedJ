<script>
const API = {
  ocr: "/api/upload/ocr/",
  analyze: "/api/upload/analyze/",
  confirm: "/api/upload/confirm/",
  suggest: "/api/events/suggest/",
  doctorSuggest: "/api/doctors/suggest/"
};

function el(){const ids=Array.from(arguments);for(let i=0;i<ids.length;i++){const x=document.getElementById(ids[i]);if(x)return x}return null}
function show(x){if(x)x.classList.remove("hidden")}
function hide(x){if(x)x.classList.add("hidden")}
function setv(x,v){if(x)x.value=v||""}
function seth(x,h){if(x)x.innerHTML=h||""}
function dis(x,f){if(x)x.disabled=!!f}

function getCSRF(){
  const inps=document.querySelectorAll('input[name="csrfmiddlewaretoken"]');
  if(inps.length)return inps[0].value;
  const m=document.cookie.match(/csrftoken=([^;]+)/);
  return m?m[1]:"";
}

async function toB64(f){
  if(!f)return"";
  return new Promise((resolve,reject)=>{
    const r=new FileReader();
    r.onload=()=>resolve(String(r.result).split(",")[1]||"");
    r.onerror=reject;
    r.readAsDataURL(f);
  });
}

function picks(){
  return {
    category:(el("categorySelect","sel_category")||{}).value||"",
    specialty:(el("specialtySelect","sel_specialty")||{}).value||"",
    docType:(el("docTypeSelect","sel_doc_type")||{}).value||"",
    file:(el("fileInput","file_input")||{}).files?el("fileInput","file_input").files[0]:null,
    fileKind:(el("fileKindSelect","file_kind")||{}).value||"",
    eventId:(el("existingEventSelect")||{}).value||""
  };
}

function updateUI(){
  const p=picks();
  dis(el("specialtySelect","sel_specialty"),!p.category);
  dis(el("docTypeSelect","sel_doc_type"),!p.specialty);

  const ocrText=el("ocrText","ocr_text"); const hasOCR=ocrText?!!ocrText.value.trim():false;
  dis(el("btnOCR"),!(p.file&&p.fileKind&&p.category&&p.specialty&&p.docType));
  dis(el("btnAnalyze"),!(p.specialty&&(hasOCR)));
  dis(el("btnConfirm","btn_upload"),!(p.category&&p.specialty&&p.docType&&(p.file||hasOCR)));
}

async function suggestIfReady(){
  const wrap=el("existingEventWrap");
  const select=el("existingEventSelect");
  const p=picks();
  if(!(p.category&&p.specialty&&p.docType)){
    if(wrap)hide(wrap);
    if(select)seth(select,"");
    return;
  }
  try{
    const res=await fetch(API.suggest,{
      method:"POST",
      headers:{"Content-Type":"application/json","X-CSRFToken":getCSRF()},
      credentials:"same-origin",
      body:JSON.stringify({category_id:p.category,specialty_id:p.specialty,doc_type_id:p.docType})
    });
    if(!res.ok)throw new Error("suggest_failed");
    const data=await res.json();
    const items=data.events||[];
    if(!select)return;
    if(!items.length){
      seth(select,'<option value="">—</option>');
      if(wrap)show(wrap);
      return;
    }
    const opts=['<option value="">—</option>'].concat(items.map(x=>`<option value="${x.id}">#${x.id}${x.event_date?" · "+x.event_date:""}</option>`));
    seth(select,opts.join(""));
    if(wrap)show(wrap);
  }catch(e){
    if(select)seth(select,'<option value="">—</option>');
    if(wrap)show(wrap);
  }
}

function injectDoctorSection(){
  if(el("doctorSection"))return;
  const anchor=el("summaryText","summary_text")||el("analysisMeta")||el("ocrText","ocr_text")||document.body;
  const cont=document.createElement("div");
  cont.id="doctorSection";
  cont.className="mt-6 bg-blockbg rounded-2xl p-4 shadow-sm";
  cont.innerHTML=`
    <label class="flex items-center gap-3 text-primaryDark">
      <input id="addDoctorToggle" type="checkbox" class="h-5 w-5 rounded border-gray-300">
      <span>Искам да добавя лекар</span>
    </label>
    <div id="doctorFields" class="mt-4 hidden">
      <div class="grid md:grid-cols-3 gap-3">
        <div class="md:col-span-1">
          <div class="text-primaryDark mb-1">Изберете от записани</div>
          <select id="doctorSelect" class="w-full h-11 rounded-xl px-3 border border-gray-300">
            <option value="">—</option>
          </select>
        </div>
        <div class="md:col-span-1">
          <div class="text-primaryDark mb-1">Внимателно въведете Име и Фамилия</div>
          <input id="doctorInput" type="text" class="w-full h-11 rounded-xl px-3 border border-gray-300" placeholder="Име Фамилия">
        </div>
        <div class="md:col-span-1">
          <div class="text-primaryDark mb-1">Специалност</div>
          <select id="doctorSpecialtySelect" class="w-full h-11 rounded-xl px-3 border border-gray-300"></select>
        </div>
      </div>
      <div id="doctorAiBadge" class="mt-2 hidden text-sm" style="color:#0A4E75">Открито от AI</div>
    </div>
  `;
  anchor.parentNode.insertBefore(cont,anchor.nextSibling);
  const spcSrc=el("specialtySelect","sel_specialty");
  const spcDst=el("doctorSpecialtySelect");
  if(spcSrc&&spcDst){seth(spcDst,spcSrc.innerHTML); spcDst.value=spcSrc.value||""}
  const tgl=el("addDoctorToggle"); const fields=el("doctorFields");
  if(tgl&&fields){tgl.addEventListener("change",()=>{if(tgl.checked)show(fields);else hide(fields)})}
  const inp=el("doctorInput");
  if(inp){let lastQ=""; inp.addEventListener("input",()=>{const q=inp.value.trim(); if(q===lastQ)return; lastQ=q; doctorSuggest(q);})}
}

async function doctorSuggest(q){
  const spc=(el("doctorSpecialtySelect")||{}).value||(el("specialtySelect","sel_specialty")||{}).value||"";
  const sel=el("doctorSelect"); if(!sel)return;
  try{
    const url=`${API.doctorSuggest}?q=${encodeURIComponent(q||"")}&specialty_id=${encodeURIComponent(spc||"")}`;
    const res=await fetch(url,{credentials:"same-origin"});
    if(!res.ok)throw new Error("bad");
    const data=await res.json();
    const items=data.results||[];
    const opts=['<option value="">—</option>'].concat(items.map(x=>{
      const value=x.full_name||""; const text=x.display_name||x.full_name||""; const sid=(x.id!=null?String(x.id):"");
      return `<option value="${value}" data-id="${sid}">${text}</option>`;
    }));
    seth(sel,opts.join(""));
  }catch(e){
    seth(sel,'<option value="">—</option>');
  }
}

async function doOCR(){
  const p=picks();
  const ocrBtn=el("btnOCR");
  const ocrOut=el("ocrText","ocr_text");
  if(!(p.file&&p.fileKind&&p.category&&p.specialty&&p.docType))return;
  const fd=new FormData();
  fd.append("file",p.file);
  fd.append("file_kind",p.fileKind);
  fd.append("category_id",p.category);
  fd.append("specialty_id",p.specialty);
  fd.append("doc_type_id",p.docType);
  if(ocrBtn)dis(ocrBtn,true);
  try{
    const res=await fetch(API.ocr,{method:"POST",credentials:"same-origin",body:fd});
    if(!res.ok)throw new Error("ocr_failed");
    const data=await res.json();
    if(ocrOut)setv(ocrOut,data.ocr_text||"");
    const info=el("ocrSourceInfo"); if(info)info.textContent=data.source?`OCR: ${data.source}`:"";
    return data.ocr_text||"";
  }catch(e){
    if(ocrOut)setv(ocrOut,"");
    return"";
  }finally{
    if(ocrBtn)dis(ocrBtn,false);
    updateUI();
  }
}

async function doAnalyze(){
  const p=picks();
  const analyzeBtn=el("btnAnalyze");
  const ocrOut=el("ocrText","ocr_text");
  const summaryOut=el("summaryText","summary_text");
  const txt=ocrOut?(ocrOut.value||""):"";
  if(!(txt&&p.specialty))return;
  if(analyzeBtn)dis(analyzeBtn,true);
  try{
    const res=await fetch(API.analyze,{
      method:"POST",
      headers:{"Content-Type":"application/json","X-CSRFToken":getCSRF()},
      credentials:"same-origin",
      body:JSON.stringify({text:txt,specialty_id:p.specialty})
    });
    if(!res.ok)throw new Error("analyze_failed");
    const data=await res.json();
    const s=(data&&data.data&&data.data.summary)||data.summary||"";
    if(summaryOut)setv(summaryOut,s||"");
    const meta=el("analysisMeta");
    if(meta){
      const evd=(data&&data.data&&data.data.event_date)||"";
      const det=(data&&data.data&&data.data.detected_specialty)||"";
      meta.textContent=[evd,det].filter(Boolean).join(" • ");
    }
    const payload=el("analysisPayload"); if(payload)payload.setAttribute("data-json",JSON.stringify(data));
    injectDoctorSection();
    const found=(data&&data.data&&data.data.doctors)||[];
    if(found&&found.length){
      const tgl=el("addDoctorToggle"); const fields=el("doctorFields");
      if(tgl&&fields){tgl.checked=true; show(fields)}
      const inp=el("doctorInput"); if(inp)inp.value=String(found[0]||"");
      const badge=el("doctorAiBadge"); if(badge)show(badge);
      doctorSuggest(found[0]||"");
    }else{
      doctorSuggest("");
    }
    return data;
  }catch(e){
    if(summaryOut)setv(summaryOut,"");
    const payload=el("analysisPayload"); if(payload)payload.setAttribute("data-json","{}");
    return null;
  }finally{
    if(analyzeBtn)dis(analyzeBtn,false);
    updateUI();
  }
}

function collectDoctorBlock(){
  const tgl=el("addDoctorToggle"); const use=tgl?tgl.checked:false;
  const sel=el("doctorSelect"); const inp=el("doctorInput"); const spc=el("doctorSpecialtySelect");
  const nameSel=sel&&sel.value?sel.value.trim():"";
  const nameInp=inp&&inp.value?inp.value.trim():"";
  const name=nameSel||nameInp;
  const specialty_id=spc&&spc.value?spc.value:"";
  const practitioner_id=sel&&sel.selectedOptions&&sel.selectedOptions[0]?(sel.selectedOptions[0].getAttribute("data-id")||""):"";
  if(!use||!name)return null;
  if(practitioner_id)return{practitioner_id:parseInt(practitioner_id,10),role:"author",is_primary:true};
  return{full_name:name||"",specialty_id:specialty_id||"",role:"author",is_primary:true};
}

async function doConfirm(){
  const p=picks();
  const btn=el("btnConfirm","btn_upload");
  const ocrOut=el("ocrText","ocr_text");
  const summaryOut=el("summaryText","summary_text");
  if(!(p.file&&p.category&&p.specialty&&p.docType))return;
  let finalText=ocrOut?(ocrOut.value||""):"";
  if(!finalText){const t=await doOCR(); finalText=t||""}
  const finalSummary=summaryOut?(summaryOut.value||""):"";
  const fileB64=await toB64(p.file);
  const analysisPayloadEl=el("analysisPayload");
  let analysis={}; if(analysisPayloadEl){try{analysis=JSON.parse(analysisPayloadEl.getAttribute("data-json")||"{}")}catch(_){}} 
  const doctor=collectDoctorBlock();
  const payload={
    category_id:p.category,
    specialty_id:p.specialty,
    doc_type_id:p.docType,
    event_id:p.eventId||null,
    final_text:finalText,
    final_summary:finalSummary,
    analysis:analysis,
    file_b64:fileB64,
    file_name:p.file.name||"document.bin",
    file_mime:p.file.type||"application/octet-stream",
    file_kind:p.fileKind||"other",
    doctor:doctor
  };
  if(btn)dis(btn,true);
  try{
    const res=await fetch(API.confirm,{
      method:"POST",
      headers:{"Content-Type":"application/json","X-CSRFToken":getCSRF()},
      credentials:"same-origin",
      body:JSON.stringify(payload)
    });
    if(!res.ok)throw new Error("confirm_failed");
    await res.json();
    window.location.href="/documents/";
  }catch(e){
  }finally{
    if(btn)dis(btn,false);
  }
}

function bindUI(){
  const cat=el("categorySelect","sel_category");
  const spc=el("specialtySelect","sel_specialty");
  const doc=el("docTypeSelect","sel_doc_type");
  const file=el("fileInput","file_input");
  const kind=el("fileKindSelect","file_kind");

  if(cat)cat.addEventListener("change",()=>{updateUI();suggestIfReady()});
  if(spc)spc.addEventListener("change",()=>{updateUI();suggestIfReady(); const dst=el("doctorSpecialtySelect"); if(dst)dst.value=spc.value||""; doctorSuggest((el("doctorInput")||{}).value||"")});
  if(doc)doc.addEventListener("change",()=>{updateUI();suggestIfReady()});
  if(file)file.addEventListener("change",updateUI);
  if(kind)kind.addEventListener("change",updateUI);

  const bOCR=el("btnOCR"); const bAna=el("btnAnalyze"); const bCfm=el("btnConfirm","btn_upload");
  if(bOCR)bOCR.addEventListener("click",e=>{e.preventDefault();doOCR()});
  if(bAna)bAna.addEventListener("click",e=>{e.preventDefault();doAnalyze()});
  if(bCfm)bCfm.addEventListener("click",e=>{e.preventDefault();doConfirm()});

  injectDoctorSection();
  updateUI();
  suggestIfReady();
}

document.addEventListener("DOMContentLoaded",bindUI);
</script>
