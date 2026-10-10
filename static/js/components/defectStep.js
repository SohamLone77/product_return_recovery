/**
 * Step 2: Defect Information Component
 * Defect Category, Defect Description, Visible Damage (Yes/No), and Optional Damage Image.
 * Enforces conditional validations based on product condition and "Other" category.
 */

class DefectStep {
  constructor(formState) {
    this.formState = formState;
    this.initDOM();
  }

  initDOM() {
    this.defectPillCards = document.querySelectorAll('.defect-pill-card');
    this.defectDescTextarea = document.getElementById('textareaDefectDesc');
    this.charCountEl = document.getElementById('charCountDefectDesc');
    this.toggleDamagePills = document.querySelectorAll('.toggle-damage-pill');

    // Image Upload DOM
    this.dropzone = document.getElementById('damageImageDropzone');
    this.fileInput = document.getElementById('fileDamageImage');
    this.previewContainer = document.getElementById('damageImagePreview');
    this.previewThumb = document.getElementById('damagePreviewThumb');
    this.previewName = document.getElementById('damagePreviewName');
    this.previewMeta = document.getElementById('damagePreviewMeta');
    this.btnRemoveImage = document.getElementById('btnRemoveDamageImage');

    // Error message elements
    this.errDefectCategory = document.getElementById('errDefectCategory');
    this.errDefectDesc = document.getElementById('errDefectDesc');
    this.errVisibleDamage = document.getElementById('errVisibleDamage');
    this.errImageUpload = document.getElementById('errImageUpload');

    // Attach listeners
    this.defectPillCards.forEach((card) => {
      card.addEventListener('click', () => {
        const radio = card.querySelector('input[type="radio"]');
        if (radio) {
          radio.checked = true;
          this.defectPillCards.forEach((c) => c.classList.remove('selected'));
          card.classList.add('selected');
          this.formState.defectCategory = radio.value;
          this.clearError(null, this.errDefectCategory);
          this.handleConditionalFields();
        }
      });
    });

    if (this.defectDescTextarea) {
      this.defectDescTextarea.addEventListener('input', () => {
        const val = this.defectDescTextarea.value;
        this.formState.defectDescription = val;
        if (this.charCountEl) {
          this.charCountEl.textContent = `${val.length}/500`;
        }
        if (val.trim()) {
          this.clearError(this.defectDescTextarea, this.errDefectDesc);
        }
      });
      this.defectDescTextarea.addEventListener('blur', () => this.validateDefectDesc());
    }

    // Visible Damage Toggle Pills (Yes / No)
    this.toggleDamagePills.forEach((pill) => {
      pill.addEventListener('click', () => {
        const radio = pill.querySelector('input[type="radio"]');
        if (radio) {
          radio.checked = true;
          this.toggleDamagePills.forEach((p) => p.classList.remove('selected'));
          pill.classList.add('selected');
          this.formState.visibleDamage = radio.value === 'yes';
          this.clearError(null, this.errVisibleDamage);
        }
      });
    });

    // File Upload handling
    this.initImageUpload();

    // Listen to condition change events to update guidance
    window.addEventListener('conditionChanged', (e) => {
      this.handleConditionNotice(e.detail.condition);
    });
  }

  initImageUpload() {
    if (!this.dropzone || !this.fileInput) return;

    this.dropzone.addEventListener('click', () => {
      this.fileInput.click();
    });

    this.fileInput.addEventListener('change', (e) => {
      const file = e.target.files && e.target.files[0];
      if (file) {
        this.processImageFile(file);
      }
    });

    // Drag & Drop
    ['dragenter', 'dragover'].forEach((eventName) => {
      this.dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        this.dropzone.classList.add('dragover');
      });
    });

    ['dragleave', 'drop'].forEach((eventName) => {
      this.dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        this.dropzone.classList.remove('dragover');
      });
    });

    this.dropzone.addEventListener('drop', (e) => {
      const dt = e.dataTransfer;
      const file = dt.files && dt.files[0];
      if (file) {
        this.processImageFile(file);
      }
    });

    if (this.btnRemoveImage) {
      this.btnRemoveImage.addEventListener('click', (e) => {
        e.stopPropagation();
        this.removeImage();
      });
    }
  }

  processImageFile(file) {
    if (!file.type.startsWith('image/')) {
      this.setError(null, this.errImageUpload, 'Please select a valid image file (PNG, JPG, WEBP).');
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      this.setError(null, this.errImageUpload, 'Image size exceeds maximum limit of 5MB.');
      return;
    }

    this.clearError(null, this.errImageUpload);

    const reader = new FileReader();
    reader.onload = (e) => {
      const dataUrl = e.target.result;
      this.formState.damageImage = {
        fileName: file.name,
        fileSize: file.size,
        contentType: file.type,
        dataUrl: dataUrl
      };

      if (this.previewThumb) this.previewThumb.src = dataUrl;
      if (this.previewName) this.previewName.textContent = file.name;
      if (this.previewMeta) this.previewMeta.textContent = `${(file.size / 1024).toFixed(1)} KB • ${file.type}`;
      if (this.previewContainer) this.previewContainer.style.display = 'flex';
      if (this.dropzone) this.dropzone.style.display = 'none';
    };
    reader.readAsDataURL(file);
  }

  removeImage() {
    this.formState.damageImage = null;
    if (this.fileInput) this.fileInput.value = '';
    if (this.previewContainer) this.previewContainer.style.display = 'none';
    if (this.dropzone) this.dropzone.style.display = 'block';
  }

  handleConditionNotice(condition) {
    const noticeEl = document.getElementById('conditionDefectNotice');
    if (!noticeEl) return;

    if (condition === 'Damaged' || condition === 'Non-functional') {
      noticeEl.innerHTML = `
        <span class="alert-icon">ℹ️</span>
        <span>Product condition is <strong>${condition}</strong>. Please record the specific defect and describe the issue so recovery routing can assess repair eligibility.</span>
      `;
      noticeEl.style.display = 'flex';
    } else {
      noticeEl.style.display = 'none';
    }
  }

  handleConditionalFields() {
    const isOther = this.formState.defectCategory === 'Other';
    const label = document.getElementById('labelDefectDescRequired');
    if (label) {
      const isDamagedOrBroken = ['Damaged', 'Non-functional'].includes(this.formState.condition);
      label.style.display = (isOther || isDamagedOrBroken) ? 'inline' : 'none';
    }
  }

  validateDefectCategory() {
    const selected = document.querySelector('input[name="defectCategory"]:checked');
    if (!selected) {
      this.setError(null, this.errDefectCategory, 'Please select a defect category.');
      return false;
    }

    const cat = selected.value;
    const cond = this.formState.condition;

    // If condition is Damaged or Non-functional, defect cannot be "No defect"
    if (['Damaged', 'Non-functional'].includes(cond) && cat === 'No defect') {
      this.setError(
        null,
        this.errDefectCategory,
        `Products marked as '${cond}' must specify a defect category other than 'No defect'.`
      );
      return false;
    }

    this.clearError(null, this.errDefectCategory);
    this.formState.defectCategory = cat;
    return true;
  }

  validateDefectDesc() {
    const desc = (this.defectDescTextarea ? this.defectDescTextarea.value : '').trim();
    const cat = this.formState.defectCategory;
    const cond = this.formState.condition;

    const isOther = cat === 'Other';
    const isDamagedOrBroken = ['Damaged', 'Non-functional'].includes(cond);

    if (isOther && !desc) {
      this.setError(this.defectDescTextarea, this.errDefectDesc, "Please provide an explanatory description when selecting 'Other' defect.");
      return false;
    }

    if (isDamagedOrBroken && !desc) {
      this.setError(this.defectDescTextarea, this.errDefectDesc, `Defect description is required when product is '${cond}'.`);
      return false;
    }

    this.clearError(this.defectDescTextarea, this.errDefectDesc);
    this.formState.defectDescription = desc;
    return true;
  }

  validateVisibleDamage() {
    const selected = document.querySelector('input[name="visibleDamage"]:checked');
    if (!selected) {
      this.setError(null, this.errVisibleDamage, 'Please indicate whether there is visible physical damage.');
      return false;
    }
    this.clearError(null, this.errVisibleDamage);
    this.formState.visibleDamage = selected.value === 'yes';
    return true;
  }

  validate() {
    const isCatValid = this.validateDefectCategory();
    const isDescValid = this.validateDefectDesc();
    const isVisValid = this.validateVisibleDamage();

    return isCatValid && isDescValid && isVisValid;
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

window.DefectStep = DefectStep;
