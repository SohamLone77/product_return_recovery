/**
 * Multi-Step Wizard Engine
 * Handles step navigation, forward validation gates, history, and progress bar updates.
 */

class AssessmentWizard {
  constructor(options = {}) {
    this.currentStep = 1;
    this.totalSteps = 5;
    this.stepNames = [
      "Product Condition",
      "Defect Information",
      "Warranty Details",
      "Review & Submit",
      "Confirmation"
    ];

    this.onStepChange = options.onStepChange || (() => {});
    this.validators = options.validators || {};
    this.formData = {};

    this.initDOM();
  }

  initDOM() {
    this.stepperItems = document.querySelectorAll('.step-indicator-item');
    this.stepSections = document.querySelectorAll('.step-section');
    this.progressFill = document.querySelector('.stepper-progress-fill');
    this.btnPrev = document.getElementById('btnWizardPrev');
    this.btnNext = document.getElementById('btnWizardNext');
    this.btnSubmit = document.getElementById('btnWizardSubmit');
    this.alertBanner = document.getElementById('wizardAlertBanner');

    // Attach stepper tab click listeners (only allowed to visit previous completed steps)
    this.stepperItems.forEach((btn) => {
      btn.addEventListener('click', () => {
        const targetStep = parseInt(btn.dataset.step, 10);
        if (targetStep < this.currentStep) {
          this.goToStep(targetStep);
        }
      });
    });

    if (this.btnPrev) {
      this.btnPrev.addEventListener('click', () => this.previous());
    }

    if (this.btnNext) {
      this.btnNext.addEventListener('click', () => this.next());
    }

    this.updateUI();
  }

  goToStep(stepNumber) {
    if (stepNumber < 1 || stepNumber > this.totalSteps) return;
    this.currentStep = stepNumber;
    this.clearAlert();
    this.updateUI();
    this.onStepChange(this.currentStep);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  next() {
    // Validate current step before advancing
    if (this.validators[this.currentStep]) {
      const isValid = this.validators[this.currentStep]();
      if (!isValid) {
        return false;
      }
    }

    if (this.currentStep < this.totalSteps) {
      this.goToStep(this.currentStep + 1);
      return true;
    }
    return false;
  }

  previous() {
    if (this.currentStep > 1 && this.currentStep < 5) {
      this.goToStep(this.currentStep - 1);
    }
  }

  reset() {
    this.currentStep = 1;
    this.formData = {};
    this.clearAlert();
    this.updateUI();
    this.onStepChange(1);
  }

  showAlert(message, type = 'error') {
    if (!this.alertBanner) return;
    this.alertBanner.className = `alert-banner alert-${type}`;
    this.alertBanner.innerHTML = `
      <span class="alert-icon">${type === 'error' ? '⚠️' : 'ℹ️'}</span>
      <span class="alert-text">${message}</span>
    `;
    this.alertBanner.style.display = 'flex';
  }

  clearAlert() {
    if (!this.alertBanner) return;
    this.alertBanner.style.display = 'none';
    this.alertBanner.innerHTML = '';
  }

  updateUI() {
    // 1. Update Stepper Tabs
    this.stepperItems.forEach((item) => {
      const step = parseInt(item.dataset.step, 10);
      item.classList.remove('active', 'completed');
      if (step === this.currentStep) {
        item.classList.add('active');
        item.removeAttribute('disabled');
      } else if (step < this.currentStep) {
        item.classList.add('completed');
        item.removeAttribute('disabled');
      } else {
        item.setAttribute('disabled', 'true');
      }
    });

    // 2. Update Progress Bar
    if (this.progressFill) {
      const percentage = ((this.currentStep - 1) / (this.totalSteps - 1)) * 100;
      this.progressFill.style.width = `${Math.max(percentage, 5)}%`;
    }

    // 3. Update Step Sections
    this.stepSections.forEach((section) => {
      const step = parseInt(section.dataset.step, 10);
      if (step === this.currentStep) {
        section.classList.add('active');
      } else {
        section.classList.remove('active');
      }
    });

    // 4. Update Footer Buttons
    if (this.btnPrev) {
      this.btnPrev.style.display = (this.currentStep > 1 && this.currentStep < 5) ? 'inline-flex' : 'none';
    }

    if (this.btnNext) {
      this.btnNext.style.display = (this.currentStep < 4) ? 'inline-flex' : 'none';
    }

    if (this.btnSubmit) {
      this.btnSubmit.style.display = (this.currentStep === 4) ? 'inline-flex' : 'none';
    }

    // Hide footer completely on confirmation step (Step 5)
    const footer = document.querySelector('.wizard-footer');
    if (footer) {
      footer.style.display = (this.currentStep === 5) ? 'none' : 'flex';
    }
  }
}

window.AssessmentWizard = AssessmentWizard;
