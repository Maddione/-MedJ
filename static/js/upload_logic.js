document.addEventListener('DOMContentLoaded', function() {
    const uploadContainer = document.getElementById('upload-container');
    const categorySelect = document.getElementById('category');
    const specialistSelect = document.getElementById('specialist');
    const fileInput = document.getElementById('file_input');
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

    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    let currentFileHash = null;

    // Elements for custom file input
    const customFileText = document.querySelector('.custom-file-text');

    // New: Back button
    const backToUploadButton = document.getElementById('back-to-upload-button');

    // MESSAGES object must be defined in the HTML before this script
    // Example: <script>const MESSAGES = { unsupported_file_format: "...", /* etc. */ };</script>


    function checkOcrButtonState() {
        if (categorySelect.value && specialistSelect.value && fileInput.files.length > 0) {
            uploadOcrButton.disabled = false;
            uploadOcrButton.classList.remove('opacity-50');
        } else {
            uploadOcrButton.disabled = true;
            uploadOcrButton.classList.add('opacity-50');
        }
    }

    function handleFileSelection() {
        if (fileInput.files.length > 0) {
            const file = fileInput.files[0];
            const reader = new FileReader();

            // Проверка за поддържани файлови типове
            const allowedTypes = [
                'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/tiff', 'image/webp', 'application/pdf'
            ];
            if (!allowedTypes.includes(file.type)) {
                // Използвай MESSAGES променливата от HTML
                alert(MESSAGES.unsupported_file_format);
                fileInput.value = ''; // Изчистване на избрания файл
                customFileText.textContent = MESSAGES.no_file_chosen;
                checkOcrButtonState();
                return;
            }

            customFileText.textContent = file.name;

            reader.onload = function(e) {
                if (file.type === "application/pdf") {
                    pdfPreview.src = e.target.result;
                    pdfPreview.classList.remove('hidden');
                    imagePreview.classList.add('hidden');
                } else {
                    imagePreview.src = e.target.result;
                    imagePreview.classList.remove('hidden');
                    pdfPreview.classList.add('hidden');
                }
            };
            reader.readAsDataURL(file);
        } else {
            customFileText.textContent = MESSAGES.no_file_chosen;
        }
        checkOcrButtonState();
    }

    categorySelect.addEventListener('change', checkOcrButtonState);
    specialistSelect.addEventListener('change', checkOcrButtonState);
    fileInput.addEventListener('change', handleFileSelection);

    if (backToUploadButton) {
        backToUploadButton.addEventListener('click', function() {
            step3ReviewDiv.classList.add('hidden'); // Hide step 3
            uploadContainer.classList.remove('hidden'); // Show original upload container (which contains steps 1 & 2)

            // Reset fields and states
            fileInput.value = ''; // Clear selected file
            fileInput.disabled = false; // Re-enable file input
            ocrTextArea.value = ''; // Clear OCR text area
            customFileText.textContent = MESSAGES.no_file_chosen; // Reset custom file input text
            uploadOcrButton.classList.remove('hidden'); // Show OCR button again
            checkOcrButtonState(); // Re-check button state (will be disabled initially)

            // Hide preview
            imagePreview.classList.add('hidden');
            pdfPreview.classList.add('hidden');

            // Ensure step1SelectionDiv and step2UploadDiv are visible (they should be already as they are part of uploadContainer)
            step1SelectionDiv.classList.remove('hidden');
            step2UploadDiv.classList.remove('hidden');
        });
    }

    checkOcrButtonState();

    uploadOcrButton.addEventListener('click', function() {
        if (uploadOcrButton.disabled) {
            alert(MESSAGES.choose_category_specialist_file);
            return;
        }

        uploadOcrButton.disabled = true;
        uploadOcrButton.innerHTML = `<span class="spinner-border spinner-border-sm"></span> ${MESSAGES.processing}`;

        const formData = new FormData();
        formData.append('document', fileInput.files[0]);

        fetch('/api/perform-ocr/', {
            method: 'POST',
            headers: { 'X-CSRFToken': csrfToken },
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                if (response.status === 400 || response.status === 500 || response.status === 409) {
                    return response.json().then(errorData => {
                        throw new Error(errorData.message || MESSAGES.unknown_server_error);
                    });
                }
                throw new Error(MESSAGES.network_server_error);
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                // ocr_text вече е под data.ocr_text_for_display от perform_ocr
                ocrTextArea.value = data.ocr_text_for_display || MESSAGES.no_text_found;
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

    analyzeButton.addEventListener('click', function() {
        analyzeButton.disabled = true;
        analyzeButton.innerHTML = `<span class="spinner-border spinner-border-sm"></span> ${MESSAGES.analysis_ai}`;
        resultsSection.classList.add('hidden');

        const dataToSend = {
            edited_text: ocrTextArea.value,
            category: categorySelect.value,
            specialist: specialistSelect.value,
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
            if (!response.ok) {
                if (response.status === 400 || response.status === 500 || response.status === 409) {
                    return response.json().then(errorData => {
                        throw new Error(errorData.message || MESSAGES.unknown_server_error);
                    });
                }
                throw new Error(MESSAGES.network_server_error);
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                // Достъпваме 'summary' и 'html_table' през 'new_document_id'
                resultSummary.innerHTML = `<p class="mb-0">${data.new_document_id.summary}</p>`;
                resultHtmlTable.innerHTML = data.new_document_id.html_table;
                resultsSection.classList.remove('hidden');
                uploadContainer.classList.add('hidden');
            } else {
                alert(`${MESSAGES.analysis_error} ${data.message}`);
            }
        })
        .catch(error => {
            console.error('Analyze Error:', error);
            alert(`${MESSAGES.critical_analysis_error} ${error.message}`);
        })
        .finally(() => {
            analyzeButton.disabled = false;
            analyzeButton.innerHTML = '{% trans "Одобри и анализирай с AI" %}';
        });
    });
});