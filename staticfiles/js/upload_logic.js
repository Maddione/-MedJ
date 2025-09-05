(function () {
  "use strict";

  const ACCEPT = [".pdf", ".jpg", ".jpeg", ".png"];

  const mainUploadForm = document.getElementById("main-upload-form") || document.querySelector("form#upload-form") || document.querySelector("form[action*='upload']");
  if (!mainUploadForm) return;
  const fileInputCandidates = [
    document.getElementById("document-input"),
    document.getElementById("file_input"),
    mainUploadForm.querySelector('input[type="file"]')
  ].filter(Boolean);

  const fileInput = fileInputCandidates[0];
  if (!fileInput) return;

  function ensureMultipleAndAccept(input) {
    const accept = input.getAttribute("accept");
    if (!accept) input.setAttribute("accept", ACCEPT.join(","));
    if (!input.multiple) input.multiple = true;
    if (input.name !== "files") input.name = "files";
  }
  ensureMultipleAndAccept(fileInput);

  const formActionInput = document.getElementById("form-action"); // hidden input toggling the action
  const step1Section = document.getElementById("step1-selection-section");
  const step2UploadSection = document.getElementById("step2-upload-section");
  const step3ReviewSection = document.getElementById("step3-review-section");
  const step4ResultsSection = document.getElementById("step4-results-section");
  const mainSubmitButtonContainer = document.getElementById("main-submit-button-container");

  const editedOcrTextArea = document.getElementById("edited-ocr-text-area");
  const analyzeAndSaveButton = document.getElementById("analyze-and-save-button");
  const backToStep1Button = document.getElementById("back-to-step1-button");
  const mainUploadButton = document.getElementById("main-upload-button");

  const fileNameDisplay = document.getElementById("file-name-display");
  const imagePreview = document.getElementById("image-preview") || document.getElementById("img_preview");
  const pdfPreview = document.getElementById("pdf-preview") || document.getElementById("pdf_preview");
  const previewPlaceholder = document.getElementById("preview-placeholder") || document.getElementById("preview_wrap");
  const viewFullSizeLink = document.getElementById("view-full-size-link");

  const specialtiesUrl = mainUploadForm.dataset?.specialtiesUrl || "";
  const csrfTokenInput = document.querySelector('[name=csrfmiddlewaretoken]');
  const csrfToken = csrfTokenInput ? csrfTokenInput.value : "";

  function ensureWarningBanner() {
    let banner = document.getElementById("upload-one-doc-warning");
    if (!banner) {
      const container = document.getElementById("upload-warning-zone") || step2UploadSection || step1Section || mainUploadForm;
      banner = document.createElement("div");
      banner.id = "upload-one-doc-warning";
      banner.className = "rounded-xl p-3 mb-4 border border-amber-300 bg-amber-50 text-amber-900 text-sm";
      banner.innerHTML = `
        <strong>Важно:</strong> Качвайте файлове, които принадлежат на <u>ЕДИН</u> документ.<br>
        • Позволено: <em>един PDF</em> <strong>или</strong> <em>много изображения (JPG/PNG)</em> на същия документ.<br>
        • Забранено: смесване на PDF и изображения едновременно или повече от един PDF.
      `;
      container ? container.prepend(banner) : document.body.prepend(banner);
    }
    return banner;
  }
  ensureWarningBanner();

  function extOf(f) {
    const n = (f?.name || "").toLowerCase();
    const i = n.lastIndexOf(".");
    return i >= 0 ? n.slice(i) : "";
  }

  function classifyFiles(files) {
    let pdfs = 0, images = 0, bad = 0;
    for (const f of files) {
      const e = extOf(f);
      if (!ACCEPT.includes(e)) { bad++; continue; }
      if (e === ".pdf") pdfs++; else images++;
    }
    return { pdfs, images, bad, total: files.length };
  }

  function validateFiles(files) {
    if (!files || !files.length) return { ok: false, reason: "Няма избрани файлове." };
    const { pdfs, images, bad } = classifyFiles(files);
    if (bad > 0) return { ok: false, reason: "Има файлове с неподдържан формат. Позволени: PDF, JPG, JPEG, PNG." };
    if (pdfs > 1) return { ok: false, reason: "Позволен е само един PDF." };
    if (pdfs === 1 && images > 0) return { ok: false, reason: "Не смесвайте PDF и изображения в едно качване." };
    return { ok: true, kind: (pdfs === 1) ? "pdf" : "images" };
  }

  const spinnerSVG = `<svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white inline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>`;

  function showLoading(button, message) {
    if (!button) return;
    button.disabled = true;
    button.innerHTML = `${spinnerSVG}${message || "Обработване..."}`;
    button.style.backgroundColor = "#0A4E75";
  }

  function resetButton(button, originalText, originalColor) {
    if (!button) return;
    button.disabled = false;
    button.textContent = originalText;
    if (originalColor) button.style.backgroundColor = originalColor;
  }

  function displayError(message) {
    // Prefer a styled error div if you have one
    const zone = document.getElementById("upload-error-zone") || document.querySelector(".bg-light-red-bg");
    if (zone && zone.querySelector("span")) {
      zone.querySelector("span").textContent = message;
      zone.classList.remove("hidden");
    } else {
      alert(message);
    }
  }
  function hideError() {
    const zone = document.getElementById("upload-error-zone") || document.querySelector(".bg-light-red-bg");
    if (zone) zone.classList.add("hidden");
  }

  function renderPreview(files, kind) {
    if (!previewPlaceholder) return;

    if (imagePreview) imagePreview.classList.add("hidden");
    if (pdfPreview) pdfPreview.classList.add("hidden");

    if (!files || !files.length) {
      previewPlaceholder.classList.add("hidden");
      return;
    }

    previewPlaceholder.classList.remove("hidden");

    if (kind === "pdf" && files.length === 1 && files[0].type === "application/pdf" && pdfPreview) {
      const url = URL.createObjectURL(files[0]);
      pdfPreview.src = url + "#toolbar=0&navpanes=0&scrollbar=0";
      pdfPreview.classList.remove("hidden");
      if (imagePreview) imagePreview.classList.add("hidden");
      if (fileNameDisplay) {
        fileNameDisplay.textContent = `Файл: ${files[0].name}`;
        fileNameDisplay.style.color = "#15BC11";
      }
      if (viewFullSizeLink) {
        viewFullSizeLink.href = url;
        viewFullSizeLink.classList.remove("hidden");
      }
      return;
    }
    const firstImage = files.find(f => f.type.startsWith("image/"));
    if (firstImage && imagePreview) {
      const r = new FileReader();
      r.onload = e => {
        imagePreview.src = e.target.result;
        imagePreview.classList.remove("hidden");
        if (pdfPreview) pdfPreview.classList.add("hidden");
      };
      r.readAsDataURL(firstImage);
    }
    if (fileNameDisplay) {
      const names = Array.from(files).map(f => f.name).join(", ");
      fileNameDisplay.textContent = `Избрани файлове (${files.length}): ${names}`;
      fileNameDisplay.style.color = "#15BC11";
    }
    if (viewFullSizeLink) viewFullSizeLink.classList.add("hidden");
  }

  function currentMessages() {
    const M = (typeof window.MESSAGES !== "undefined") ? window.MESSAGES : {};
    return Object.assign({
      processing: "Обработване...",
      upload_button: "Изпрати",
      approve_analyze_ai: "Одобри и анализирай с AI",
      network_server_error: "Мрежова/сървърна грешка.",
      critical_ocr_error: "Грешка при OCR.",
      critical_analysis_error: "Грешка при анализ.",
      no_file_chosen: "Няма избран файл."
    }, M);
  }

  fileInput.addEventListener("change", function () {
    const files = fileInput.files;
    if (!files || !files.length) {
      if (fileNameDisplay) {
        fileNameDisplay.textContent = currentMessages().no_file_chosen;
        fileNameDisplay.style.color = "#6B7280";
      }
      if (previewPlaceholder) previewPlaceholder.classList.add("hidden");
      return;
    }
    const res = validateFiles(files);
    if (!res.ok) {
      displayError(res.reason);
      fileInput.value = ""; // reset
      if (previewPlaceholder) previewPlaceholder.classList.add("hidden");
      return;
    }
    renderPreview(files, res.kind);
  });
  mainUploadForm.addEventListener("submit", function (event) {
    event.preventDefault();
    hideError();

    const M = currentMessages();
    const formData = new FormData();
    Array.from(mainUploadForm.elements).forEach(el => {
      if (!el.name || el.type === "file") return;
      // include selected values only
      if ((el.type === "checkbox" || el.type === "radio") && !el.checked) return;
      formData.append(el.name, el.value);
    });
    const files = fileInput.files;
    if (!files || !files.length) {
      displayError("Моля, изберете файл(ове).");
      return;
    }
    const v = validateFiles(files);
    if (!v.ok) {
      displayError(v.reason);
      return;
    }
    for (const f of files) formData.append("files", f);
    const actionInput = formActionInput || mainUploadForm.querySelector('input[name="action"]');
    const action = actionInput ? (actionInput.value || actionInput.getAttribute("value") || "") : "";
    const primaryBtn = (action === "analyze_and_save") ? analyzeAndSaveButton : mainUploadButton;
    showLoading(primaryBtn, (action === "analyze_and_save") ? M.approve_analyze_ai : M.processing);

    fetch(mainUploadForm.action, {
      method: "POST",
      headers: csrfToken ? { "X-CSRFToken": csrfToken } : {},
      body: formData
    })
      .then(r => r.json())
      .then(data => {
        resetButton(primaryBtn, (action === "analyze_and_save") ? M.approve_analyze_ai : M.upload_button, "#15BC11");

        if (data && data.redirect_url) {
          window.location.href = data.redirect_url;
          return;
        }

        if (!data || data.status === "error" || data.ok === false) {
          displayError(data?.message || data?.error || M.critical_ocr_error);
          return;
        }

        if (action === "analyze_and_save") {
          const summary = document.getElementById("analysis-summary-display");
          const table = document.getElementById("analysis-html-table-display");
          const viewBtn = document.getElementById("view-medical-event-button");
          if (summary && typeof data.summary === "string") summary.innerHTML = data.summary;
          if (table && typeof data.html_table === "string") table.innerHTML = data.html_table;
          if (viewBtn && data.event_id) viewBtn.href = `${window.location.origin}/medical-events/${data.event_id}/detail/`;
          if (step1Section) step1Section.classList.add("hidden");
          if (step2UploadSection) step2UploadSection.classList.add("hidden");
          if (mainSubmitButtonContainer) mainSubmitButtonContainer.classList.add("hidden");
          if (step3ReviewSection) step3ReviewSection.classList.add("hidden");
          if (step4ResultsSection) step4ResultsSection.classList.remove("hidden");
        } else {
          const ocrText = data.ocr_text || data.extracted_text || "";
          if (editedOcrTextArea) editedOcrTextArea.value = ocrText;

          if (step1Section) step1Section.classList.add("hidden");
          if (step2UploadSection) step2UploadSection.classList.add("hidden");
          if (mainSubmitButtonContainer) mainSubmitButtonContainer.classList.add("hidden");
          if (step3ReviewSection) step3ReviewSection.classList.remove("hidden");
          if (step4ResultsSection) step4ResultsSection.classList.add("hidden");

          if (formActionInput) formActionInput.value = "analyze_and_save";
        }
      })
      .catch(err => {
        console.error("Upload error:", err);
        resetButton(primaryBtn, (action === "analyze_and_save") ? M.approve_analyze_ai : M.upload_button, "#15BC11");
        displayError(M.network_server_error);
      });
  });

  if (backToStep1Button) {
    backToStep1Button.addEventListener("click", function () {
      if (formActionInput) formActionInput.value = "perform_ocr_and_analyze";
      if (step1Section) step1Section.classList.remove("hidden");
      if (step2UploadSection) step2UploadSection.classList.remove("hidden");
      if (mainSubmitButtonContainer) mainSubmitButtonContainer.classList.remove("hidden");
      if (step3ReviewSection) step3ReviewSection.classList.add("hidden");
      if (step4ResultsSection) step4ResultsSection.classList.add("hidden");
      if (editedOcrTextArea) editedOcrTextArea.value = "";
      if (fileInput) fileInput.value = "";
      if (fileNameDisplay) { fileNameDisplay.textContent = (window.MESSAGES?.no_file_chosen || "Няма избран файл."); fileNameDisplay.style.color = "#6B7280"; }
      if (previewPlaceholder) previewPlaceholder.classList.add("hidden");
      if (imagePreview) imagePreview.classList.add("hidden");
      if (pdfPreview) pdfPreview.classList.add("hidden");
      if (viewFullSizeLink) viewFullSizeLink.classList.add("hidden");
    });
  }
})();
