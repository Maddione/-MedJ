(function(){
  var selDoc=document.getElementById("sel_doc_kind");
  var selSpec=document.getElementById("sel_specialty");
  var selFiletype=document.getElementById("sel_filetype");
  var fileInput=document.getElementById("file_input");
  var btnUpload=document.getElementById("btn_upload");
  var preview=document.getElementById("preview_section");
  var prevLeft=document.getElementById("preview_left");
  var prevRight=document.getElementById("preview_right");
  var btnConfirm=document.getElementById("btn_confirm");
  var token=null;

  function ok(){
    return selDoc.value && selSpec.value && selFiletype.value && fileInput.files.length>0;
  }
  function sync(){
    btnUpload.disabled=!ok();
    btnUpload.className=ok()?"w-full rounded-xl bg-primary text-white py-3 text-lg font-semibold":"w-full rounded-xl bg-primary/40 text-white py-3 text-lg font-semibold";
  }
  ["change","input"].forEach(function(e){
    [selDoc,selSpec,selFiletype,fileInput].forEach(function(el){ if(el) el.addEventListener(e,sync); });
  });
  sync();

  function renderLeft(files){
    prevLeft.innerHTML="";
    var list=document.createElement("div");
    for(var i=0;i<files.length;i++){
      var f=files[i];
      var row=document.createElement("div");
      row.className="flex items-center gap-3 border-b border-primary/40 py-2";
      if(f.type.startsWith("image/")){
        var img=document.createElement("img");
        img.className="h-20 w-auto rounded";
        img.src=URL.createObjectURL(f);
        row.appendChild(img);
      }
      var name=document.createElement("div");
      name.className="text-primaryDark text-base";
      name.textContent=f.name;
      row.appendChild(name);
      list.appendChild(row);
    }
    prevLeft.appendChild(list);
  }

  btnUpload.addEventListener("click",function(ev){
    ev.preventDefault();
    if(!ok()) return;
    renderLeft(fileInput.files);
    var fd=new FormData();
    fd.append("doc_kind",selDoc.value);
    fd.append("specialty",selSpec.value);
    fd.append("file_type",selFiletype.value);
    for(var i=0;i<fileInput.files.length;i++){ fd.append("files",fileInput.files[i]); }
    fetch("/upload/preview/",{method:"POST",body:fd,headers:{"X-Requested-With":"XMLHttpRequest"}}).then(function(r){return r.json();}).then(function(data){
      token=data.token||null;
      prevRight.innerHTML=data.html||data.summary||"";
      preview.classList.remove("hidden");
      window.scrollTo({top:preview.offsetTop-30,behavior:"smooth"});
    }).catch(function(){
      prevRight.innerHTML="Генерирането е недостъпно в момента. Опитайте отново.";
      preview.classList.remove("hidden");
    });
  });

  if(btnConfirm){
    btnConfirm.addEventListener("click",function(ev){
      ev.preventDefault();
      if(!token) return;
      var fd=new FormData();
      fd.append("token",token);
      fetch("/upload/confirm/",{method:"POST",body:fd,headers:{"X-Requested-With":"XMLHttpRequest"}}).then(function(r){return r.json();}).then(function(data){
        if(data.ok){ window.location.href="/upload/history/"; }
      });
    });
  }
})();
