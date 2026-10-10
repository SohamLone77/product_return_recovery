/**
 * Step 5: Confirmation View Component
 * Displays finalized assessment receipt, unique assessment ID,
 * preliminary disposition routing, and actions.
 */

class ConfirmationStep {
  constructor(options = {}) {
    this.onReset = options.onReset || (() => {});
    this.initDOM();
  }

  initDOM() {
    this.idDisplay = document.getElementById('confirmAssessmentId');
    this.btnCopyId = document.getElementById('btnCopyAssessmentId');
    this.backendModeBadge = document.getElementById('confirmBackendModeBadge');
    this.dispositionRoute = document.getElementById('confirmDispositionRoute');
    this.recoveryRatio = document.getElementById('confirmRecoveryRatio');
    this.dispositionAction = document.getElementById('confirmDispositionAction');
    this.timestampDisplay = document.getElementById('confirmTimestamp');

    this.btnNewReturn = document.getElementById('btnConfirmNewReturn');
    this.btnPrint = document.getElementById('btnConfirmPrint');

    if (this.btnCopyId) {
      this.btnCopyId.addEventListener('click', () => {
        const text = this.idDisplay ? this.idDisplay.textContent : '';
        if (text && text !== '—') {
          navigator.clipboard.writeText(text).then(() => {
            if (window.showToast) {
              window.showToast('Assessment ID copied to clipboard!', 'info');
            }
          });
        }
      });
    }

    if (this.btnNewReturn) {
      this.btnNewReturn.addEventListener('click', () => {
        this.onReset();
      });
    }

    if (this.btnPrint) {
      this.btnPrint.addEventListener('click', () => {
        window.print();
      });
    }
  }

  render(result) {
    if (!result) return;

    if (this.idDisplay) {
      this.idDisplay.textContent = result.assessmentId || 'ASM-RECORDED';
    }

    if (this.timestampDisplay) {
      this.timestampDisplay.textContent = new Date(result.timestamp || Date.now()).toLocaleString();
    }

    // Backend Source Indicator
    if (this.backendModeBadge) {
      if (result.isMock) {
        this.backendModeBadge.className = 'api-status-badge mock-mode';
        this.backendModeBadge.innerHTML = `
          <span class="status-dot"></span>
          <span>Temporary Mock Service (Person 3 Interface)</span>
        `;
      } else {
        this.backendModeBadge.className = 'api-status-badge';
        this.backendModeBadge.innerHTML = `
          <span class="status-dot"></span>
          <span>Live API (POST /assessment)</span>
        `;
      }
    }

    // Preliminary Disposition
    const disp = result.preliminaryDisposition || {};
    if (this.dispositionRoute) {
      this.dispositionRoute.textContent = disp.route || 'ROUTED_FOR_INSPECTION';
    }

    if (this.recoveryRatio) {
      const ratio = disp.estimatedRecoveryRatio ? Math.round(disp.estimatedRecoveryRatio * 100) : 50;
      this.recoveryRatio.textContent = `${ratio}% Value Retention`;
    }

    if (this.dispositionAction) {
      this.dispositionAction.textContent = disp.recommendedAction || 'Stage product for warehouse return intake verification.';
    }
  }
}

window.ConfirmationStep = ConfirmationStep;
