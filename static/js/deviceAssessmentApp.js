/**
 * Device Assessment App Controller
 * Handles questionnaire, image uploads, result display, and demo return loading.
 */

document.addEventListener("DOMContentLoaded", () => {
  // ─── State ───────────────────────────────────────────────────────────────
  const state = {
    selectedReturn: null,
    uploadedImages: [],    // { fileName, dataUrl, label }
    powersOn: null,        // true / false / null (unknown)
    result: null
  };

  // ─── DOM refs ─────────────────────────────────────────────────────────────
  const tabBtns = document.querySelectorAll(".module-tab-btn");
  const tabViews = document.querySelectorAll(".da-tab-view");

  const returnsGrid = document.getElementById("demoReturnsGrid");
  const selectedReturnBanner = document.getElementById("selectedReturnBanner");
  const selectedReturnId = document.getElementById("selectedReturnIdText");
  const selectedReturnName = document.getElementById("selectedReturnNameText");
  const btnClearReturn = document.getElementById("btnClearReturn");

  const form = document.getElementById("deviceAssessmentForm");
  const btnSubmit = document.getElementById("btnSubmitDeviceAssessment");
  const submitAlertBanner = document.getElementById("daAlertBanner");

  const resultView = document.getElementById("daResultView");
  const resultSkeleton = document.getElementById("daResultSkeleton");

  // Score gauges
  const gCondition = document.getElementById("gaugeCondition");
  const gRepair = document.getElementById("gaugeRepair");
  const gConfidence = document.getElementById("gaugeConfidence");
  const gRisk = document.getElementById("gaugeRisk");

  // Auth / warranty badges
  const authBadge = document.getElementById("authStatusBadge");
  const warrantyBadge = document.getElementById("warrantyStatusBadge");
  const dispositionBadge = document.getElementById("dispositionBadge");
  const assessmentIdEl = document.getElementById("daAssessmentId");
  const backendModeEl = document.getElementById("daBackendMode");
  const manualReviewBox = document.getElementById("manualReviewBox");
  const manualReviewReasons = document.getElementById("manualReviewReasons");

  // Evidence panels
  const evidenceAuthBody = document.getElementById("evidenceAuthBody");
  const evidenceCondBody = document.getElementById("evidenceCondBody");
  const evidenceWarrBody = document.getElementById("evidenceWarrBody");

  // Btn new assessment
  const btnNewAssessment = document.getElementById("btnNewAssessment");

  // ─── Header status badge ─────────────────────────────────────────────────
  const headerBadge = document.getElementById("headerApiBadge");
  (async () => {
    if (!headerBadge || !window.deviceAssessmentApi) return;
    const h = await window.deviceAssessmentApi.checkHealth();
    if (h.isLive) {
      headerBadge.className = "api-status-badge";
      headerBadge.innerHTML = `<span class="status-dot"></span><span>Live Backend v2.0</span>`;
    } else {
      headerBadge.className = "api-status-badge mock-mode";
      headerBadge.innerHTML = `<span class="status-dot"></span><span>Mock Service Ready</span>`;
    }
  })();

  // ─── Toast helper ────────────────────────────────────────────────────────
  function toast(msg, type = "info") {
    const c = document.getElementById("toastContainer");
    if (!c) return;
    const t = document.createElement("div");
    t.className = `toast toast-${type}`;
    const icon = type === "success" ? "✅" : type === "error" ? "❌" : "ℹ️";
    t.innerHTML = `<span>${icon}</span><span>${msg}</span>`;
    c.appendChild(t);
    setTimeout(() => {
      t.style.opacity = "0";
      t.style.transform = "translateY(10px)";
      t.style.transition = "all 0.3s ease";
      setTimeout(() => t.remove(), 300);
    }, 4500);
  }

  // ─── Tab switching ────────────────────────────────────────────────────────
  tabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      tabBtns.forEach(b => b.classList.remove("active"));
      tabViews.forEach(v => v.style.display = "none");
      btn.classList.add("active");
      const target = document.getElementById(btn.dataset.tab);
      if (target) target.style.display = "block";
    });
  });

  // ─── Load demo returns ────────────────────────────────────────────────────
  async function loadDemoReturns() {
    if (!returnsGrid) return;
    returnsGrid.innerHTML = `<div style="color: var(--text-muted); font-size: 0.875rem;">Loading demo returns...</div>`;

    const returns = await window.deviceAssessmentApi.fetchDemoReturns();
    if (!returns || returns.length === 0) {
      returnsGrid.innerHTML = `<div style="color: var(--text-muted);">No demo returns available. Ensure the backend is running.</div>`;
      return;
    }

    returnsGrid.innerHTML = "";
    returns.forEach(ret => {
      const badgeColor = ret.label && ret.label.includes("COUNTERFEIT") ? "var(--rose-400)" :
        ret.label && ret.label.includes("SUSPICIOUS") ? "var(--amber-400)" :
          ret.label && ret.label.includes("UNKNOWN") ? "#a5b4fc" : "var(--emerald-400)";

      const card = document.createElement("div");
      card.className = "return-card";
      card.innerHTML = `
        <div class="return-card-type-badge" style="color: ${badgeColor}; background: rgba(0,0,0,0.4); border: 1px solid ${badgeColor};">
          ${(ret.label || "").split("—")[0].trim()}
        </div>
        <div class="return-card-id">${ret.returnId}</div>
        <div class="return-card-name">${ret.manufacturer || ""} ${ret.model || ""}</div>
        <div class="return-card-meta">${ret.category || ""} · ${ret.sellerChannel || "Unknown channel"}</div>
        <div class="return-card-meta" style="margin-top: 0.35rem; font-size: 0.72rem; color: var(--text-muted);">
          ${(ret.label || "").split("—").slice(1).join("—").trim()}
        </div>
      `;
      card.addEventListener("click", () => selectReturn(ret));
      returnsGrid.appendChild(card);
    });
  }

  loadDemoReturns();

  function selectReturn(ret) {
    state.selectedReturn = ret;
    if (selectedReturnBanner) selectedReturnBanner.style.display = "flex";
    if (selectedReturnId) selectedReturnId.textContent = ret.returnId;
    if (selectedReturnName) selectedReturnName.textContent = `${ret.manufacturer || ""} ${ret.model || ""}`.trim() || "Unnamed Device";

    // Switch to questionnaire tab and pre-fill
    tabBtns.forEach(b => b.classList.remove("active"));
    tabViews.forEach(v => v.style.display = "none");
    const qTab = document.querySelector('[data-tab="daTabQuestionnaire"]');
    if (qTab) qTab.classList.add("active");
    const qView = document.getElementById("daTabQuestionnaire");
    if (qView) qView.style.display = "block";

    prefillForm(ret);
    toast(`Loaded: ${ret.returnId} — ${ret.manufacturer} ${ret.model}`, "info");
  }

  if (btnClearReturn) {
    btnClearReturn.addEventListener("click", () => {
      state.selectedReturn = null;
      if (selectedReturnBanner) selectedReturnBanner.style.display = "none";
    });
  }

  function prefillForm(ret) {
    const set = (id, val) => {
      const el = document.getElementById(id);
      if (el && val !== undefined && val !== null) el.value = val;
    };
    set("inputReturnId", ret.returnId);
    set("inputCategory", ret.category);
    set("inputManufacturer", ret.manufacturer);
    set("inputModel", ret.model);
    set("inputSerial", ret.serialNumber);
    set("inputImei", ret.imei);
    set("inputPurchaseDate", ret.purchaseDate);
    set("inputReturnDate", ret.returnDate);
    set("inputSellerChannel", ret.sellerChannel);
    set("inputPurchasePrice", ret.claimedPurchasePrice);
    set("inputEstRepairCost", ret.estimatedRepairCost);
    set("inputEstResaleValue", ret.estimatedResaleValue);
    set("inputEstPartsValue", ret.estimatedPartsValue);
    set("inputCustomerSymptoms", ret.customerSymptoms);

    // Checkboxes
    const setChk = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.checked = Boolean(val);
    };
    setChk("chkInvoice", ret.invoiceAvailable);
    setChk("chkWarrantyClaimed", ret.warrantyClaimed);
    setChk("chkLiquidDamage", ret.liquidDamage);
    setChk("chkImpactDamage", ret.impactDamage);
    setChk("chkMissingParts", ret.missingComponents);
    setChk("chkTamper", ret.tamperingEvidence);
    setChk("chkBattery", ret.batteryIssue);
    setChk("chkScreen", ret.screenIssue);
    setChk("chkCharging", ret.chargingIssue);
    setChk("chkMotherboard", ret.motherboardIssue);
    setChk("chkSoftware", ret.softwareIssue);
    setChk("chkCamera", ret.cameraIssue);
    setChk("chkLabelInconsistency", ret.labelInconsistency);

    // Screen & body selects
    set("selectScreenCondition", ret.screenCondition);
    set("selectBodyCondition", ret.bodyCondition);

    // Powers on three-way
    setPowersOn(ret.powersOn);

    // Tamper seals
    const sealYes = document.getElementById("sealYes");
    const sealNo = document.getElementById("sealNo");
    if (ret.tamperSealsIntact === true && sealYes) {
      sealYes.classList.add("selected-yes");
      if (sealNo) sealNo.classList.remove("selected-no");
    } else if (ret.tamperSealsIntact === false && sealNo) {
      sealNo.classList.add("selected-no");
      if (sealYes) sealYes.classList.remove("selected-yes");
    }
  }

  // ─── Three-way powers-on buttons ─────────────────────────────────────────
  const poYes = document.getElementById("poYes");
  const poNo = document.getElementById("poNo");
  const poUnk = document.getElementById("poUnk");

  function setPowersOn(val) {
    state.powersOn = val;
    [poYes, poNo, poUnk].forEach(b => {
      if (b) b.className = "three-way-btn";
    });
    if (val === true && poYes) poYes.className = "three-way-btn selected-yes";
    else if (val === false && poNo) poNo.className = "three-way-btn selected-no";
    else if (val === null && poUnk) poUnk.className = "three-way-btn selected-unk";
  }

  if (poYes) poYes.addEventListener("click", () => setPowersOn(true));
  if (poNo) poNo.addEventListener("click", () => setPowersOn(false));
  if (poUnk) poUnk.addEventListener("click", () => setPowersOn(null));

  // ─── Tamper seal two-way ─────────────────────────────────────────────────
  const sealYes = document.getElementById("sealYes");
  const sealNo = document.getElementById("sealNo");
  if (sealYes) sealYes.addEventListener("click", () => {
    sealYes.className = "three-way-btn selected-yes";
    if (sealNo) sealNo.className = "three-way-btn";
  });
  if (sealNo) sealNo.addEventListener("click", () => {
    sealNo.className = "three-way-btn selected-no";
    if (sealYes) sealYes.className = "three-way-btn";
  });

  // ─── Image Upload ─────────────────────────────────────────────────────────
  const imgDropzone = document.getElementById("daImageDropzone");
  const imgFileInput = document.getElementById("daFileInput");
  const imgPreviewStrip = document.getElementById("daImagePreviewStrip");

  if (imgDropzone) {
    imgDropzone.addEventListener("click", () => imgFileInput && imgFileInput.click());
    ["dragenter", "dragover"].forEach(ev =>
      imgDropzone.addEventListener(ev, e => { e.preventDefault(); imgDropzone.classList.add("drag-over"); }));
    ["dragleave", "drop"].forEach(ev =>
      imgDropzone.addEventListener(ev, e => { e.preventDefault(); imgDropzone.classList.remove("drag-over"); }));
    imgDropzone.addEventListener("drop", e => {
      const files = Array.from(e.dataTransfer.files || []);
      files.forEach(f => processImage(f));
    });
  }

  if (imgFileInput) {
    imgFileInput.addEventListener("change", e => {
      Array.from(e.target.files || []).forEach(f => processImage(f));
    });
  }

  function processImage(file) {
    if (!file.type.startsWith("image/")) {
      toast("Please select an image file (PNG, JPG, WEBP).", "error");
      return;
    }
    if (file.size > 8 * 1024 * 1024) {
      toast("Image exceeds 8MB limit.", "error");
      return;
    }
    const reader = new FileReader();
    reader.onload = e => {
      const obj = { fileName: file.name, dataUrl: e.target.result, size: file.size };
      state.uploadedImages.push(obj);
      renderImagePreviews();
    };
    reader.readAsDataURL(file);
  }

  function renderImagePreviews() {
    if (!imgPreviewStrip) return;
    imgPreviewStrip.innerHTML = "";
    state.uploadedImages.forEach((img, idx) => {
      const wrap = document.createElement("div");
      wrap.style.cssText = "position:relative;display:inline-block;";
      const thumb = document.createElement("img");
      thumb.src = img.dataUrl;
      thumb.className = "img-preview-thumb";
      thumb.title = img.fileName;
      const rm = document.createElement("button");
      rm.type = "button";
      rm.textContent = "×";
      rm.style.cssText = "position:absolute;top:-4px;right:-4px;width:18px;height:18px;border-radius:50%;background:var(--rose-500);color:#fff;border:none;cursor:pointer;font-size:0.8rem;line-height:1;";
      rm.addEventListener("click", () => {
        state.uploadedImages.splice(idx, 1);
        renderImagePreviews();
      });
      wrap.appendChild(thumb);
      wrap.appendChild(rm);
      imgPreviewStrip.appendChild(wrap);
    });
    if (state.uploadedImages.length > 0 && imgDropzone) {
      imgDropzone.innerHTML = `<div style="font-size:0.85rem;color:var(--text-secondary);">${state.uploadedImages.length} image(s) added · Click to add more</div>`;
    }
  }

  // ─── Form validation ────────────────────────────────────────────────────
  function clearError(id) {
    const el = document.getElementById(id);
    if (el) { el.textContent = ""; el.style.display = "none"; }
    const input = document.getElementById(id.replace("err", "input").replace("Err", ""));
    if (input) input.classList.remove("is-invalid");
  }

  function setError(inputId, errId, msg) {
    const inp = document.getElementById(inputId);
    if (inp) inp.classList.add("is-invalid");
    const err = document.getElementById(errId);
    if (err) { err.textContent = msg; err.style.display = "flex"; }
  }

  function validateForm() {
    let valid = true;
    const returnId = (document.getElementById("inputReturnId") || {}).value || "";
    if (!returnId.trim()) {
      setError("inputReturnId", "errReturnId", "Return ID is required.");
      valid = false;
    } else clearError("errReturnId");

    const category = (document.getElementById("inputCategory") || {}).value || "";
    if (!category.trim()) {
      setError("inputCategory", "errCategory", "Product category is required.");
      valid = false;
    } else clearError("errCategory");

    const purchaseDate = (document.getElementById("inputPurchaseDate") || {}).value || "";
    if (purchaseDate) {
      const d = new Date(purchaseDate);
      if (isNaN(d) || d > new Date()) {
        setError("inputPurchaseDate", "errPurchaseDate", "Purchase date must be valid and not in the future.");
        valid = false;
      } else clearError("errPurchaseDate");
    }

    return valid;
  }

  // ─── Submit ────────────────────────────────────────────────────────────
  function buildPayload() {
    const g = id => (document.getElementById(id) || {}).value || "";
    const chk = id => !!(document.getElementById(id) || {}).checked;
    const sealYesEl = document.getElementById("sealYes");
    const sealNoEl = document.getElementById("sealNo");
    let tamperSealsIntact = null;
    if (sealYesEl && sealYesEl.classList.contains("selected-yes")) tamperSealsIntact = true;
    if (sealNoEl && sealNoEl.classList.contains("selected-no")) tamperSealsIntact = false;

    const priceRaw = g("inputPurchasePrice");
    const repairRaw = g("inputEstRepairCost");
    const resaleRaw = g("inputEstResaleValue");
    const partsRaw = g("inputEstPartsValue");

    return {
      returnId: g("inputReturnId").trim(),
      category: g("inputCategory").trim(),
      manufacturer: g("inputManufacturer").trim(),
      model: g("inputModel").trim(),
      serialNumber: g("inputSerial").trim(),
      imei: g("inputImei").trim(),
      purchaseDate: g("inputPurchaseDate"),
      returnDate: g("inputReturnDate"),
      sellerChannel: g("inputSellerChannel").trim(),
      claimedPurchasePrice: priceRaw ? parseFloat(priceRaw) : null,
      invoiceAvailable: chk("chkInvoice"),
      warrantyClaimed: chk("chkWarrantyClaimed"),
      serialOnLabel: g("inputSerial").trim(),
      serialOnDevice: g("inputSerialOnDevice").trim(),
      labelInconsistency: chk("chkLabelInconsistency"),
      packagingCondition: g("inputPackagingNote").trim(),
      // Condition fields
      powersOn: state.powersOn,
      screenCondition: g("selectScreenCondition"),
      bodyCondition: g("selectBodyCondition"),
      liquidDamage: chk("chkLiquidDamage"),
      impactDamage: chk("chkImpactDamage"),
      missingComponents: chk("chkMissingParts"),
      tamperingEvidence: chk("chkTamper"),
      tamperSealsIntact,
      // Defects
      batteryIssue: chk("chkBattery"),
      screenIssue: chk("chkScreen"),
      chargingIssue: chk("chkCharging"),
      motherboardIssue: chk("chkMotherboard"),
      cameraIssue: chk("chkCamera"),
      softwareIssue: chk("chkSoftware"),
      customerSymptoms: g("inputCustomerSymptoms").trim(),
      // Economic
      estimatedRepairCost: repairRaw ? parseFloat(repairRaw) : 0,
      estimatedResaleValue: resaleRaw ? parseFloat(resaleRaw) : 0,
      estimatedPartsValue: partsRaw ? parseFloat(partsRaw) : 0,
      estimatedLaborCost: 0,
      estimatedRepairHours: 0,
      // Images (file names only — no actual upload in demo)
      images: state.uploadedImages.map(i => i.fileName)
    };
  }

  if (btnSubmit) {
    btnSubmit.addEventListener("click", async () => {
      if (!validateForm()) {
        showAlert("Please fix the highlighted fields before submitting.", "error");
        return;
      }
      clearAlert();
      setSubmitting(true);

      const payload = buildPayload();
      try {
        const result = await window.deviceAssessmentApi.submitAssessment(payload);
        state.result = result;
        setSubmitting(false);
        renderResult(result);
        // Switch to results tab
        tabBtns.forEach(b => b.classList.remove("active"));
        tabViews.forEach(v => v.style.display = "none");
        const rTab = document.querySelector('[data-tab="daTabResults"]');
        if (rTab) rTab.classList.add("active");
        const rView = document.getElementById("daTabResults");
        if (rView) rView.style.display = "block";
        toast(result.isMock ? "Assessment via Mock Service" : `Assessment ID: ${result.assessmentId}`, "success");
      } catch (err) {
        setSubmitting(false);
        const msg = err.message || "Submission failed.";
        showAlert(msg, "error");
        toast(msg, "error");
      }
    });
  }

  function setSubmitting(active) {
    if (!btnSubmit) return;
    btnSubmit.disabled = active;
    btnSubmit.innerHTML = active
      ? `<span class="spinner"></span><span>Analysing Device...</span>`
      : `<span>Run Full Assessment</span><span>➔</span>`;
  }

  function showAlert(msg, type = "error") {
    if (!submitAlertBanner) return;
    submitAlertBanner.className = `alert-banner alert-${type}`;
    submitAlertBanner.innerHTML = `<span>${type === "error" ? "⚠️" : "ℹ️"}</span><span>${msg}</span>`;
    submitAlertBanner.style.display = "flex";
  }

  function clearAlert() {
    if (!submitAlertBanner) return;
    submitAlertBanner.style.display = "none";
  }

  // ─── Render Results ───────────────────────────────────────────────────────
  function scoreClass(v) {
    if (v >= 70) return "score-high";
    if (v >= 40) return "score-med";
    return "score-low";
  }

  function riskClass(v) {
    if (v <= 15) return "score-high";
    if (v <= 40) return "score-med";
    return "score-low";
  }

  function renderGauge(el, value, type = "score") {
    if (!el) return;
    const cls = type === "risk" ? riskClass(value) : scoreClass(value);
    el.className = `score-gauge-card ${cls}`;
    el.querySelector(".score-gauge-value").textContent = value;
    el.querySelector(".score-gauge-fill").style.width = `${value}%`;
  }

  function authBadgeClass(status) {
    return {
      "likely_genuine": "auth-genuine",
      "suspicious": "auth-suspicious",
      "likely_counterfeit": "auth-counterfeit",
      "unknown": "auth-unknown"
    }[status] || "auth-unknown";
  }

  function authLabel(status) {
    return {
      "likely_genuine": "✅ Likely Genuine",
      "suspicious": "⚠️ Suspicious",
      "likely_counterfeit": "🚨 Likely Counterfeit",
      "unknown": "❓ Unknown"
    }[status] || "Unknown";
  }

  function warrantyLabel(status) {
    return {
      "eligible": "✅ Eligible",
      "not_eligible": "❌ Not Eligible",
      "pending_verification": "⏳ Pending Verification",
      "insufficient_information": "❓ Insufficient Information",
      "manual_review": "🔍 Manual Review"
    }[status] || status;
  }

  function renderResult(r) {
    if (resultSkeleton) resultSkeleton.style.display = "none";
    if (resultView) resultView.style.display = "block";

    if (assessmentIdEl) assessmentIdEl.textContent = r.assessmentId || "—";
    if (backendModeEl) {
      backendModeEl.className = r.isMock ? "api-status-badge mock-mode" : "api-status-badge";
      backendModeEl.innerHTML = r.isMock
        ? `<span class="status-dot"></span><span>Temporary Mock Service</span>`
        : `<span class="status-dot"></span><span>Live API (/api/device-assessment)</span>`;
    }

    renderGauge(gCondition, r.conditionScore || 0, "score");
    renderGauge(gRepair, r.repairabilityScore || 0, "score");
    renderGauge(gConfidence, r.confidenceScore || 0, "score");
    renderGauge(gRisk, r.authenticityRiskScore || 0, "risk");

    if (authBadge) {
      authBadge.className = `auth-badge ${authBadgeClass(r.authenticityStatus)}`;
      authBadge.textContent = authLabel(r.authenticityStatus);
    }
    if (warrantyBadge) {
      const wc = r.warrantyStatus === "eligible" ? "var(--emerald-400)" :
        r.warrantyStatus === "not_eligible" ? "var(--rose-400)" :
          r.warrantyStatus === "pending_verification" ? "var(--amber-400)" : "var(--cyan-400)";
      warrantyBadge.style.color = wc;
      warrantyBadge.textContent = warrantyLabel(r.warrantyStatus);
    }
    if (dispositionBadge) dispositionBadge.textContent = r.preliminaryDisposition || "—";

    if (manualReviewBox) {
      manualReviewBox.style.display = r.manualReviewRequired ? "block" : "none";
      if (manualReviewReasons && r.manualReviewReasons) {
        manualReviewReasons.innerHTML = r.manualReviewReasons.map(
          rr => `<li>${esc(rr)}</li>`
        ).join("");
      }
    }

    // Evidence panels
    const ev = r.evidence || {};

    if (evidenceAuthBody && ev.authenticity) {
      const a = ev.authenticity;
      const inds = (a.indicators || []).map(i => {
        const cls = `indicator-${(i.impact || "neutral").replace(" ", "_")}`;
        return `<div class="indicator-item ${cls}"><span>${i.signal}</span></div>`;
      }).join("") || "<div style='color:var(--text-muted);font-size:0.82rem;'>No indicators recorded.</div>";

      const miss = (a.missing_evidence || []).map(m => `<li>${esc(m)}</li>`).join("");

      evidenceAuthBody.innerHTML = `
        <div class="indicator-list">${inds}</div>
        ${miss ? `<div class="missing-info-box" style="margin-top:0.75rem;"><strong>Missing Evidence:</strong><ul style="margin-top:0.35rem;padding-left:1rem;">${miss}</ul></div>` : ""}
        <div class="disclaimer-box">${esc(a.disclaimer || "")}</div>
      `;
    }

    if (evidenceCondBody && ev.condition) {
      const c = ev.condition;
      const defects = (c.observed_defects || r.observedDefects || []).map(d => `<li>${esc(d)}</li>`).join("");
      const lims = (c.limitations || []).map(l => `<li>${esc(l)}</li>`).join("");
      const insp = (c.recommended_inspection || []).map(i => `<li>${esc(i)}</li>`).join("");
      evidenceCondBody.innerHTML = `
        ${defects ? `<strong style="font-size:0.82rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:.04em;">Observed Defects</strong><ul style="padding-left:1rem;margin-top:.4rem;margin-bottom:.85rem;font-size:.85rem;">${defects}</ul>` : ""}
        ${lims ? `<strong style="font-size:0.82rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:.04em;">Limitations</strong><ul style="padding-left:1rem;margin-top:.4rem;margin-bottom:.85rem;font-size:.85rem;">${lims}</ul>` : ""}
        ${insp ? `<strong style="font-size:0.82rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:.04em;">Recommended Inspection</strong><ul style="padding-left:1rem;margin-top:.4rem;font-size:.85rem;">${insp}</ul>` : ""}
        <div class="disclaimer-box">${esc(c.disclaimer || "")}</div>
      `;
    }

    if (evidenceWarrBody && ev.warranty) {
      const w = ev.warranty;
      const evUsed = (w.evidence_used || []).map(e => `<li>${esc(e)}</li>`).join("");
      const miss = (w.missing_information || []).map(m => `<li>${esc(m)}</li>`).join("");
      const excl = (w.exclusion_reasons || []).map(x => `<li>${esc(x)}</li>`).join("");
      evidenceWarrBody.innerHTML = `
        ${evUsed ? `<strong style="font-size:0.82rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:.04em;">Evidence Used</strong><ul style="padding-left:1rem;margin-top:.4rem;margin-bottom:.85rem;font-size:.85rem;">${evUsed}</ul>` : ""}
        ${excl ? `<strong style="font-size:0.82rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:.04em;">Exclusion Triggers</strong><ul style="padding-left:1rem;margin-top:.4rem;margin-bottom:.85rem;font-size:.85rem;color:var(--rose-400);">${excl}</ul>` : ""}
        ${miss ? `<div class="missing-info-box"><strong>Missing Information:</strong><ul style="margin-top:.35rem;padding-left:1rem;">${miss}</ul></div>` : ""}
        <div class="disclaimer-box">${esc(w.disclaimer || "")}</div>
      `;
    }
  }

  // Evidence panel collapse/expand
  document.querySelectorAll(".evidence-panel-header").forEach(hdr => {
    hdr.addEventListener("click", () => {
      const panel = hdr.closest(".evidence-panel");
      panel.classList.toggle("open");
    });
  });

  if (btnNewAssessment) {
    btnNewAssessment.addEventListener("click", () => {
      if (resultView) resultView.style.display = "none";
      state.result = null;
      // Go to questionnaire tab
      tabBtns.forEach(b => b.classList.remove("active"));
      tabViews.forEach(v => v.style.display = "none");
      const qTab = document.querySelector('[data-tab="daTabQuestionnaire"]');
      if (qTab) qTab.classList.add("active");
      const qView = document.getElementById("daTabQuestionnaire");
      if (qView) qView.style.display = "block";
    });
  }

  function esc(s) {
    return String(s || "")
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
});
