(function(){
  var steps=[
    {k:"go_personalcard", sel:"body", title:"Личен картон", text:"Първо попълни личните данни, за да знаем на кого са документите."},
    {k:"pc_form", sel:"#personalcard-form", title:"Форма", text:"Попълни полетата и Запази."},
    {k:"go_upload", sel:"#nav-upload", title:"Качване", text:"Отиди към качване на документ."},
    {k:"upload_doc_kind",sel:"#doc_kind_select",title:"Вид документ",text:"Избери вид документ,Медицинска специалност и Медицинска категория. Това е задължително."},
    {k:"upload_file_type",sel:"#file_type_select",title:"Тип файл",text:"Избери тип файл: изображение или PDF."},
    {k:"upload_pick_file",sel:"#file_input",title:"Файл",text:"Прикачи файла, който искаш да анализираш.Можеш да качваш няколко изображения на веднъж, но помни че трябва да са само от един документ!"},
    {k:"upload_analyze",sel:"#analyze_save_btn",title:"Анализ и запис",text:"Натисни „Анализирай и запази“, прегледай текста,поправи го ако се налага и потвърди."},
    {k:"share_entry",sel:"#nav-share",title:"Споделяне",text:"Отиди в споделяне, за да генерираш линк или QR."},
    {k:"share_links",sel:"#create_links_btn",title:"Линкове за сваляне",text:"Създай линкове за изтегляне на PDF/CSV."},
    {k:"share_qr",sel:"#qr_btn",title:"QR код",text:"Генерирай QR за бърз достъп."},
    {k:"export_pdf",sel:"#export_pdf_btn",title:"PDF експорт",text:"Експортирай като PDF."},
    {k:"export_csv",sel:"#export_csv_btn",title:"CSV експорт",text:"Експортирай като CSV."},
    {k:"done",sel:"body",title:"Готово",text:"Това беше краткият урок за използване на сайта. Можеш да го отвориш отново от менюто Помощ."}
  ];
  var key="medj_tour_v1_done";
  function qs(s){return document.querySelector(s)}
  function rectOf(el){var r=el.getBoundingClientRect();return{t:r.top+window.scrollY,l:r.left+window.scrollX,w:r.width,h:r.height}}
  function ensureMask(){var m=qs(".onb-mask");if(!m){m=document.createElement("div");m.className="onb-mask";document.body.appendChild(m)}return m}
  function ensureSpot(){var s=qs(".onb-spot");if(!s){s=document.createElement("div");s.className="onb-spot";document.body.appendChild(s)}return s}
  function ensurePanel(){var p=qs(".onb-panel");if(!p){p=document.createElement("div");p.className="onb-panel";p.innerHTML='<div class="onb-title"></div><div class="onb-text"></div><div class="onb-actions"><button class="onb-btn ghost" data-act="skip">Пропусни</button><button class="onb-btn ghost" data-act="prev">Назад</button><button class="onb-btn primary" data-act="next">Напред</button></div>';document.body.appendChild(p)}return p}
  function placeAround(p,elr){var x=elr.l+elr.w+16,y=elr.t;var vw=window.innerWidth,vh=window.innerHeight;var pw=p.offsetWidth,ph=p.offsetHeight;if(x+pw>vw-16)x=elr.l; if(y+ph>vh-16)y=elr.t+elr.h+16; p.style.left=x+"px";p.style.top=y+"px"}
  function showStep(i){
    if(i<0)i=0; if(i>=steps.length){finish();return}
    state.i=i;
    var st=steps[i],el=qs(st.sel);
    if(!el){next();return}
    var m=ensureMask(),s=ensureSpot(),p=ensurePanel();
    var r=rectOf(el);{k:"go_personalcard", sel:"body", title:"Личен картон", text:"Първо попълни личните данни, после ще качим документ."},
    {k:"pc_form", sel:"#personalcard-form", title:"Форма", text:"Попълни полетата и Запази."},
    {k:"go_upload", sel:"#nav-upload", title:"Качване", text:"Отиди към качване на документ."},
    s.style.left=r.l+"px";s.style.top=r.t+"px";s.style.width=r.w+"px";s.style.height=r.h+"px";
    p.querySelector(".onb-title").textContent=st.title;
    p.querySelector(".onb-text").textContent=st.text;
    placeAround(p,r);
    m.classList.add("show");
    window.scrollTo({top:r.t-120,behavior:"smooth"});
  }
  function hide(){var m=qs(".onb-mask");if(m)m.classList.remove("show");}
  function finish(){localStorage.setItem(key,"1");hide();var s=qs(".onb-spot");if(s)s.remove();var p=qs(".onb-panel");if(p)p.remove()}
  function next(){
    var st=steps[state.i]||{};
    if(st.k==="go_upload"){window.location.href="/upload/";return}
    if(st.k==="share_entry"){window.location.href="/share/";return}
    if(st.k==="export_pdf"){return showStep(state.i+1)}
    showStep(state.i+1)
  }
  function prev(){showStep(state.i-1)}
  function init(){
    if(localStorage.getItem(key)==="1")return;
    var p=ensurePanel();
    p.addEventListener("click",function(e){
      var a=e.target.getAttribute("data-act");
      if(a==="skip"){finish()}
      if(a==="next"){next()}
      if(a==="prev"){prev()}
    });
    showStep(0);
  }
  var state={i:0};
  if(document.readyState==="loading"){document.addEventListener("DOMContentLoaded",init)}else{init()}
})();
