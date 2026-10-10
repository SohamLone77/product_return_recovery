/**
 * Intelligent Product Returns & Recovery Engine
 * Person 2: Return Assessment Module - Main App Controller
 */

document.addEventListener('DOMContentLoaded', () => {
  // Global form state object preserved throughout lifecycle
  const formState = {
    productId: '',
    productName: '',
    category: '',
    condition: '',
    defectCategory: '',
    defectDescription: '',
    visibleDamage: false,
    damageImage: null,
    warrantyStatus: '',
    purchaseDate: '',
    warrantyExpiryDate: null,
    proofOfPurchase: ''
  };

  // Toast System
  const toastContainer = document.getElementById('toastContainer');
  window.showToast = function (message, type = 'info') {
    if (!toastContainer) return;
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    const icon = type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️';
    toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;
    toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  };

  // View Switcher (Landing vs Wizard)
  const landingView = document.getElementById('landingView');
  const wizardView = document.getElementById('wizardView');
  const btnStartNewReturn = document.getElementById('btnStartNewReturn');
  const btnHeroNewReturn = document.getElementById('btnHeroNewReturn');
  const btnBackToDashboard = document.getElementById('btnBackToDashboard');
  const btnNavBrand = document.getElementById('navBrandLink');

  function showWizard() {
    if (landingView) landingView.style.display = 'none';
    if (wizardView) {
      wizardView.style.display = 'block';
      wizardView.classList.add('active');
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function showLanding() {
    if (wizardView) {
      wizardView.style.display = 'none';
      wizardView.classList.remove('active');
    }
    if (landingView) landingView.style.display = 'block';
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  if (btnStartNewReturn) btnStartNewReturn.addEventListener('click', showWizard);
  if (btnHeroNewReturn) btnHeroNewReturn.addEventListener('click', showWizard);
  if (btnBackToDashboard) btnBackToDashboard.addEventListener('click', showLanding);
  if (btnNavBrand) {
    btnNavBrand.addEventListener('click', (e) => {
      e.preventDefault();
      showLanding();
    });
  }

  // Header API Status Badge
  const headerApiBadge = document.getElementById('headerApiBadge');
  async function refreshBackendStatus() {
    if (!headerApiBadge || !window.assessmentApi) return;
    const health = await window.assessmentApi.checkBackendHealth();
    if (health.isLive) {
      headerApiBadge.className = 'api-status-badge';
      headerApiBadge.innerHTML = `<span class="status-dot"></span><span>Live Backend (Port 5001)</span>`;
      headerApiBadge.title = "Connected to live POST /assessment endpoint";
    } else {
      headerApiBadge.className = 'api-status-badge mock-mode';
      headerApiBadge.innerHTML = `<span class="status-dot"></span><span>Mock Service Ready</span>`;
      headerApiBadge.title = `Backend status: ${health.detail || 'Offline'}. Local Mock Assessment will handle submissions.`;
    }
  }

  // Run initial health check
  refreshBackendStatus();

  // Instantiate Steps
  const conditionStep = new ConditionStep(formState);
  const defectStep = new DefectStep(formState);
  const warrantyStep = new WarrantyStep(formState);

  let wizard = null;
  const reviewStep = new ReviewStep(formState, {
    goToStep: (s) => wizard && wizard.goToStep(s)
  });

  const confirmationStep = new ConfirmationStep({
    onReset: () => {
      resetAssessmentForm();
      showWizard();
    }
  });

  // Step validation definitions
  const stepValidators = {
    1: () => conditionStep.validate(),
    2: () => defectStep.validate(),
    3: () => warrantyStep.validate(),
    4: () => reviewStep.validate()
  };

  // Instantiate Wizard
  wizard = new AssessmentWizard({
    validators: stepValidators,
    onStepChange: (step) => {
      if (step === 4) {
        reviewStep.renderSummary();
      }
    }
  });

  // Wire Submission Action
  const btnSubmit = document.getElementById('btnWizardSubmit');
  if (btnSubmit) {
    btnSubmit.addEventListener('click', async () => {
      // Validate Review Step
      if (!reviewStep.validate()) {
        wizard.showAlert("Please confirm the verification checkbox to submit the assessment.");
        return;
      }

      // UI Submitting State
      setSubmittingState(true);
      wizard.clearAlert();

      try {
        const payload = {
          productId: formState.productId,
          productName: formState.productName,
          category: formState.category,
          condition: formState.condition,
          defectCategory: formState.defectCategory,
          defectDescription: formState.defectDescription,
          visibleDamage: formState.visibleDamage,
          damageImage: formState.damageImage,
          warrantyStatus: formState.warrantyStatus,
          purchaseDate: formState.purchaseDate,
          warrantyExpiryDate: formState.warrantyExpiryDate,
          proofOfPurchase: formState.proofOfPurchase
        };

        const result = await window.assessmentApi.submitAssessment(payload);

        // Success UI State
        setSubmittingState(false);
        confirmationStep.render(result);
        wizard.goToStep(5);

        const noticeMsg = result.isMock
          ? `Assessment recorded via Temporary Mock (${result.assessmentId})`
          : `Assessment recorded via Live Backend (${result.assessmentId})`;
        window.showToast(noticeMsg, 'success');

      } catch (err) {
        setSubmittingState(false);
        console.error("[App] Submission error:", err);

        let errorMsg = err.message || "Failed to submit product assessment. Please check your inputs and try again.";
        if (err.errors) {
          const detail = Object.values(err.errors).join(" • ");
          errorMsg = `${errorMsg}: ${detail}`;
        }

        wizard.showAlert(errorMsg, 'error');
        window.showToast(errorMsg, 'error');
      }
    });
  }

  function setSubmittingState(isSubmitting) {
    if (!btnSubmit) return;
    if (isSubmitting) {
      btnSubmit.disabled = true;
      btnSubmit.innerHTML = `<span class="spinner"></span><span>Submitting Assessment...</span>`;
      if (wizard.btnPrev) wizard.btnPrev.disabled = true;
    } else {
      btnSubmit.disabled = false;
      btnSubmit.innerHTML = `<span>Submit Assessment</span> <span>➔</span>`;
      if (wizard.btnPrev) wizard.btnPrev.disabled = false;
    }
  }

  function resetAssessmentForm() {
    // Reset state
    formState.productId = '';
    formState.productName = '';
    formState.category = '';
    formState.condition = '';
    formState.defectCategory = '';
    formState.defectDescription = '';
    formState.visibleDamage = false;
    formState.damageImage = null;
    formState.warrantyStatus = '';
    formState.purchaseDate = '';
    formState.warrantyExpiryDate = null;
    formState.proofOfPurchase = '';

    // Clear form inputs
    const form = document.getElementById('returnAssessmentForm');
    if (form) form.reset();

    // Reset visual card selections
    document.querySelectorAll('.condition-card, .defect-pill-card, .toggle-damage-pill, .warranty-option-card').forEach((el) => {
      el.classList.remove('selected');
    });

    // Remove previewed image
    defectStep.removeImage();

    // Reset wizard
    wizard.reset();
  }

  // Pre-fill Sample Return Data button (for quick QA and user convenience)
  const btnPrefillSample = document.getElementById('btnPrefillSample');
  if (btnPrefillSample) {
    btnPrefillSample.addEventListener('click', () => {
      showWizard();
      const randomId = 'SKU-LOGIX-' + Math.floor(1000 + Math.random() * 9000);
      formState.productId = randomId;
      formState.productName = 'Sony WH-1000XM5 Wireless Headphones';
      formState.category = 'Audio & Wearables';
      formState.condition = 'Damaged';
      formState.defectCategory = 'Charging or connectivity issue';
      formState.defectDescription = 'USB-C charging port pin bent; device intermittently drops Bluetooth pairing.';
      formState.visibleDamage = true;
      formState.warrantyStatus = 'In warranty';

      const pastDate = new Date();
      pastDate.setDate(pastDate.getDate() - 120);
      formState.purchaseDate = pastDate.toISOString().split('T')[0];

      const expiryDate = new Date();
      expiryDate.setDate(expiryDate.getDate() + 245);
      formState.warrantyExpiryDate = expiryDate.toISOString().split('T')[0];
      formState.proofOfPurchase = 'INV-AMZ-2026-98124';

      // Update UI inputs
      conditionStep.populateFromState();

      // Trigger condition notice
      window.dispatchEvent(new CustomEvent('conditionChanged', {
        detail: { condition: formState.condition }
      }));

      // Set defect radio
      const defectRadio = document.querySelector(`input[name="defectCategory"][value="${formState.defectCategory}"]`);
      if (defectRadio) {
        defectRadio.checked = true;
        document.querySelectorAll('.defect-pill-card').forEach(c => c.classList.remove('selected'));
        const parent = defectRadio.closest('.defect-pill-card');
        if (parent) parent.classList.add('selected');
      }

      if (defectStep.defectDescTextarea) {
        defectStep.defectDescTextarea.value = formState.defectDescription;
        if (defectStep.charCountEl) defectStep.charCountEl.textContent = `${formState.defectDescription.length}/500`;
      }

      const damageYesRadio = document.querySelector('input[name="visibleDamage"][value="yes"]');
      if (damageYesRadio) {
        damageYesRadio.checked = true;
        document.querySelectorAll('.toggle-damage-pill').forEach(p => p.classList.remove('selected'));
        const parent = damageYesRadio.closest('.toggle-damage-pill');
        if (parent) parent.classList.add('selected');
      }

      const warrantyRadio = document.querySelector(`input[name="warrantyStatus"][value="${formState.warrantyStatus}"]`);
      if (warrantyRadio) {
        warrantyRadio.checked = true;
        document.querySelectorAll('.warranty-option-card').forEach(w => w.classList.remove('selected'));
        const parent = warrantyRadio.closest('.warranty-option-card');
        if (parent) parent.classList.add('selected');
      }

      if (warrantyStep.purchaseDateInput) warrantyStep.purchaseDateInput.value = formState.purchaseDate;
      if (warrantyStep.expiryDateInput) warrantyStep.expiryDateInput.value = formState.warrantyExpiryDate;
      if (warrantyStep.proofInput) warrantyStep.proofInput.value = formState.proofOfPurchase;

      window.showToast("Pre-filled sample assessment data for testing!", 'info');
    });
  }
});
