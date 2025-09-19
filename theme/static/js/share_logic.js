(function(){
  const form = document.getElementById("share-filters");
  if (!form) return;

  const applyBtn = document.getElementById("gen-links");
  const summaryBox = document.getElementById("results-summary");
  const listBox = document.getElementById("results-list");
  const qrImg = document.getElementById("qr-img");
  const linkFields = {
    events: document.getElementById("link-pdf-events"),
    labs: document.getElementById("link-pdf-labs"),
    csv: document.getElementById("link-csv"),
  };
  const openButtons = {
    events: document.getElementById("btn-pdf-events"),
    labs: document.getElementById("btn-pdf-labs"),
    csv: document.getElementById("btn-csv"),
  };
  const eventsToggle = form.querySelector('#generate-events');
  const labsToggle = form.querySelector('#generate-labs');
  const csvToggle = form.querySelector('#generate-csv');
  const createUrl = form.dataset.createLinksUrl || "";
  const qrUrl = form.dataset.qrForUrl || "";

  let dirty = false;
  let isLoading = false;
  let lastPayload = null;
  const defaultSummary = summaryBox ? summaryBox.textContent : "";
  const buttonDefaultText = applyBtn ? applyBtn.textContent : "";

  function getCSRF(){
    const el = document.querySelector('input[name="csrfmiddlewaretoken"]');
    return el ? el.value : '';
  }

  function escapeHtml(str){
    return String(str || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function clampHours(value){
    const num = parseInt(value || 0, 10);
    if (Number.isNaN(num) || num < 1) return 1;
    if (num > 8760) return 8760;
    return num;
  }

  function getValues(name){
    return Array.from(form.querySelectorAll(`input[name="${name}"]:checked, select[name="${name}"] option:checked`))
      .map((node) => node.value)
      .filter((val) => val != null && val !== "");
  }

  function payloadFromForm(){
    const fd = new FormData(form);
    return {
      start_date: (fd.get("start_date") || "").trim(),
      end_date: (fd.get("end_date") || "").trim(),
      hours_events: clampHours(fd.get("hours_events")),
      hours_labs: clampHours(fd.get("hours_labs")),
      hours_csv: clampHours(fd.get("hours_csv")),
      generate_events: !!eventsToggle?.checked,
      generate_labs: !!labsToggle?.checked,
      generate_csv: !!csvToggle?.checked,
      filters: {
        specialty: getValues("specialty"),
        category: getValues("category"),
        event: getValues("event"),
        indicator: getValues("indicator"),
      },
    };
  }

  function hasAnyOutputSelected(){
    return !!(eventsToggle?.checked || labsToggle?.checked || csvToggle?.checked);
  }

  function setButtonState(){
    if (!applyBtn) return;
    const shouldDisable = !hasAnyOutputSelected() || isLoading || (!dirty && lastPayload !== null);
    applyBtn.disabled = shouldDisable;
    applyBtn.classList.toggle("opacity-50", shouldDisable);
    applyBtn.classList.toggle("cursor-not-allowed", shouldDisable);
    applyBtn.setAttribute("aria-disabled", shouldDisable ? "true" : "false");
  }

  function markDirty(){
    dirty = true;
    setButtonState();
  }

  function setSummary(text){
    if (!summaryBox) return;
    const value = (text || "").toString().trim();
    summaryBox.textContent = value || defaultSummary;
  }

  function clearLinks(){
    Object.entries(linkFields).forEach(([key, field]) => {
      if (field) field.value = "";
      const btn = openButtons[key];
      if (btn){
        btn.href = "#";
        btn.classList.add("opacity-50", "pointer-events-none");
      }
    });
  }

  function renderDocuments(items){
    if (!listBox) return;
    if (items === null){
      listBox.innerHTML = "";
      return;
    }
    listBox.innerHTML = "";
    if (!Array.isArray(items) || !items.length){
      const li = document.createElement("li");
      li.className = "text-sm text-gray-500 bg-gray-50 rounded-lg px-3 py-2";
      li.textContent = "Няма документи за показване.";
      listBox.appendChild(li);
      return;
    }
    items.forEach((item) => {
      const li = document.createElement("li");
      li.className = "border border-gray-200 rounded-xl px-3 py-2 bg-white shadow-sm";
      const title = document.createElement("div");
      title.className = "text-sm font-semibold text-[#0A4E75]";
      title.textContent = item.title || `Документ №${item.id || ''}`;
      const meta = document.createElement("div");
      meta.className = "text-xs text-gray-500 mt-1";
      const uploaded = item.uploaded_at ? `Качен: ${item.uploaded_at}` : "";
      const docDate = item.document_date ? `Документ: ${item.document_date}` : "";
      meta.textContent = [uploaded, docDate].filter(Boolean).join(" • ");
      li.appendChild(title);
      if (meta.textContent) li.appendChild(meta);
      if (Array.isArray(item.tags) && item.tags.length){
        const tagsWrap = document.createElement("div");
        tagsWrap.className = "flex flex-wrap gap-1 mt-2";
        item.tags.slice(0, 6).forEach((tag) => {
          const badge = document.createElement("span");
          badge.className = "text-xs bg-[#EAEBDA] text-[#0A4E75] px-2 py-0.5 rounded-full";
          badge.textContent = tag;
          tagsWrap.appendChild(badge);
        });
        li.appendChild(tagsWrap);
      }
      const actions = document.createElement("div");
      actions.className = "mt-2 flex flex-wrap gap-2";
      if (item.detail_url){
        const link = document.createElement("a");
        link.href = item.detail_url;
        link.className = "inline-flex items-center gap-1 text-xs text-[#0A4E75] hover:underline";
        link.innerHTML = `${escapeHtml("Виж детайли")} <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>`;
        actions.appendChild(link);
      }
      if (item.export_pdf_url){
        const pdf = document.createElement("a");
        pdf.href = item.export_pdf_url;
        pdf.target = "_blank";
        pdf.rel = "noopener";
        pdf.className = "inline-flex items-center gap-1 text-xs text-white bg-[#0A4E75] hover:bg-[#073954] transition-colors px-2 py-1 rounded-lg";
        pdf.innerHTML = `<i class="fa-solid fa-file-pdf"></i> ${escapeHtml("PDF")}`;
        actions.appendChild(pdf);
      }
      if (actions.children.length){
        li.appendChild(actions);
      }
      listBox.appendChild(li);
    });
  }

  function setLink(key, url){
    const field = linkFields[key];
    const btn = openButtons[key];
    if (!field || !btn) return;
    const value = (url || "").toString();
    field.value = value;
    if (value){
      btn.href = value;
      btn.classList.remove("opacity-50", "pointer-events-none");
    } else {
      btn.href = "#";
      btn.classList.add("opacity-50", "pointer-events-none");
    }
  }

  function updateLinks(payload, data){
    setLink("events", payload.generate_events ? data.pdf_events_url : "");
    setLink("labs", payload.generate_labs ? data.pdf_labs_url : "");
    setLink("csv", payload.generate_csv ? data.csv_url : "");
  }

  function updateQr(payload, data){
    if (!qrImg) return;
    let target = "";
    if (payload.generate_events && data.pdf_events_url) target = data.pdf_events_url;
    else if (payload.generate_labs && data.pdf_labs_url) target = data.pdf_labs_url;
    else if (payload.generate_csv && data.csv_url) target = data.csv_url;
    if (!target){
      qrImg.removeAttribute("src");
      return;
    }
    const endpoint = qrUrl || "";
    if (!endpoint){
      qrImg.src = target;
      return;
    }
    const url = `${endpoint}?url=${encodeURIComponent(target)}&v=${Date.now()}`;
    qrImg.src = url;
  }

  function applyCounts(data){
    if (!data || typeof data !== "object") return;
    if (data.notice){
      setSummary(data.notice);
      return;
    }
    const counts = data.counts || {};
    const pieces = [];
    if (counts.documents) pieces.push(`${counts.documents} документа`);
    if (counts.events) pieces.push(`${counts.events} събития`);
    if (counts.labs) pieces.push(`${counts.labs} лабораторни показателя`);
    setSummary(pieces.length ? `Намерени: ${pieces.join(', ')}.` : "Няма резултати за избраните филтри.");
  }

  function setLoading(flag){
    isLoading = !!flag;
    if (applyBtn){
      if (isLoading){
        applyBtn.textContent = "Генериране...";
        applyBtn.classList.add("opacity-50", "cursor-wait");
        applyBtn.setAttribute("aria-busy", "true");
      } else {
        applyBtn.textContent = buttonDefaultText;
        applyBtn.classList.remove("cursor-wait");
        applyBtn.removeAttribute("aria-busy");
      }
    }
    setButtonState();
  }

  async function generateLinks(){
    if (!applyBtn || applyBtn.disabled) return;
    const payload = payloadFromForm();
    lastPayload = payload;
    setLoading(true);
    clearLinks();
    renderDocuments(null);
    setSummary("Генериране на линкове...");
    try {
      const resp = await fetch(createUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRFToken": getCSRF() },
        body: JSON.stringify(payload),
      });
      if (!resp.ok){
        setSummary("Грешка при генерирането. Моля, опитайте отново.");
        return;
      }
      const data = await resp.json();
      updateLinks(payload, data);
      renderDocuments(data.documents || []);
      updateQr(payload, data);
      applyCounts(data);
      dirty = false;
    } catch (err){
      console.error("share links", err);
      setSummary("Възникна проблем при връзката със сървъра.");
    } finally {
      setLoading(false);
    }
  }

  function clearState(){
    clearLinks();
    if (qrImg) qrImg.removeAttribute("src");
    renderDocuments(null);
    setSummary(defaultSummary);
  }

  form.addEventListener("change", markDirty);
  form.addEventListener("input", markDirty);
  if (applyBtn){
    applyBtn.addEventListener("click", function(e){
      e.preventDefault();
      generateLinks();
    });
  }

  clearState();
  setButtonState();
})();
