(function () {
  var KEY = "onboarding_state";

  function readState() {
    try { return JSON.parse(localStorage.getItem(KEY)) || { step: 1, done: false }; }
    catch (e) { return { step: 1, done: false }; }
  }
  function writeState(s) { try { localStorage.setItem(KEY, JSON.stringify(s)); } catch (e) {} }

  function isPersonalCard(path) { return /^\/personalcard\/?$/.test(path); }
  function isUpload(path) { return /^\/(?:app\/)?upload\/?$/.test(path); }
  function isUploadHistory(path) { return /^\/(?:app\/)?upload\/history\/?$/.test(path); }

  function throttleRedirect(to) {
    var tsKey = KEY + "_last_redirect";
    var now = Date.now();
    try {
      var last = parseInt(localStorage.getItem(tsKey) || "0", 10);
      if (isFinite(last) && now - last < 2000) return;
      localStorage.setItem(tsKey, String(now));
    } catch (e) {}
    if (location.pathname !== to) location.href = to;
  }

  var state = readState();
  if (state.done) return;

  var path = location.pathname;

  if (state.step <= 1) {
    if (!isPersonalCard(path)) {
      throttleRedirect("/personalcard/");
      return;
    }
    state.step = 1;
    writeState(state);
  } else if (state.step === 2) {
    if (!isUpload(path)) {
      return;
    }
  } else if (state.step === 3) {
    if (!isUploadHistory(path)) {
      return;
    }
  }

  if (isUpload(path) && state.step < 2) {
    state.step = 2;
    writeState(state);
  }
  if (isUploadHistory(path) && state.step < 3) {
    state.step = 3;
    writeState(state);
  }

  document.addEventListener("click", function (e) {
    var t = e.target;
    if (!t) return;

    var txt = (t.innerText || t.textContent || "").trim();
    var isAck = /^(Разбрах|разбрах|Got it|I understand|OK|Ok|ok)$/.test(txt);
    var isModalHide = t.hasAttribute("data-modal-hide") || (t.closest && t.closest("[data-modal-hide]"));
    var isNext = (t.matches && t.matches("[data-onboarding-next], .onboarding-next")) ||
                 (t.closest && t.closest("[data-onboarding-next], .onboarding-next"));

    if (!(isAck || isModalHide || isNext)) return;

    var s = readState();
    if (isUploadHistory(path)) {
      s.done = true;
    } else if (isUpload(path)) {
      s.step = Math.max(s.step, 2);
    } else if (isPersonalCard(path)) {
      s.step = 1;
    }
    writeState(s);

    if (s.done) {
      var modal = document.getElementById("onboarding_modal");
      if (modal) {
        modal.classList.add("hidden", "opacity-0", "invisible");
        modal.classList.remove("visible", "opacity-100");
      }
    }
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      var s = readState();
      s.done = true;
      writeState(s);
      var modal = document.getElementById("onboarding_modal");
      if (modal) {
        modal.classList.add("hidden", "opacity-0", "invisible");
        modal.classList.remove("visible", "opacity-100");
      }
    }
  });
})();
