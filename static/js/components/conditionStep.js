/**
 * Step 1: Product Condition Component
 * Manages Product SKU/ID, Product Name, Category dropdown, and Condition radio cards.
 */

class ConditionStep {
  constructor(formState) {
    this.formState = formState;
    this.initDOM();
  }

  initDOM() {
    this.productIdInput = document.getElementById('inputProductId');
    this.productNameInput = document.getElementById('inputProductName');
    this.categorySelect = document.getElementById('selectCategory');
    this.conditionCards = document.querySelectorAll('.condition-card');

    this.errProductId = document.getElementById('errProductId');
    this.errCategory = document.getElementById('errCategory');
    this.errCondition = document.getElementById('errCondition');

    // Attach listeners
    if (this.productIdInput) {
      this.productIdInput.addEventListener('input', () => {
        this.formState.productId = this.productIdInput.value.trim();
        if (this.formState.productId) {
          this.clearError(this.productIdInput, this.errProductId);
        }
      });
      this.productIdInput.addEventListener('blur', () => this.validateProductId());
    }

    if (this.productNameInput) {
      this.productNameInput.addEventListener('input', () => {
        this.formState.productName = this.productNameInput.value.trim();
      });
    }

    if (this.categorySelect) {
      this.categorySelect.addEventListener('change', () => {
        this.formState.category = this.categorySelect.value.trim();
        if (this.formState.category) {
          this.clearError(this.categorySelect, this.errCategory);
        }
      });
      this.categorySelect.addEventListener('blur', () => this.validateCategory());
    }

    // Condition Cards Radio selection
    this.conditionCards.forEach((card) => {
      card.addEventListener('click', () => {
        const radio = card.querySelector('input[type="radio"]');
        if (radio) {
          radio.checked = true;
          this.conditionCards.forEach((c) => c.classList.remove('selected'));
          card.classList.add('selected');
          this.formState.condition = radio.value;
          this.clearError(null, this.errCondition);

          // Dispatch event to inform defect step (e.g. if Damaged / Non-functional selected)
          window.dispatchEvent(new CustomEvent('conditionChanged', {
            detail: { condition: radio.value }
          }));
        }
      });
    });
  }

  validateProductId() {
    const val = (this.productIdInput ? this.productIdInput.value : '').trim();
    if (!val) {
      this.setError(this.productIdInput, this.errProductId, 'Product identifier or SKU is required.');
      return false;
    }
    this.clearError(this.productIdInput, this.errProductId);
    this.formState.productId = val;
    return true;
  }

  validateCategory() {
    const val = (this.categorySelect ? this.categorySelect.value : '').trim();
    if (!val) {
      this.setError(this.categorySelect, this.errCategory, 'Please select a product category.');
      return false;
    }
    this.clearError(this.categorySelect, this.errCategory);
    this.formState.category = val;
    return true;
  }

  validateCondition() {
    const selected = document.querySelector('input[name="condition"]:checked');
    if (!selected) {
      this.setError(null, this.errCondition, 'Please select the physical condition of the product.');
      return false;
    }
    this.clearError(null, this.errCondition);
    this.formState.condition = selected.value;
    return true;
  }

  validate() {
    const isIdValid = this.validateProductId();
    const isCatValid = this.validateCategory();
    const isCondValid = this.validateCondition();

    return isIdValid && isCatValid && isCondValid;
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

  populateFromState() {
    if (this.productIdInput && this.formState.productId) {
      this.productIdInput.value = this.formState.productId;
    }
    if (this.productNameInput && this.formState.productName) {
      this.productNameInput.value = this.formState.productName;
    }
    if (this.categorySelect && this.formState.category) {
      this.categorySelect.value = this.formState.category;
    }
    if (this.formState.condition) {
      const radio = document.querySelector(`input[name="condition"][value="${this.formState.condition}"]`);
      if (radio) {
        radio.checked = true;
        this.conditionCards.forEach((c) => c.classList.remove('selected'));
        const parentCard = radio.closest('.condition-card');
        if (parentCard) parentCard.classList.add('selected');
      }
    }
  }
}

window.ConditionStep = ConditionStep;
