// static/js/upload_logic.js

document.addEventListener('DOMContentLoaded', function() {
    // Select elements based on the new HTML structure
    const uploadContainer = document.getElementById('upload-container'); // The main cream block
    const eventTypeSelect = document.getElementById('event-type-select');
    const categorySelect = document.getElementById('category');
    const specialtySelect = document.getElementById('specialist');
    const doctorSelect = document.getElementById('doctor-select');
    const fileInput = document.getElementById('file_input');
    const fileTypeSelect = document.getElementById('file-type-select');
    const uploadOcrButton = document.getElementById('upload-ocr-button'); // The "Сканирай" button
    const analyzeButton = document.getElementById('analyze-button'); // The "Одобри и анализирай с AI" button
    const ocrTextArea = document.getElementById('ocr_text_area');

    // Main layout sections (visibility controlled)
    const fullUploadForm = document.getElementById('full-upload-form'); // The form for initial upload
    const step3ReviewDiv = document.getElementById('step3-review'); // The review section (Step 2)
    const resultsSection = document.getElementById('results-section'); // The final results section

    // Elements within resultsSection (if they are still defined within it)
    const resultSummary = document.getElementById('result-summary');
    const resultHtmlTable = document.getElementById('result-html-table');

    // Preview elements (now main preview is the only one in HTML structure related to file input)
    const mainImagePreview = document.getElementById('main-image-preview');
    const mainPdfPreview = document.getElementById('main-pdf-preview');
    const mainPreviewPlaceholder = document.getElementById('main-preview-placeholder');
    const viewFullSizeLink = document.getElementById('view-full-size-link');

    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    const languagePrefix = '/' + document.documentElement.lang;

    // Global loading overlay
    const analysisLoadingOverlay = document.getElementById('analysis-loading-overlay');

    // Elements on upload_review.html for display and hidden submission
    const displayEventTypeTitle = document.getElementById('display_event_type_title');
    const displayCategoryName = document.getElementById('display_category_name');
    const displaySpecialtyName = document.getElementById('display_specialty_name');
    const displayPractitionerName = document.getElementById('display_practitioner_name');
    const displayEventDate = document.getElementById('display_event_date');
    const manualEventDateInput = document.getElementById('manual_event_date_input');
    const manualEventDateContainer = document.getElementById('manual_event_date_container');

    // Hidden inputs on review form for re-submission
    const reviewDocumentIdInput = document.getElementById('review_document_id');
    const reviewEventTypeTitleHidden = document.getElementById('review_event_type_title_hidden');
    const reviewCategoryNameHidden = document.getElementById('review_category_name_hidden');
    const reviewSpecialtyNameHidden = document.getElementById('review_specialty_name_hidden');
    const reviewPractitionerNameHidden = document.getElementById('review_practitioner_name_hidden');
    const reviewEventDateHidden = document.getElementById('review_event_date_hidden');


    // Back to Upload Button Logic (on review page)
    const backToUploadButton = document.getElementById('back-to-upload-button');
    if (backToUploadButton) {
        backToUploadButton.addEventListener('click', function() {
            window.location.href = `${languagePrefix}/upload/`;
        });
    }

    // --- OCR Upload Button (Сканирай) Logic ---
    if (uploadOcrButton) {
        uploadOcrButton.addEventListener('click', function() {
            const file = fileInput.files[0];
            const eventType = eventTypeSelect.value;
            const categoryName = categorySelect.value;
            const specialtyName = specialtySelect.value;
            const doctorName = doctorSelect.value;
            const fileType = fileTypeSelect.value;

            if (!file) {
                alert(MESSAGES.select_file);
                return;
            }
            if (!eventType) {
                alert(MESSAGES.select_event_type || "Моля, изберете тип на събитието.");
                return;
            }
            if (!categoryName) {
                alert(MESSAGES.select_category || "Моля, изберете медицинска категория.");
                return;
            }
            if (!specialtyName) {
                alert(MESSAGES.select_specialty || "Моля, изберете специалност/изследване.");
                return;
            }
            if (!fileType) {
                alert(MESSAGES.select_file_type || "Моля, посочете тип на файла.");
                return;
            }

            if (file.size > 10 * 1024 * 1024) { // 10 MB limit
                alert(MESSAGES.file_too_large);
                return;
            }

            const allowedExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.tiff', '.bmp', '.webp', '.pdf'];
            const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
            if (!allowedExtensions.includes(fileExtension)) {
                alert(MESSAGES.invalid_file_type);
                return;
            }

            const formData = new FormData();
            formData.append('file', file);
            formData.append('csrfmiddlewaretoken', csrfToken);
            formData.append('event_type_title', eventType);
            formData.append('category_name', categoryName);
            formData.append('specialty_name', specialtyName);
            formData.append('practitioner_name', doctorName);
            formData.append('file_type', fileType);

            uploadOcrButton.disabled = true;
            uploadOcrButton.innerHTML = `<span class="spinner-border spinner-border-sm"></span> ${MESSAGES.uploading_file || 'Качва се файл...'}`;

            // Hide initial form and show global loading overlay
            if (fullUploadForm) fullUploadForm.classList.add('hidden');
            if (analysisLoadingOverlay) analysisLoadingOverlay.classList.remove('hidden');

            fetch(`${languagePrefix}/api/perform-ocr/`, {
                method: 'POST',
                body: formData,
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(errorData => {
                        throw new Error(errorData.message || MESSAGES.unknown_server_error);
                    });
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    if (ocrTextArea) ocrTextArea.value = data.ocr_text;
                    if (reviewDocumentIdInput) reviewDocumentIdInput.value = data.document_id;

                    // Set hidden inputs on review form for re-submission
                    if (reviewEventTypeTitleHidden) reviewEventTypeTitleHidden.value = eventType;
                    if (reviewCategoryNameHidden) reviewCategoryNameHidden.value = categoryName;
                    if (reviewSpecialtyNameHidden) reviewSpecialtyNameHidden.value = specialtyName;
                    if (reviewPractitionerNameHidden) reviewPractitionerNameHidden.value = doctorName;

                    // Display selected options on the review page
                    if (displayEventTypeTitle) displayEventTypeTitle.textContent = eventTypeSelect.options[eventTypeSelect.selectedIndex].textContent;
                    if (displayCategoryName) displayCategoryName.textContent = categorySelect.options[categorySelect.selectedIndex].textContent;
                    if (displaySpecialtyName) displaySpecialtyName.textContent = specialtySelect.options[specialtySelect.selectedIndex].textContent;
                    if (displayPractitionerName) displayPractitionerName.textContent = doctorSelect.options[doctorSelect.selectedIndex].textContent;

                    // Handle main preview (now only one set of preview elements)
                    if (data.file_url) {
                        const fileExtension = '.' + data.file_url.split('.').pop().toLowerCase();
                        if (fileExtension === '.pdf') {
                            mainPdfPreview.src = data.file_url;
                            mainPdfPreview.classList.remove('hidden');
                            mainImagePreview.classList.add('hidden');
                        } else if (['.jpg', '.jpeg', '.png', '.gif', '.tiff', '.bmp', '.webp'].includes(fileExtension)) {
                            mainImagePreview.src = data.file_url;
                            mainImagePreview.classList.remove('hidden');
                            mainPdfPreview.classList.add('hidden');
                        }
                        if (mainPreviewPlaceholder) mainPreviewPlaceholder.classList.add('hidden');
                        if (viewFullSizeLink) viewFullSizeLink.href = data.file_url;
                    } else {
                        if (mainPreviewPlaceholder) mainPreviewPlaceholder.classList.remove('hidden');
                    }

                    if (step3ReviewDiv) step3ReviewDiv.classList.remove('hidden'); // Show review step
                    alert(MESSAGES.ocr_success);
                } else {
                    alert(`${MESSAGES.upload_error || 'Upload error'}: ${data.message}`);
                    // Show initial form on error
                    if (fullUploadForm) fullUploadForm.classList.remove('hidden');
                }
            })
            .catch(error => {
                console.error('OCR Upload Error:', error);
                alert(`${MESSAGES.critical_upload_error || 'Critical upload error'}: ${error.message}`);
                if (fullUploadForm) fullUploadForm.classList.remove('hidden');
            })
            .finally(() => {
                uploadOcrButton.disabled = false;
                uploadOcrButton.innerHTML = MESSAGES.uploading_file || 'Качи и обработи с OCR';
                if (analysisLoadingOverlay) analysisLoadingOverlay.classList.add('hidden');
            });
        });
    }

    // --- AI Analyze Button Logic ---
    if (analyzeButton) {
        analyzeButton.addEventListener('click', function() {
            const editedOcrText = ocrTextArea ? ocrTextArea.value : '';
            const documentId = reviewDocumentIdInput.value;

            if (!editedOcrText || !documentId) {
                alert((MESSAGES.analysis_error || 'Analysis error') + " " + (MESSAGES.no_text_or_doc_id || "No text or document ID."));
                return;
            }

            analyzeButton.disabled = true;
            analyzeButton.innerHTML = `<span class="spinner-border spinner-border-sm"></span> ${MESSAGES.analyze_loading || 'Извършва се анализ...'}`;

            // Hide review section and show global loading overlay
            if (step3ReviewDiv) step3ReviewDiv.classList.add('hidden');
            if (analysisLoadingOverlay) analysisLoadingOverlay.classList.remove('hidden');

            const formData = new FormData();
            formData.append('edited_ocr_text', editedOcrText);
            formData.append('temp_document_id', documentId);
            formData.append('csrfmiddlewaretoken', csrfToken);

            const reviewForm = document.getElementById('review-form');
            if (reviewForm) {
                const eventTypeTitleInput = reviewForm.querySelector('input[name="event_type_title"]');
                const categoryNameInput = reviewForm.querySelector('input[name="category_name"]');
                const specialtyNameInput = reviewForm.querySelector('input[name="specialty_name"]');
                const practitionerNameInput = reviewForm.querySelector('input[name="practitioner_name"]');
                const manualEventDateInput = document.getElementById('manual_event_date_input');

                if (eventTypeTitleInput) formData.append('event_type_title', eventTypeTitleInput.value);
                if (categoryNameInput) formData.append('category_name', categoryNameInput.value);
                if (specialtyNameInput) formData.append('specialty_name', specialtyNameInput.value);
                if (practitionerNameInput) formData.append('practitioner_name', practitionerNameInput.value);

                if (manualEventDateInput && manualEventDateInput.value) {
                    formData.append('event_date', manualEventDateInput.value);
                } else if (reviewEventDateHidden && reviewEventDateHidden.value) {
                    formData.append('event_date', reviewEventDateHidden.value);
                }
            }


            fetch(`${languagePrefix}/api/analyze-document/`, {
                method: 'POST',
                body: formData,
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(errorData => {
                        throw new Error(errorData.message || MESSAGES.unknown_server_error);
                    });
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    alert(data.message);
                    if (data.redirect_url) {
                        window.location.href = data.redirect_url;
                    }
                }
                else if (data.status === 'redirect_to_review') {
                    alert(data.message);
                    window.location.href = data.redirect_url;
                }
                else {
                    alert(`${MESSAGES.analysis_error || 'Analysis error'}: ${data.message}`);
                }
            })
            .catch(error => {
                console.error('Analyze Error:', error);
                alert(`${MESSAGES.critical_analysis_error || 'Critical analysis error'}: ${error.message}`);
            })
            .finally(() => {
                if (analyzeButton) {
                    analyzeButton.disabled = false;
                    analyzeButton.innerHTML = MESSAGES.approve_analyze_ai || 'Одобри и анализирай с AI';
                }
                if (analysisLoadingOverlay) analysisLoadingOverlay.classList.add('hidden');
            });
        });
    }

    // --- Dynamic loading of specialties based on category ---
    if (categorySelect && specialtySelect) {
        categorySelect.addEventListener('change', function() {
            const selectedCategoryName = categorySelect.value;
            if (selectedCategoryName) {
                specialtySelect.disabled = true;
                specialtySelect.innerHTML = `<option value="">${MESSAGES.loading_specialties || "Зарежда специалности..."}</option>`;

                fetch(`${languagePrefix}/ajax/get-specialties/?category_name=${encodeURIComponent(selectedCategoryName)}`)
                    .then(response => response.json())
                    .then(data => {
                        specialtySelect.innerHTML = `<option value="">${MESSAGES.select_specialty || "Изберете специалност..."}</option>`;
                        data.specialties.forEach(specialty => {
                            const option = document.createElement('option');
                            option.value = specialty.name;
                            option.textContent = specialty.name;
                            specialtySelect.appendChild(option);
                        });
                        specialtySelect.disabled = false;
                    })
                    .catch(error => {
                        console.error('Error loading specialties:', error);
                        specialtySelect.innerHTML = `<option value="">${MESSAGES.error_loading_specialties || "Грешка при зареждане..."}</option>`;
                        specialtySelect.disabled = true;
                    });
            } else {
                specialtySelect.disabled = true;
                specialtySelect.innerHTML = `<option value="">${MESSAGES.select_category_first || "Първо изберете категория"}</option>`;
            }
        });
    }

    // --- File Input Change Listener for Preview ---
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            const file = this.files[0];
            const customFileText = document.querySelector('.custom-file-text');
            if (file) {
                customFileText.textContent = file.name;
                const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
                const fileURL = URL.createObjectURL(file);

                // Reset previews
                mainImagePreview.classList.add('hidden');
                mainPdfPreview.classList.add('hidden');
                mainPreviewPlaceholder.classList.remove('hidden');

                viewFullSizeLink.classList.add('hidden');

                if (fileExtension === '.pdf') {
                    mainPdfPreview.src = fileURL;
                    mainPdfPreview.classList.remove('hidden');
                    mainImagePreview.classList.add('hidden');
                    mainPreviewPlaceholder.classList.add('hidden');

                    viewFullSizeLink.href = fileURL;
                    viewFullSizeLink.classList.remove('hidden');
                } else if (['.jpg', '.jpeg', '.png', '.gif', '.tiff', '.bmp', '.webp'].includes(fileExtension)) {
                    mainImagePreview.src = fileURL;
                    mainImagePreview.classList.remove('hidden');
                    mainPdfPreview.classList.add('hidden');
                    mainPreviewPlaceholder.classList.add('hidden');

                    viewFullSizeLink.href = fileURL;
                    viewFullSizeLink.classList.remove('hidden');
                }
            } else {
                customFileText.textContent = MESSAGES.no_file_selected || "Все още не е избран файл";

                mainImagePreview.classList.add('hidden');
                mainPdfPreview.classList.add('hidden');
                mainPreviewPlaceholder.classList.remove('hidden');

                viewFullSizeLink.classList.add('hidden');
            }
        });
    }
});