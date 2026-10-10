/**
 * Step 3: Warranty Information Component
 * Warranty Status, Purchase Date, Warranty Expiry Date, and Proof of Purchase.
 * Validates date ranges (no future purchase date, expiry date >= purchase date).
 */

class WarrantyStep {
  constructor(formState) {
    this.formState = formState;
    this.initDOM();
  }

  initDOM() {
    this.warrantyCards = document.querySelectorAll('.warranty-option-card');
    this.purchaseDateInput = document.getElementById('inputPurchaseDate');
    this.expiryDateInput = document.getElementById('inputWarrantyExpiryDate');
    this.proofInput = document.getElementById('inputProofOfPurchase');

    this.errWarrantyStatus = document.getElementById('errWarrantyStatus');
    this.errPurchaseDate = document.getElementById('errPurchaseDate');
    this.errExpiryDate = document.getElementById('errExpiryDate');

    // Restrict max purchase date to today
    const todayStr = new Date().toISOString().split('T')[0];
    if (this.purchaseDateInput) {
      this.purchaseDateInput.max = todayStr;
      this.purchaseDateInput.addEventListener('input', () => {
        this.formState.purchaseDate = this.purchaseDateInput.value;
        this.validatePurchaseDate();
        if (this.expiryDateInput && this.expiryDateInput.value) {
          this.validateExpiryDate();
        }
      });
      this.purchaseDateInput.addEventListener('blur', () => this.validatePurchaseDate());
    }

    if (this.expiryDateInput) {
      this.expiryDateInput.addEventListener('input', () => {
        this.formState.warrantyExpiryDate = this.expiryDateInput.value;
        this.validateExpiryDate();
      });
      this.expiryDateInput.addEventListener('blur', () => this.validateExpiryDate());
    }

    if (this.proofInput) {
      this.proofInput.addEventListener('input', () => {
        this.formState.proofOfPurchase = this.proofInput.value.trim();
      });
    }

    // Warranty Option Cards Selection
    this.warrantyCards.forEach((card) => {
      card.addEventListener('click', () => {
        const radio = card.querySelector('input[type="radio"]');
        if (radio) {
          radio.checked = true;
          this.warrantyCards.forEach((c) => c.classList.remove('selected'));
          card.classList.add('selected');
          this.formState.warrantyStatus = radio.value;
          this.clearError(null, this.errWarrantyStatus);
        }
      });
    });
  }

  validateWarrantyStatus() {
    const selected = document.querySelector('input[name="warrantyStatus"]:checked');
    if (!selected) {
      this.setError(null, this.errWarrantyStatus, 'Please select a warranty status.');
      return false;
    }
    this.clearError(null, this.errWarrantyStatus);
    this.formState.warrantyStatus = selected.value;
    return true;
  }

  validatePurchaseDate() {
    const val = this.purchaseDateInput ? this.purchaseDateInput.value : '';
    if (!val) {
      this.setError(this.purchaseDateInput, this.errPurchaseDate, 'Purchase date is required.');
      return false;
    }

    const purchaseDate = new Date(val);
    const today = new Date();
    today.setHours(23, 59, 59, 999);

    if (isNaN(purchaseDate.getTime())) {
      this.setError(this.purchaseDateInput, this.errPurchaseDate, 'Invalid purchase date.');
      return false;
    }

    if (purchaseDate > today) {
      this.setError(
        this.purchaseDateInput,
        this.errPurchaseDate,
        `Purchase date cannot be in the future (today is ${new Date().toISOString().split('T')[0]}).`
      );
      return false;
    }

    this.clearError(this.purchaseDateInput, this.errPurchaseDate);
    this.formState.purchaseDate = val;
    return true;
  }

  validateExpiryDate() {
    const expiryVal = this.expiryDateInput ? this.expiryDateInput.value : '';
    const purchaseVal = this.purchaseDateInput ? this.purchaseDateInput.value : '';

    if (!expiryVal) {
      this.clearError(this.expiryDateInput, this.errExpiryDate);
      this.formState.warrantyExpiryDate = null;
      return true;
    }

    const expiryDate = new Date(expiryVal);
    if (isNaN(expiryDate.getTime())) {
      this.setError(this.expiryDateInput, this.errExpiryDate, 'Invalid warranty expiry date.');
      return false;
    }

    if (purchaseVal) {
      const purchaseDate = new Date(purchaseVal);
      if (expiryDate < purchaseDate) {
        this.setError(
          this.expiryDateInput,
          this.errExpiryDate,
          'Warranty expiry date cannot precede the purchase date.'
        );
        return false;
      }
    }

    this.clearError(this.expiryDateInput, this.errExpiryDate);
    this.formState.warrantyExpiryDate = expiryVal;
    return true;
  }

  validate() {
    const isStatusValid = this.validateWarrantyStatus();
    const isPurchaseValid = this.validatePurchaseDate();
    const isExpiryValid = this.validateExpiryDate();

    return isStatusValid && isPurchaseValid && isExpiryValid;
  }

  setError(inputEl, errorEl, message) {
    if (inputEl) inputEl.classList.add('is-invalid');
    if (errorEl) {
      errorEl.textContent = message;
      errorEl.style.display = 'flex';
    }
  }

  clearError(inputEl, errorEl) {
    if (inputEl) inputEl.classList.remove('is-invalid');
    if (errorEl) {
      errorEl.textContent = '';
      errorEl.style.display = 'none';
    }
  }
}

window.WarrantyStep = WarrantyStep;
