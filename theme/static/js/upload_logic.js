(function(){
  var form=document.getElementById("upload-form");
  var selCat=document.getElementById("sel_category");
  var selSpec=document.getElementById("sel_specialty");
  var selDoc=document.getElementById("sel_doc_type")||document.getElementById("sel_doc_kind");
  var selFiletype=document.getElementById("sel_filetype")||document.getElementById("file_kind");
  var fileInput=document.getElementById("file_input");
  var btnUpload=document.getElementById("btn_upload");
  var preview=document.getElementById("preview_section");
  var prevLeft=document.getElementById("preview_left");
  var prevRight=document.getElementById("preview_right");
  var warn=document.getElementById("req_warn");
  var warnList=document.getElementById("req_list");
  var btnConfirm=document.getElementById("btn_confirm");
  var csrfEl=document.querySelector('input[name=csrfmiddlewaretoken]');
  var csrf=csrfEl?csrfEl.value:"";
  var ocrUrl=(form&&form.getAttribute("data-upload-ocr-url"))||"/upload/ocr/";
  var confirmUrl="/upload/confirm/";
  function hasValueSelect(el){return !!el&&el.selectedIndex>0}
  function enabled(el){return el&&!el.disabled}
  function setDisabled(el,d){if(!el)return;el.disabled=!!d;el.setAttribute("aria-disabled",d?"true":"false");el.classList.toggle("disabled-ui",!!d)}
  function showRequirements(){
    if(!warn||!warnList)return;
    var m=[];
    if(selCat&&!hasValueSelect(selCat))m.push("Категория");
    if(selSpec&&!hasValueSelect(selSpec))m.push("Специалност");
    if(selDoc&&!hasValueSelect(selDoc))m.push("Вид документ");
    if(!fileInput||fileInput.disabled||!fileInput.files||!fileInput.files.length)m.push("Документ за качване");
    if(selFiletype&&!hasValueSelect(selFiletype))m.push("Тип файл");
    warnList.innerHTML=m.map(function(x){return "<li>• "+x+"</li>"}).join("");
    if(m.length){warn.classList.remove("hidden")}else{warn.classList.add("hidden")}
  }
  function sync(){
    var step1=!selCat||hasValueSelect(selCat);
    setDisabled(selSpec,!step1);
    if(!step1&&selSpec)selSpec.selectedIndex=0;
    var step2=step1&&(!selSpec||hasValueSelect(selSpec));
    setDisabled(selDoc,!step2);
    if(!step2&&selDoc)selDoc.selectedIndex=0;
    var step3=step2&&(!selDoc||hasValueSelect(selDoc));
    setDisabled(fileInput,!step3);
    if(!step3&&fileInput){fileInput.value=""}
    var hasFile=step3&&fileInput&&fileInput.files&&fileInput.files.length>0;
    setDisabled(selFiletype,!hasFile);
    if(!hasFile&&selFiletype)selFiletype.selectedIndex=0;
    var ok=step3&&hasFile&&(!selFiletype||hasValueSelect(selFiletype));
    setDisabled(btnUpload,!ok);
    showRequirements();
  }
  function renderLeft(files){
    if(!prevLeft||!files)return;
    prevLeft.innerHTML="";
    var list=document.createElement("div");
    for(var i=0;i<files.length;i++){
      var f=files[i];
      var row=document.createElement("div");
      row.className="flex items-center gap-3 border-b border-black/10 py-2";
      if(f.type&&f.type.indexOf("image/")===0){
        var img=document.createElement("img");
        img.className="h-20 w-auto rounded";
        img.src=URL.createObjectURL(f);
        row.appendChild(img);
      }
      var name=document.createElement("div");
      name.className="text-[#0A1E4A] text-base";
      name.textContent=f.name;
      row.appendChild(name);
      list.appendChild(row);
    }
    prevLeft.appendChild(list);
  }
  function buildFD(){
    var fd=new FormData();
    var docVal=selDoc?selDoc.value:"";
    var specVal=selSpec?selSpec.value:"";
    var catVal=selCat?selCat.value:"";
    if(docVal)fd.append("doc_type",docVal);
    if(specVal)fd.append("specialty",specVal);
    if(catVal)fd.append("med_category",catVal);
    if(fileInput&&fileInput.files){for(var i=0;i<fileInput.files.length;i++){fd.append("files",fileInput.files[i])}}
    return fd;
  }
  function postOCR(){
    var fd=buildFD();
    return fetch(ocrUrl,{method:"POST",headers:{"X-Requested-With":"XMLHttpRequest","X-CSRFToken":csrf},body:fd}).then(function(r){if(!r.ok)throw new Error("http "+r.status);return r.json()})
  }
  function onUpload(e){
    e.preventDefault();
    showRequirements();
    if(enabled(btnUpload)&&!btnUpload.disabled){
      renderLeft(fileInput.files||[]);
      postOCR().then(function(j){
        if(prevRight){prevRight.innerHTML=(j&&j.ocr_text)||""}
        if(preview){preview.classList.remove("hidden")}
        if(preview){window.scrollTo({top:preview.offsetTop-30,behavior:"smooth"})}
        if(warn)warn.classList.add("hidden");
      }).catch(function(){
        if(prevRight){prevRight.innerHTML="Генерирането е недостъпно в момента. Опитайте отново."}
        if(preview){preview.classList.remove("hidden")}
        if(warn){warnList.innerHTML="<li>• Грешка при връзката.</li>";warn.classList.remove("hidden")}
      });
    }
  }
  function onConfirm(e){
    if(!btnConfirm)return;
    e.preventDefault();
    var fd=new FormData();
    fetch(confirmUrl,{method:"POST",headers:{"X-Requested-With":"XMLHttpRequest","X-CSRFToken":csrf},body:fd}).then(function(r){return r.json()}).then(function(d){if(d&&d.ok){window.location.href="/upload/history/"}})
  }
  ["change","input"].forEach(function(t){
    [selCat,selSpec,selDoc,selFiletype,fileInput].forEach(function(el){if(el)el.addEventListener(t,sync)})
  });
  if(btnUpload)btnUpload.addEventListener("click",onUpload);
  if(btnConfirm)btnConfirm.addEventListener("click",onConfirm);
  document.addEventListener("click",function(e){
    var blocked=false,el=e.target;
    if(el.closest&&el.closest(".disabled-ui"))blocked=true;
    if((el.tagName==="SELECT"||el.tagName==="BUTTON"||el.tagName==="LABEL")&&(el.disabled||el.getAttribute("aria-disabled")==="true"))blocked=true;
    if(blocked){e.preventDefault();e.stopPropagation();showRequirements()}
  },true);
  sync();
})();
