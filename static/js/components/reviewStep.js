/**
 * Step 4: Review & Submit Component
 * Displays comprehensive summary of entered data with quick edit jumps.
 * Coordinates with assessmentApi to submit to backend or fallback mock.
 */

class ReviewStep {
  constructor(formState, wizard) {
    this.formState = formState;
    this.wizard = wizard;
    this.initDOM();
  }

  initDOM() {
    this.reviewProductCard = document.getElementById('reviewProductSection');
    this.reviewDefectCard = document.getElementById('reviewDefectSection');
    this.reviewWarrantyCard = document.getElementById('reviewWarrantySection');
    this.reviewAckCheckbox = document.getElementById('checkboxReviewAck');
    this.errReviewAck = document.getElementById('errReviewAck');

    // Quick Jump Edit Buttons
    document.querySelectorAll('.review-edit-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const targetStep = parseInt(btn.dataset.targetStep, 10);
        if (targetStep) {
          this.wizard.goToStep(targetStep);
        }
      });
    });

    if (this.reviewAckCheckbox) {
      this.reviewAckCheckbox.addEventListener('change', () => {
        if (this.reviewAckCheckbox.checked) {
          this.clearError(this.errReviewAck);
        }
      });
    }
  }

  renderSummary() {
    // 1. Product Summary
    if (this.reviewProductCard) {
      this.reviewProductCard.innerHTML = `
        <div class="review-dl">
          <div class="review-dt">Product SKU / ID:</div>
          <div class="review-dd"><code style="color: var(--amber-400); font-family: var(--font-mono);">${this.escape(this.formState.productId || '—')}</code></div>

          <div class="review-dt">Product Name:</div>
          <div class="review-dd">${this.escape(this.formState.productName || 'Unspecified Model')}</div>

          <div class="review-dt">Category:</div>
          <div class="review-dd">${this.escape(this.formState.category || '—')}</div>

          <div class="review-dt">Physical Condition:</div>
          <div class="review-dd">
            <span class="badge-module" style="background: rgba(245, 158, 11, 0.15);">${this.escape(this.formState.condition || '—')}</span>
          </div>
        </div>
      `;
    }

    // 2. Defect Summary
    if (this.reviewDefectCard) {
      const hasImage = Boolean(this.formState.damageImage);
      const imageSnippet = hasImage
        ? `<div style="margin-top: 0.75rem; display: flex; align-items: center; gap: 0.5rem; font-size: 0.8rem; color: var(--cyan-400);">
             <span>📷 Damage Photo: ${this.escape(this.formState.damageImage.fileName)} (${(this.formState.damageImage.fileSize / 1024).toFixed(0)} KB)</span>
           </div>`
        : '';

      this.reviewDefectCard.innerHTML = `
        <div class="review-dl">
          <div class="review-dt">Defect Category:</div>
          <div class="review-dd"><strong>${this.escape(this.formState.defectCategory || 'No defect')}</strong></div>

          <div class="review-dt">Visible Damage:</div>
          <div class="review-dd">${this.formState.visibleDamage ? '<span style="color: var(--rose-400);">Yes</span>' : '<span style="color: var(--emerald-400);">No</span>'}</div>

          <div class="review-dt">Description:</div>
          <div class="review-dd">${this.escape(this.formState.defectDescription || 'None provided')}</div>
        </div>
        ${imageSnippet}
      `;
    }

    // 3. Warranty Summary
    if (this.reviewWarrantyCard) {
      this.reviewWarrantyCard.innerHTML = `
        <div class="review-dl">
          <div class="review-dt">Warranty Status:</div>
          <div class="review-dd">${this.escape(this.formState.warrantyStatus || '—')}</div>

          <div class="review-dt">Purchase Date:</div>
          <div class="review-dd">${this.escape(this.formState.purchaseDate || '—')}</div>

          <div class="review-dt">Warranty Expiry:</div>
          <div class="review-dd">${this.escape(this.formState.warrantyExpiryDate || 'Not specified / N/A')}</div>

          <div class="review-dt">Proof of Purchase:</div>
          <div class="review-dd">${this.escape(this.formState.proofOfPurchase || 'None entered')}</div>
        </div>
      `;
    }
  }

  validate() {
    if (this.reviewAckCheckbox && !this.reviewAckCheckbox.checked) {
      this.setError(this.errReviewAck, 'Please confirm the assessment information accuracy to proceed.');
      return false;
    }
    this.clearError(this.errReviewAck);
    return true;
  }

  setError(errorEl, message) {
    if (errorEl) {
      errorEl.textContent = message;
      errorEl.style.display = 'flex';
    }
  }

  clearError(errorEl) {
    if (errorEl) {
      errorEl.textContent = '';
      errorEl.style.display = 'none';
    }
  }

  escape(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
}

window.ReviewStep = ReviewStep;
