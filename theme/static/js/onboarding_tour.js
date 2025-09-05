(function(){
  if (localStorage.getItem("medj_tour_done")==="1") return;

  const steps = [
    { el: '[data-tour="dashboard-cards"]', msg: 'Тук виждаш бърз преглед на активностите и документите.' },
    { el: '[data-tour="upload"]', msg: 'Качи документ в няколко стъпки: вид → специалност → категория → файл.' },
    { el: '[data-tour="share"]', msg: 'Сподели временно чрез линк или QR код с филтри по дати и вид.' },
  ];

  const overlay = document.createElement('div'); overlay.className = 'tour-overlay'; document.body.appendChild(overlay);
  const tip = document.createElement('div'); tip.className = 'tour-step'; document.body.appendChild(tip);

  let i = 0;
  function place(){
    const target = document.querySelector(steps[i].el);
    if(!target){ next(); return; }
    tip.innerHTML = `
      <div style="color:#0A4E75;font-weight:700;margin-bottom:8px">Онбординг</div>
      <div style="color:#0A4E75">${steps[i].msg}</div>
      <div class="tour-actions">
        <button class="tour-btn secondary" data-skip>Пропусни</button>
        <button class="tour-btn" data-next>${i===steps.length-1?'Готово':'Напред'}</button>
      </div>`;
    const rect = target.getBoundingClientRect();
    tip.style.top = (window.scrollY + rect.top + rect.height + 12) + 'px';
    tip.style.left = Math.min(window.scrollX + rect.left, window.scrollX + window.innerWidth - 380) + 'px';
    tip.querySelector('[data-next]').onclick = next;
    tip.querySelector('[data-skip]').onclick = end;
  }
  function next(){ i++; if(i>=steps.length){ end(); } else { place(); } }
  function end(){ overlay.remove(); tip.remove(); localStorage.setItem("medj_tour_done","1"); }
  place();
})();
