document.addEventListener('DOMContentLoaded', function() {
    const uploadContainer = document.getElementById('upload-container');
    const eventTypeSelect = document.getElementById('event-type-select');
    const categorySelect = document.getElementById('category');
    const specialtySelect = document.getElementById('specialist');
    const doctorSelect = document.getElementById('doctor-select');
    const fileInput = document.getElementById('file_input');
    const fileTypeSelect = document.getElementById('file-type-select');
    const uploadOcrButton = document.getElementById('upload-ocr-button');
    const analyzeButton = document.getElementById('analyze-button');
    const ocrTextArea = document.getElementById('ocr_text_area');

    const step1SelectionDiv = document.getElementById('step1-selection');
    const step2UploadDiv = document.getElementById('step2-upload');
    const step3ReviewDiv = document.getElementById('step3-review');

    const resultsSection = document.getElementById('results-section');
    const resultSummary = document.getElementById('result-summary');
    const resultHtmlTable = document.getElementById('result-html-table');

    const imagePreview = document.getElementById('image-preview');
    const pdfPreview = document.getElementById('pdf-preview');
    const viewFullSizeLink = document.getElementById('view-full-size-link');
    const previewPlaceholder = document.getElementById('preview-placeholder');

    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    let currentFileHash = null;

    const customFileText = document.querySelector('.custom-file-text');
    const backToUploadButton = document.getElementById('back-to-upload-button');

    // --- START DEBUGGING LOGS (keep for now, remove later) ---
    console.log("DEBUG: DOMContentLoaded fired.");
    console.log("DEBUG: eventTypeSelect:", eventTypeSelect);
    console.log("DEBUG: categorySelect:", categorySelect);
    console.log("DEBUG: specialtySelect:", specialtySelect);
    console.log("DEBUG: doctorSelect:", doctorSelect);
    console.log("DEBUG: fileInput:", fileInput);
    console.log("DEBUG: fileTypeSelect:", fileTypeSelect);
    console.log("DEBUG: uploadOcrButton:", uploadOcrButton);
    console.log("DEBUG: analyzeButton:", analyzeButton);
    console.log("DEBUG: ocrTextArea:", ocrTextArea);
    console.log("DEBUG: imagePreview:", imagePreview);
    console.log("DEBUG: pdfPreview:", pdfPreview);
    console.log("DEBUG: viewFullSizeLink:", viewFullSizeLink);
    console.log("DEBUG: previewPlaceholder:", previewPlaceholder);
    console.log("DEBUG: customFileText:", customFileText);
    console.log("DEBUG: backToUploadButton:", backToUploadButton);
    // --- END DEBUGGING LOGS ---


    let originalCategoryOptions = '';
    if (categorySelect) {
        originalCategoryOptions = categorySelect.innerHTML;
    }

    function checkOcrButtonState() {
        if (eventTypeSelect && categorySelect && specialtySelect && fileInput && fileTypeSelect) {
            if (eventTypeSelect.value && categorySelect.value && specialtySelect.value && fileInput.files.length > 0 && fileTypeSelect.value) {
                if (uploadOcrButton) {
                    uploadOcrButton.disabled = false;
                    uploadOcrButton.classList.remove('opacity-40');
                }
            } else {
                if (uploadOcrButton) {
                    uploadOcrButton.disabled = true;
                    uploadOcrButton.classList.add('opacity-40');
                }
            }
        } else {
            console.warn("DEBUG: checkOcrButtonState called but some elements are null.");
            if (uploadOcrButton) {
                uploadOcrButton.disabled = true;
                uploadOcrButton.classList.add('opacity-40');
            }
        }
    }

    function handleFileSelection() {
        if (fileInput.files.length > 0) {
            const file = fileInput.files[0];
            const reader = new FileReader();

            const allowedImageTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/tiff', 'image/webp'];
            const allowedPdfType = 'application/pdf';

            if (!allowedImageTypes.includes(file.type) && file.type !== allowedPdfType) {
                alert(MESSAGES.unsupported_file_format);
                fileInput.value = '';
                if (customFileText) customFileText.textContent = MESSAGES.no_file_chosen;
                if (imagePreview) imagePreview.classList.add('hidden');
                if (pdfPreview) pdfPreview.classList.add('hidden');
                if (viewFullSizeLink) viewFullSizeLink.classList.add('hidden');
                if (previewPlaceholder) previewPlaceholder.classList.remove('hidden');
                checkOcrButtonState();
                return;
            }

            if (customFileText) customFileText.textContent = file.name;

            reader.onload = function(e) {
                const fileURL = e.target.result;
                if (file.type === allowedPdfType) {
                    if (pdfPreview) {
                        pdfPreview.src = fileURL;
                        pdfPreview.classList.remove('hidden');
                    }
                    if (imagePreview) imagePreview.classList.add('hidden');
                } else {
                    if (imagePreview) {
                        imagePreview.src = fileURL;
                        imagePreview.classList.remove('hidden');
                    }
                    if (pdfPreview) pdfPreview.classList.add('hidden');
                }
                if (viewFullSizeLink) {
                    viewFullSizeLink.href = fileURL;
                    viewFullSizeLink.classList.remove('hidden');
                }
                if (previewPlaceholder) previewPlaceholder.classList.add('hidden');
            };
            reader.readAsDataURL(file);
        } else {
            if (customFileText) customFileText.textContent = MESSAGES.no_file_chosen;
            if (imagePreview) imagePreview.classList.add('hidden');
            if (pdfPreview) pdfPreview.classList.add('hidden');
            if (viewFullSizeLink) viewFullSizeLink.classList.add('hidden');
            if (previewPlaceholder) previewPlaceholder.classList.remove('hidden');
        }
        checkOcrButtonState();
    }

    // Initial state setup on page load
    if (categorySelect) {
        categorySelect.disabled = true;
        categorySelect.value = "";
    }
    if (specialtySelect) {
        specialtySelect.disabled = true;
        specialtySelect.innerHTML = '<option value="" disabled selected>' + MESSAGES.choose_specialty_first + '</option>';
    }
    if (uploadOcrButton) {
        uploadOcrButton.disabled = true;
        uploadOcrButton.classList.add('opacity-40');
    }
    if (viewFullSizeLink) viewFullSizeLink.classList.add('hidden');
    if (previewPlaceholder) previewPlaceholder.classList.remove('hidden');


    // Event Listeners
    if (eventTypeSelect) {
        eventTypeSelect.addEventListener('change', function() {
            if (categorySelect) {
                categorySelect.disabled = !this.value;
                categorySelect.value = "";
                categorySelect.innerHTML = originalCategoryOptions;
            }
            if (specialtySelect) {
                specialtySelect.disabled = true;
                specialtySelect.innerHTML = '<option value="" disabled selected>' + MESSAGES.choose_specialty_first + '</option>';
            }
            checkOcrButtonState();
        });
    }

    if (categorySelect) {
        categorySelect.addEventListener('change', function() {
            if (specialtySelect) {
                specialtySelect.disabled = !this.value;
                specialtySelect.innerHTML = '<option value="" disabled selected>' + MESSAGES.choose_specialty_first + '</option>';
            }
            checkOcrButtonState();

            if (this.value) {
                fetch(`/ajax/get-specialties/`)
                    .then(response => response.json())
                    .then(data => {
                        if (specialtySelect) {
                            specialtySelect.innerHTML = '<option value="" disabled selected>' + MESSAGES.choose_specialty_prompt + '</option>';
                            data.forEach(spec => {
                                const option = document.createElement('option');
                                option.value = spec.name;
                                option.textContent = spec.name;
                                specialtySelect.appendChild(option);
                            });
                        }
                    })
                    .catch(error => {
                        console.error('Error fetching specialties:', error);
                        alert(MESSAGES.error_fetching_specialties);
                    });
            }
        });
    }

    if (specialtySelect) specialtySelect.addEventListener('change', checkOcrButtonState);
    if (doctorSelect) doctorSelect.addEventListener('change', checkOcrButtonState);
    if (fileInput) fileInput.addEventListener('change', handleFileSelection);
    if (fileTypeSelect) fileTypeSelect.addEventListener('change', checkOcrButtonState);


    if (backToUploadButton) {
        backToUploadButton.addEventListener('click', function() {
            if (step3ReviewDiv) step3ReviewDiv.classList.add('hidden');
            if (resultsSection) resultsSection.classList.add('hidden');
            if (uploadContainer) uploadContainer.classList.remove('hidden');

            if (eventTypeSelect) eventTypeSelect.value = "";
            if (categorySelect) {
                categorySelect.value = "";
                categorySelect.disabled = true;
                categorySelect.innerHTML = originalCategoryOptions;
            }
            if (specialtySelect) {
                specialtySelect.value = "";
                specialtySelect.disabled = true;
                specialtySelect.innerHTML = '<option value="" disabled selected>' + MESSAGES.choose_specialty_first + '</option>';
            }
            if (doctorSelect) doctorSelect.value = "";
            if (fileTypeSelect) fileTypeSelect.value = "";

            if (fileInput) fileInput.value = '';
            if (ocrTextArea) ocrTextArea.value = '';
            if (ocrTextArea) ocrTextArea.readOnly = false;
            if (customFileText) customFileText.textContent = MESSAGES.no_file_chosen;

            if (uploadOcrButton) {
                uploadOcrButton.classList.remove('hidden');
                uploadOcrButton.innerHTML = MESSAGES.upload_button;
            }

            if (imagePreview) imagePreview.classList.add('hidden');
            if (pdfPreview) pdfPreview.classList.add('hidden');
            if (viewFullSizeLink) viewFullSizeLink.classList.add('hidden');
            if (previewPlaceholder) previewPlaceholder.classList.remove('hidden');

            checkOcrButtonState();

            if (step1SelectionDiv) step1SelectionDiv.classList.remove('hidden');
            if (step2UploadDiv) step2UploadDiv.classList.remove('hidden');
        });
    }

    checkOcrButtonState();

 if (uploadOcrButton) {
        uploadOcrButton.addEventListener('click', function() {
            if (uploadOcrButton.disabled) {
                alert(MESSAGES.choose_category_specialist_file);
                return;
            }

            console.log("DEBUG: OCR Button clicked.");
            console.log("DEBUG: fileInput:", fileInput);
            if (fileInput.files.length > 0) {
                console.log("DEBUG: File selected:", fileInput.files[0].name, fileInput.files[0].type);
            } else {
                console.error("ERROR: No file selected in fileInput.files.");
                alert(MESSAGES.no_file_chosen);
                return;
            }

            uploadOcrButton.disabled = true;
            uploadOcrButton.innerHTML = `<span class="spinner-border spinner-border-sm"></span> ${MESSAGES.processing}`;

            const formData = new FormData();
            formData.append('document', fileInput.files[0]);
            formData.append('csrfmiddlewaretoken', csrfToken); // Explicitly add CSRF token to FormData

            console.log("DEBUG: FormData content:");
            for (let pair of formData.entries()) {
                console.log(pair[0] + ', ' + pair[1]);
            }

            fetch('/api/perform-ocr/', {
                method: 'POST',
                // *** CRITICAL FIX: DO NOT set Content-Type header manually for FormData ***
                // The browser will automatically set 'multipart/form-data' with the correct boundary.
                // If you set it, it will overwrite the browser's automatic setting and break file uploads.
                // ALSO, CSRF token is now part of FormData, so no need for X-CSRFToken header.
                // If your backend still requires X-CSRFToken header, you can add it, but it's redundant with FormData.
                // For simplicity and correctness with FormData, remove X-CSRFToken from headers too.
                // If you keep X-CSRFToken, ensure it's not conflicting.

                // Simplified headers to ensure browser handles Content-Type and CSRF (if included in FormData)
                headers: {
                    // No 'Content-Type' header here
                },
                body: formData // Send FormData directly
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
                    ocrTextArea.value = data.ocr_text_for_display || MESSAGES.no_text_found;
                    ocrTextArea.readOnly = false;
                    step3ReviewDiv.classList.remove('hidden');
                    uploadOcrButton.classList.add('hidden');
                    fileInput.disabled = true;
                    currentFileHash = data.file_hash;
                } else {
                    alert(`${MESSAGES.ocr_error} ${data.message}`);
                }
            })
            .catch(error => {
                console.error('OCR Error:', error);
                alert(`${MESSAGES.critical_ocr_error} ${error.message}`);
            })
            .finally(() => {
                uploadOcrButton.disabled = false;
                uploadOcrButton.innerHTML = MESSAGES.upload_button;
            });
        });
    }



    if (analyzeButton) {
        analyzeButton.addEventListener('click', function() {
            analyzeButton.disabled = true;
            analyzeButton.innerHTML = `<span class="spinner-border spinner-border-sm"></span> ${MESSAGES.analysis_ai}`;

            // Hide previous sections
            if (step1SelectionDiv) step1SelectionDiv.classList.add('hidden');
            if (step2UploadDiv) step2UploadDiv.classList.add('hidden');
            if (step3ReviewDiv) step3ReviewDiv.classList.add('hidden');

            // Show results section and activate loading overlay
            if (resultsSection) resultsSection.classList.remove('hidden');
            if (analysisLoadingOverlay) analysisLoadingOverlay.classList.remove('hidden'); // Show loading overlay
            if (analysisResultsContent) analysisResultsContent.classList.add('hidden'); // Hide actual results content initially


            const dataToSend = {
                edited_text: ocrTextArea ? ocrTextArea.value : '',
                event_type: eventTypeSelect ? eventTypeSelect.value : '',
                category: categorySelect ? categorySelect.value : '',
                specialist: specialtySelect ? specialtySelect.value : '',
                doctor: doctorSelect ? doctorSelect.value : '',
                file_type: fileTypeSelect ? fileTypeSelect.value : '',
                file_hash: currentFileHash
            };

            fetch('/api/analyze-document/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(dataToSend)
            })
            .then(response => {
                let responseData = null;
                if (!response.ok) {
                    return response.json().then(errorData => {
                        responseData = errorData;
                        throw new Error(errorData.message || MESSAGES.unknown_server_error);
                    });
                }
                return response.json().then(successData => {
                    responseData = successData;
                    return successData;
                });
            })
            .then(data => {
                if (data.status === 'success') {
                    if (resultSummary) resultSummary.innerHTML = `<p class="mb-0">${String(data.new_document_id.summary)}</p>`;
                    if (resultHtmlTable) resultHtmlTable.innerHTML = String(data.new_document_id.html_table);
                    if (analysisResultsContent) analysisResultsContent.classList.remove('hidden'); // Show actual results content
                } else {
                    alert(`${MESSAGES.analysis_error} ${data.message}`);
                    if (resultsSection) resultsSection.classList.add('hidden'); // Hide results section on non-critical error
                }
            })
            .catch(error => {
                console.error('Analyze Error:', error);
                alert(`${MESSAGES.critical_analysis_error} ${error.message}`);
                if (resultsSection) resultsSection.classList.add('hidden'); // Hide results section on critical error
            })
            .finally(() => {
                if (analyzeButton) {
                    analyzeButton.disabled = false;
                    analyzeButton.innerHTML = MESSAGES.approve_analyze_ai;
                }
                if (analysisLoadingOverlay) analysisLoadingOverlay.classList.add('hidden'); // Hide loading overlay
            });
        });
    }
});