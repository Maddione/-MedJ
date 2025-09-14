const API={ocr:"/api/upload/ocr/",analyze:"/api/upload/analyze/",confirm:"/api/upload/confirm/",suggest:"/api/events/suggest/"};
function el(id){return document.getElementById(id);}
function show(x){if(x)x.classList.remove("hidden");}
function hide(x){if(x)x.classList.add("hidden");}
function seth(x,h){if(x)x.innerHTML=h||"";}
function setv(x,v){if(x)x.value=v||"";}
function dis(x,f){if(!x)return;x.disabled=!!f;}
function getCSRF(){const t=document.querySelector('input[name="csrfmiddlewaretoken"]');if(t&&t.value)return t.value;const m=document.cookie.match(/(?:^|;)\s*csrftoken=([^;]+)/);return m?decodeURIComponent(m[1]):"";}
let CURRENT_FILE=null, CURRENT_FILE_KIND="", CURRENT_FILE_URL=null;

function picks(){
  return{
    category:(el("sel_category")||{}).value||"",
    specialty:(el("sel_specialty")||{}).value||"",
    docType:(el("sel_doc_type")||{}).value||"",
    fileKind:CURRENT_FILE_KIND||"",
    file:CURRENT_FILE,
    eventId:(el("existingEventSelect")||{}).value||""
  };
}

function stage(){
  const p=picks();
  if(!p.file)return"choose_file";
  const text=(el("workText")||{}).value||"";
  if(!text.trim())return"ocr";
  return"analyze";
}

function updateButtons(){
  const s=stage();
  const bOCR=el("btnOCR"),bAna=el("btnAnalyze"),bCfm=el("btnConfirm");
  if(bOCR)(s==="ocr")?show(bOCR):hide(bOCR);
  if(bAna)(s!=="ocr")?show(bAna):hide(bAna);
  if(bCfm)(s!=="ocr")?show(bCfm):hide(bCfm);
}

function setBusy(on){
  const o=el("loadingOverlay");
  if(on)show(o);else hide(o);
}

function showError(msg){
  const box=el("errorBox");
  if(box){box.textContent=msg||"Грешка.";show(box);}
}

function clearError(){
  const box=el("errorBox");
  if(box){box.textContent="";hide(box);}
}

function renderPreview(){
  const wrap=el("previewBlock"),img=el("previewImg"),pdf=el("previewPDF"),emb=el("previewEmbed"),meta=el("fileMeta"),badge=el("fileNameBadge");
  if(!CURRENT_FILE){hide(wrap);if(meta)seth(meta,"");if(badge)badge.classList.add("hidden");return;}
  if(CURRENT_FILE_URL){URL.revokeObjectURL(CURRENT_FILE_URL);CURRENT_FILE_URL=null;}
  CURRENT_FILE_URL=URL.createObjectURL(CURRENT_FILE);
  const name=CURRENT_FILE.name||"file";
  const type=(CURRENT_FILE.type||"").toLowerCase();
  const sizeKB=Math.round((CURRENT_FILE.size||0)/1024);
  if(type.startsWith("image/")){img.src=CURRENT_FILE_URL;show(img);hide(pdf);}
  else if(type==="application/pdf"||name.toLowerCase().endsWith(".pdf")){emb.src=CURRENT_FILE_URL;hide(img);show(pdf);}
  else{hide(img);hide(pdf);}
  show(wrap);
  if(meta)meta.textContent=`${name} • ${sizeKB} KB • ${type||"unknown"}`;
  if(badge){badge.textContent=name;badge.classList.remove("hidden");}
}

function handleFileInputChange(){
  const fi=el("file_input");
  const kind=el("file_kind");
  CURRENT_FILE=fi&&fi.files?fi.files[0]:null;
  CURRENT_FILE_KIND=(kind&&kind.value)||"";
  renderPreview();
  updateButtons();
}

async function doOCR(){
  clearError();
  const p=picks();
  if(!p.file){showError("Моля изберете файл.");return;}
  setBusy(true);
  const fd=new FormData();
  fd.append("file",p.file);
  fd.append("file_kind",p.fileKind||"");
  try{
    const res=await fetch(API.ocr,{method:"POST",headers:{"X-CSRFToken":getCSRF()},credentials:"same-origin",body:fd});
    const ct=(res.headers.get("content-type")||"").toLowerCase();
    const data=ct.includes("application/json")?await res.json():{error:"invalid_response"};
    if(data.error){showError("OCR неуспешен: "+(data.detail||data.error));return;}
    const text=(data.ocr_text||"").toString();
    if(!text.trim()){showError("Празен OCR резултат.");return;}
    const area=el("workText");area.removeAttribute("disabled");setv(area,text);
    const meta=el("workMeta");if(meta)meta.textContent=(data.engine?"OCR: "+data.engine:"");
    updateButtons();
  }catch(e){
    showError("OCR грешка при заявката.");
  }finally{
    setBusy(false);
  }
}

async function doAnalyze(){
  clearError();
  const area=el("workText");const text=(area?area.value:"")||"";
  if(!text.trim()){showError("Липсва текст за анализ.");return;}
  setBusy(true);
  try{
    const res=await fetch(API.analyze,{method:"POST",headers:{"Content-Type":"application/json","X-CSRFToken":getCSRF()},credentials:"same-origin",body:JSON.stringify({text})});
    const data=await res.json();
    const summary=(data.summary||"").toString();
    if(!summary.trim()){showError("Празен резултат от анализ.");return;}
    setv(area,summary);
    updateButtons();
  }catch(e){
    showError("Грешка при анализ.");
  }finally{
    setBusy(false);
  }
}

async function doConfirm(){
  clearError();
  const area=el("workText");const text=(area?area.value:"")||"";
  if(!text.trim()){showError("Няма данни за запис.");return;}
  setBusy(true);
  try{
    const res=await fetch(API.confirm,{method:"POST",headers:{"Content-Type":"application/json","X-CSRFToken":getCSRF()},credentials:"same-origin",body:JSON.stringify({text})});
    if(!res.ok)throw new Error("confirm_failed");
  }catch(e){
    showError("Грешка при запис.");
  }finally{
    setBusy(false);
  }
}

function bindUI(){
  const form=el("uploadForm");
  if(form){
    form.setAttribute("action","#");
    form.setAttribute("method","post");
    form.setAttribute("novalidate","novalidate");
    form.addEventListener("submit",e=>{e.preventDefault();return false;});
  }
  const choose=el("chooseFileBtn"),fi=el("file_input");
  if(choose)choose.addEventListener("click",e=>{e.preventDefault();if(fi)fi.click();});
  if(fi)fi.addEventListener("change",handleFileInputChange);
  const kind=el("file_kind");if(kind)kind.addEventListener("change",()=>{CURRENT_FILE_KIND=kind.value||"";});
  const bOCR=el("btnOCR"),bAna=el("btnAnalyze"),bCfm=el("btnConfirm");
  if(bOCR)bOCR.addEventListener("click",e=>{e.preventDefault();doOCR();});
  if(bAna)bAna.addEventListener("click",e=>{e.preventDefault();doAnalyze();});
  if(bCfm)bCfm.addEventListener("click",e=>{e.preventDefault();doConfirm();});
  updateButtons();
}

document.addEventListener("DOMContentLoaded",bindUI);
