(function () {
  var KEY = "onboarding_state";
  function readState() {
    try { return JSON.parse(localStorage.getItem(KEY)) || { step: 1, done: false }; }
    catch (e) { return { step: 1, done: false }; }
  }
  function writeState(s) { try { localStorage.setItem(KEY, JSON.stringify(s)); } catch (e) {} }
  function nextPathFor(step) {
    if (step === 1) return "/personalcard/";
    if (step === 2) return "/upload/";
    if (step === 3) return "/upload/history/";
    return "/";
  }
  function throttleRedirect(to) {
    var tsKey = KEY + "_last_redirect";
    var now = Date.now();
    try {
      var last = parseInt(localStorage.getItem(tsKey) || "0", 10);
      if (isFinite(last) && now - last < 2000) return; // 2s guard
      localStorage.setItem(tsKey, String(now));
    } catch (e) {}
    if (location.pathname !== to) location.href = to;
  }

  var state = readState();
  if (state.done) return;

  // Soft-enforce we are on the expected page for current step
  var expected = nextPathFor(state.step);
  if (!new RegExp("^" + expected.replace(/\//g, "\\/") + "?$").test(location.pathname)) {
    throttleRedirect(expected);
  }

  // Click handler to advance when user acknowledges (no template changes needed)
  document.addEventListener("click", function (e) {
    var t = e.target;
    if (!t) return;

    var text = (t.innerText || t.textContent || "").trim().toLowerCase();
    var isAckText = /^(разбрах|got it|i understand|ок|ok)$/i.test(text);
    var isModalHide = t.hasAttribute("data-modal-hide") || t.closest("[data-modal-hide]");
    var isOnboardingNext = t.matches("[data-onboarding-next], .onboarding-next") || t.closest("[data-onboarding-next], .onboarding-next");

    if (!(isAckText || isModalHide || isOnboardingNext)) return;

    // Advance state
    if (state.step < 3) {
      state.step += 1;
    } else {
      state.done = true;
    }
    writeState(state);

    // Navigate for next step or finish
    if (state.done) {
      // Close any open modal if present
      var modal = document.getElementById("onboarding_modal");
      if (modal) {
        modal.classList.add("hidden", "opacity-0", "invisible");
        modal.classList.remove("visible", "opacity-100");
      }
      return;
    }
    throttleRedirect(nextPathFor(state.step));
  });

  // Escape key to dismiss when on final step
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      var s = readState();
      s.done = true; writeState(s);
      var modal = document.getElementById("onboarding_modal");
      if (modal) {
        modal.classList.add("hidden", "opacity-0", "invisible");
        modal.classList.remove("visible", "opacity-100");
      }
    }
  });
})();
