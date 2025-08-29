document.addEventListener('DOMContentLoaded', function() {
    const mainUploadForm = document.getElementById('main-upload-form');
    const formActionInput = document.getElementById('form-action');
    const step1Section = document.getElementById('step1-selection-section');
    const step2UploadSection = document.getElementById('step2-upload-section');
    const mainSubmitButtonContainer = document.getElementById('main-submit-button-container');

    const step3ReviewSection = document.getElementById('step3-review-section');
    const editedOcrTextArea = document.getElementById('edited-ocr-text-area');
    const analyzeAndSaveButton = document.getElementById('analyze-and-save-button');
    const backToStep1Button = document.getElementById('back-to-step1-button');

    const step4ResultsSection = document.getElementById('step4-results-section');
    const analysisSummaryDisplay = document.getElementById('analysis-summary-display');
    const analysisHtmlTableDisplay = document.getElementById('analysis-html-table-display');
    const viewMedicalEventButton = document.getElementById('view-medical-event-button');

    const eventSelect = document.getElementById('event-type-select');
    const categorySelect = document.getElementById('category-select');
    const specialtySelect = document.getElementById('specialty-select');
    const doctorSelect = document.getElementById('doctor-select');
    const fileInput = document.getElementById('document-input');
    const fileTypeSelect = document.getElementById('file-type-select');
    const mainUploadButton = document.getElementById('main-upload-button');

    const fileNameDisplay = document.getElementById('file-name-display');
    const imagePreview = document.getElementById('image-preview');
    const pdfPreview = document.getElementById('pdf-preview');
    const previewPlaceholder = document.getElementById('preview-placeholder');
    const viewFullSizeLink = document.getElementById('view-full-size-link');

    const reviewEventTypeSpan = document.getElementById('review-event-type');
    const reviewCategorySpan = document.getElementById('review-category');
    const reviewSpecialtySpan = document.getElementById('review-specialty');
    const reviewDoctorSpan = document.getElementById('review-doctor');

    const specialtiesUrl = mainUploadForm.dataset.specialtiesUrl; // Ще вземем от data-specialties-url атрибут
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    const inputsToValidate = [eventSelect, categorySelect, specialtySelect, fileInput, fileTypeSelect];

    const spinnerSVG = `<svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white inline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>`;

    function checkFormValidity() {
        const allValid = inputsToValidate.every(input => {
            if (input.type === 'file') {
                return input.files.length > 0;
            }
            return input.value.trim() !== '';
        });
        mainUploadButton.disabled = !allValid;
        if (!allValid) {
            mainUploadButton.classList.add('opacity-40', 'cursor-not-allowed');
        } else {
            mainUploadButton.classList.remove('opacity-40', 'cursor-not-allowed');
        }
    }

    function showLoading(button, message) {
        button.disabled = true;
        button.innerHTML = `${spinnerSVG}${message}`;
        button.style.backgroundColor = '#0A4E75';
    }

    function resetButton(button, originalText, originalColor) {
        button.disabled = false;
        button.innerHTML = originalText;
        button.style.backgroundColor = originalColor;
    }

    function displayError(message) {
        const errorDiv = document.querySelector('.bg-light-red-bg');
        if (errorDiv) {
            errorDiv.querySelector('span').textContent = message;
            errorDiv.classList.remove('hidden');
        } else {
            alert(message);
        }
    }

    function hideError() {
        const errorDiv = document.querySelector('.bg-light-red-bg');
        if (errorDiv) {
            errorDiv.classList.add('hidden');
        }
    }

    function updateUI(data, step) {
        if (step === 1) { // Show initial form
            step1Section.classList.remove('hidden');
            step2UploadSection.classList.remove('hidden');
            mainSubmitButtonContainer.classList.remove('hidden');
            step3ReviewSection.classList.add('hidden');
            step4ResultsSection.classList.add('hidden');
        } else if (step === 2) { // Show review section
            editedOcrTextArea.value = data.ocr_text;
            reviewEventTypeSpan.textContent = data.selected_event_type_display;
            reviewCategorySpan.textContent = data.selected_category_display;
            reviewSpecialtySpan.textContent = data.selected_specialty_display;
            reviewDoctorSpan.textContent = data.selected_doctor_display;

            if (data.temp_file_url) {
                previewPlaceholder.classList.add('hidden');
                viewFullSizeLink.href = data.temp_file_url;
                viewFullSizeLink.classList.remove('hidden');
                if (data.file_type === 'image') {
                    imagePreview.src = data.temp_file_url;
                    imagePreview.classList.remove('hidden');
                    pdfPreview.classList.add('hidden');
                } else if (data.file_type === 'pdf') {
                    pdfPreview.src = data.temp_file_url + '#toolbar=0&navpanes=0&scrollbar=0';
                    pdfPreview.classList.remove('hidden');
                    imagePreview.classList.add('hidden');
                }
            }
            step1Section.classList.add('hidden');
            step2UploadSection.classList.add('hidden');
            mainSubmitButtonContainer.classList.add('hidden');
            step3ReviewSection.classList.remove('hidden');
            step4ResultsSection.classList.add('hidden');
        } else if (step === 3) { // Show results section
            analysisSummaryDisplay.innerHTML = data.summary;
            analysisHtmlTableDisplay.innerHTML = data.html_table;
            viewMedicalEventButton.href = `${window.location.origin}/medical-events/${data.event_id}/detail/`;

            step1Section.classList.add('hidden');
            step2UploadSection.classList.add('hidden');
            mainSubmitButtonContainer.classList.add('hidden');
            step3ReviewSection.classList.add('hidden');
            step4ResultsSection.classList.remove('hidden');
        }
    }

    mainUploadForm.addEventListener('submit', function(event) {
        event.preventDefault();
        hideError();

        const formData = new FormData(this);
        const action = formData.get('action');

        if (action === 'perform_ocr_and_analyze') {
            if (mainUploadButton.disabled) {
                displayError(MESSAGES.choose_category_specialist_file);
                return;
            }
            showLoading(mainUploadButton, MESSAGES.processing);
        } else if (action === 'analyze_and_save') {
            showLoading(analyzeAndSaveButton, MESSAGES.analysis_ai);
        }

        fetch(this.action, {
            method: 'POST',
            body: formData,
        })
        .then(response => response.json())
        .then(data => {
            if (action === 'perform_ocr_and_analyze') {
                resetButton(mainUploadButton, MESSAGES.upload_button, '#15BC11');
                if (data.status === 'success') {
                    updateUI(data, 2); // Show review section
                    formActionInput.value = 'analyze_and_save'; // Change action for next step
                } else {
                    displayError(data.message || MESSAGES.critical_ocr_error);
                }
            } else if (action === 'analyze_and_save') {
                resetButton(analyzeAndSaveButton, MESSAGES.approve_analyze_ai, '#15BC11');
                if (data.status === 'success') {
                    updateUI(data, 3); // Show results section
                } else {
                    displayError(data.message || MESSAGES.critical_analysis_error);
                }
            }
        })
        .catch(error => {
            console.error('Fetch Error:', error);
            if (action === 'perform_ocr_and_analyze') {
                resetButton(mainUploadButton, MESSAGES.upload_button, '#15BC11');
                displayError(MESSAGES.network_server_error);
            } else if (action === 'analyze_and_save') {
                resetButton(analyzeAndSaveButton, MESSAGES.approve_analyze_ai, '#15BC11');
                displayError(MESSAGES.network_server_error);
            }
        });
    });

    backToStep1Button.addEventListener('click', function() {
        formActionInput.value = 'perform_ocr_and_analyze';
        updateUI({}, 1); // Reset to step 1
        editedOcrTextArea.value = '';
        fileInput.value = '';
        fileNameDisplay.textContent = MESSAGES.no_file_chosen;
        fileNameDisplay.style.color = '#6B7280';
        previewPlaceholder.classList.remove('hidden');
        imagePreview.classList.add('hidden');
        pdfPreview.classList.add('hidden');
        viewFullSizeLink.classList.add('hidden');
        checkFormValidity();
    });

    categorySelect.addEventListener('change', function () {
        const categoryId = this.value;
        specialtySelect.innerHTML = '<option value="" disabled selected>' + MESSAGES.choose_specialty_prompt + '</option>';
        specialtySelect.disabled = true;

        if (categoryId) {
            fetch(`${specialtiesUrl}?category_id=${categoryId}`)
                .then(response => response.json())
                .then(data => {
                    specialtySelect.innerHTML = '<option value="" disabled selected>' + MESSAGES.choose_specialty_prompt + '</option>';
                    if (data.specialties.length === 0) {
                        specialtySelect.innerHTML = '<option value="" disabled selected>' + MESSAGES.no_specialties_found + '</option>';
                    } else {
                        data.specialties.forEach(function (spec) {
                            const option = new Option(spec.name, spec.id);
                            specialtySelect.add(option);
                        });
                    }
                    specialtySelect.disabled = false;
                })
                .catch(error => {
                    console.error('Fetch error:', error);
                    specialtySelect.innerHTML = '<option value="">' + MESSAGES.error_fetching_specialties + '</option>';
                })
                .finally(() => {
                    checkFormValidity();
                });
        } else {
            specialtySelect.innerHTML = '<option value="" disabled selected>' + MESSAGES.choose_specialty_first + '</option>';
            checkFormValidity();
        }
    });

    eventSelect.addEventListener('change', function() {
        if (this.value) {
            categorySelect.disabled = false;
            categorySelect.value = "";
            specialtySelect.disabled = true;
            specialtySelect.value = "";
            categorySelect.querySelector('option[disabled]').textContent = MESSAGES.choose_category_first;
        } else {
            categorySelect.disabled = true;
            categorySelect.value = "";
            specialtySelect.disabled = true;
            specialtySelect.value = "";
            categorySelect.querySelector('option[disabled]').textContent = MESSAGES.choose_category_first;
        }
        checkFormValidity();
    });

    fileInput.addEventListener('change', function() {
        if (this.files.length > 0) {
            fileNameDisplay.textContent = `${MESSAGES.file_chosen}: ${this.files[0].name}`;
            fileNameDisplay.style.color = '#15BC11';
            previewPlaceholder.classList.remove('hidden');
            imagePreview.classList.add('hidden');
            pdfPreview.classList.add('hidden');
            viewFullSizeLink.classList.add('hidden');
        } else {
            fileNameDisplay.textContent = MESSAGES.no_file_chosen;
            fileNameDisplay.style.color = '#6B7280';
            previewPlaceholder.classList.remove('hidden');
            imagePreview.classList.add('hidden');
            pdfPreview.classList.add('hidden');
            viewFullSizeLink.classList.add('hidden');
        }
        checkFormValidity();
    });

    fileTypeSelect.addEventListener('change', checkFormValidity);
    doctorSelect.addEventListener('change', checkFormValidity);

    categorySelect.disabled = true;
    specialtySelect.disabled = true;
    checkFormValidity();

    inputsToValidate.forEach(input => {
        if (input !== fileInput && input !== fileTypeSelect && input !== eventSelect && input !== categorySelect && input !== doctorSelect) {
            input.addEventListener('change', checkFormValidity);
        }
    });
});