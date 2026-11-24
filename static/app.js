(function () {
  "use strict";

  var analytical = document.getElementById("analytical-form");
  var spice = document.getElementById("spice-form");
  var engineRadios = document.querySelectorAll('input[name="engine"]');

  function selectedEngine() {
    var checked = document.querySelector('input[name="engine"]:checked');
    return checked ? checked.value : "spice";
  }

  function syncEngine() {
    var engine = selectedEngine();
    if (analytical) analytical.hidden = engine !== "analytical";
    if (spice) spice.hidden = engine !== "spice";
  }

  engineRadios.forEach(function (radio) {
    radio.addEventListener("change", syncEngine);
  });
  syncEngine();

  var biasMode = document.getElementById("bias_mode");
  function syncBias() {
    if (!biasMode) return;
    var mode = biasMode.value;
    document.querySelectorAll("#analytical-form [data-modes]").forEach(function (field) {
      var allowed = (field.dataset.modes || "").split(/\s+/);
      field.hidden = allowed.indexOf(mode) === -1;
    });
  }
  if (biasMode) biasMode.addEventListener("change", syncBias);
  syncBias();

  var analysis = document.getElementById("analysis");
  var hint = document.getElementById("analysis-hint");
  var hints = {
    dc: "DC: CIN/COUT เปิดวงจร; อ่าน VB/VE/VC/VCE/IC จาก operating point",
    ac: "AC: small-signal sweep แสดง gain magnitude และ phase เทียบความถี่",
    tran: "Transient: แหล่ง SIN ตาม amplitude/frequency ที่กรอก แสดง Vin/Vout กับเวลา"
  };
  function syncAnalysis() {
    if (!analysis) return;
    var mode = analysis.value;
    if (hint) hint.textContent = hints[mode] || "";
    document.querySelectorAll("#spice-form [data-modes]").forEach(function (part) {
      var allowed = (part.dataset.modes || "").split(/\s+/);
      part.hidden = allowed.indexOf(mode) === -1;
    });
  }
  if (analysis) analysis.addEventListener("change", syncAnalysis);
  syncAnalysis();

  [analytical, spice].forEach(function (form) {
    if (!form) return;
    var button = form.querySelector('button[type="submit"]');
    if (!button) return;
    var label = button.textContent;
    form.addEventListener("submit", function () {
      button.disabled = true;
      button.textContent = "กำลังรัน…";
    });
    window.addEventListener("pageshow", function () {
      button.disabled = false;
      button.textContent = label;
    });
  });
})();
