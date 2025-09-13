(function () {
  function once(key, fn) {
    if (localStorage.getItem(key) === "1") return;
    fn();
    localStorage.setItem(key, "1");
  }

  function showPopup(title, text) {
    var overlay = document.createElement("div");
    overlay.style.position = "fixed";
    overlay.style.inset = "0";
    overlay.style.background = "rgba(0,0,0,0.45)";
    overlay.style.display = "flex";
    overlay.style.alignItems = "center";
    overlay.style.justifyContent = "center";
    overlay.style.zIndex = "9999";

    var box = document.createElement("div");
    box.style.maxWidth = "560px";
    box.style.width = "90%";
    box.style.background = "white";
    box.style.borderRadius = "12px";
    box.style.boxShadow = "0 10px 30px rgba(0,0,0,0.2)";
    box.style.padding = "20px";

    var h = document.createElement("h2");
    h.textContent = title;
    h.style.fontSize = "20px";
    h.style.fontWeight = "700";
    h.style.margin = "0 0 10px 0";

    var p = document.createElement("p");
    p.textContent = text;
    p.style.margin = "0 0 16px 0";
    p.style.lineHeight = "1.5";

    var btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = "Разбрах";
    btn.style.display = "inline-flex";
    btn.style.alignItems = "center";
    btn.style.justifyContent = "center";
    btn.style.padding = "10px 16px";
    btn.style.border = "none";
    btn.style.borderRadius = "8px";
    btn.style.background = "#2563eb";
    btn.style.color = "white";
    btn.style.fontWeight = "600";
    btn.style.cursor = "pointer";

    btn.addEventListener("click", function () {
      document.body.removeChild(overlay);
    });

    box.appendChild(h);
    box.appendChild(p);
    box.appendChild(btn);
    overlay.appendChild(box);
    document.body.appendChild(overlay);
  }

  function pathIs(re) {
    return re.test(location.pathname);
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (pathIs(/^\/personalcard\/?$/)) {
      once("onboarding_seen_step1", function () {
        showPopup(
          "Стъпка 1: Личен картон",
          "Въведете име, фамилия и дата на раждане. Полетата със * са задължителни. Натиснете „Запази“, след което „Разбрах“."
        );
      });
      return;
    }

    if (pathIs(/^\/upload\/?$/)) {
      once("onboarding_seen_step2", function () {
        showPopup(
          "Стъпка 2: Качване на документи",
          "Качете файл(ове) от устройството си. След качване може да продължите към анализ и потвърждаване."
        );
      });
      return;
    }

    if (pathIs(/^\/upload\/history\/?$/)) {
      once("onboarding_seen_step3", function () {
        showPopup(
          "Стъпка 3: История на качванията",
          "Тук виждате последно качените документи и статусите им. Може да отворите детайли или да споделите."
        );
      });
      return;
    }
  });
})();
