(function(){
  var LS_KEY="medj_onboarding_state";
  var S={step:1,done:false};
  function load(){try{var x=localStorage.getItem(LS_KEY);if(!x)return S;var o=JSON.parse(x);return typeof o.step==="number"?o:S}catch(e){return S}}
  function save(o){try{localStorage.setItem(LS_KEY,JSON.stringify(o))}catch(e){}}
  function q(s){return document.querySelector(s)}
  function on(id,ev,fn){var el=document.getElementById(id);if(el)el.addEventListener(ev,fn)}
  function show(id){var m=q('#'+id);if(!m)return;document.body.classList.add('overflow-hidden');m.classList.remove('hidden')}
  function hide(id){var m=q('#'+id);if(!m)return;m.classList.add('hidden');document.body.classList.remove('overflow-hidden')}
  function next(){var o=load();o.step+=1;if(o.step>4){o.done=true}save(o);route()}
  function prev(){var o=load();o.step=Math.max(1,o.step-1);save(o);route()}
  function route(){
  var o=load(); if(o.done) return;
  var path = location.pathname;

  if (o.step===1 && !/personalcard\/?$/.test(path)) { location.href="/personalcard/"; return; }
  if (o.step===1 &&  /personalcard\/?$/.test(path)) { show('ob_personalcard'); return; }

  if (o.step===2 && !/app\/upload\/?$/.test(path))   { location.href="/app/upload/"; return; }
  if (o.step===2 &&  /app\/upload\/?$/.test(path))   { show('ob_upload'); return; }

  if (o.step===3 && !/app\/upload\/history\/?$/.test(path)) { location.href="/app/upload/history/"; return; }
  if (o.step===3 &&  /app\/upload\/history\/?$/.test(path)) { show('ob_history'); return; }

  if (o.step===4) { show('ob_welcome'); }
}
  function markRequired(){
    document.querySelectorAll('[data-required="true"]').forEach(function(l){
      if(l.querySelector('.reqmark'))return;
      var s=document.createElement('span');s.className='reqmark text-[var(--color-danger)] ml-1';s.textContent='*';l.appendChild(s);
    })
  }
  function bindUploadLeaveGuard(){
    if(!/upload\/?$/.test(location.pathname))return;
    var dirty=false;
    ['doc_type','specialty','med_category','file_input'].forEach(function(id){
      var el=document.getElementById(id);
      if(!el)return;
      el.addEventListener('change',function(){dirty=true})
    });
    window.addEventListener('beforeunload',function(e){
      var o=load();if(o.step!==2)return;
      if(dirty){e.preventDefault();e.returnValue='';return ''}
    });
  }
  function init(){
    if(!localStorage.getItem(LS_KEY)) save({step:1,done:false});
    markRequired();
    bindUploadLeaveGuard();
    on('ob1_ok','click',function(){next()});
    on('ob2_ok','click',function(){next()});
    on('ob3_ok','click',function(){next()});
    on('ob4_ok','click',function(){var o=load();o.done=true;save(o);hide('ob_welcome')});
    on('ob1_close','click',function(){hide('ob_personalcard')});
    on('ob2_close','click',function(){hide('ob_upload')});
    on('ob3_close','click',function(){hide('ob_history')});
    on('ob4_close','click',function(){hide('ob_welcome')});
    route();
  }
  if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',init)}else{init()}
})();
