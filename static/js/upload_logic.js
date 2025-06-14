document.addEventListener('DOMContentLoaded', function () {
    // Елементи
    const uploadStateDiv = document.getElementById('upload-state');
    const reviewStateDiv = document.getElementById('review-state');
    const categorySelect = document.getElementById('category');
    const specialistSelect = document.getElementById('specialist');
    const fileInput = document.getElementById('file_input');
    const uploadOcrButton = document.getElementById('upload-ocr-button');
    const imagePreview = document.getElementById('image-preview');
    const rawOcrOutput = document.getElementById('raw-ocr-output');
    const ocrTextArea = document.getElementById('ocr_text_area');
    const analyzeButton = document.getElementById('analyze-button');
    const categoryReview = document.getElementById('category-review');
    const specialistReview = document.getElementById('specialist-review');
    const errorMessageDiv = document.getElementById('error-message');
    const summaryMessageDiv = document.getElementById('summary-message');
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    let currentFileHash = null;

    // Проверка дали всички основни елементи са намерени
    if (!uploadOcrButton || !analyzeButton || !categorySelect || !specialistSelect || !fileInput || !csrfToken) {
        console.error("Един или повече HTML елементи не са намерени. Проверете 'id'-тата в upload.html.");
        return;
    }

    function showError(message) {
        errorMessageDiv.textContent = message;
        errorMessageDiv.style.display = 'block';
    }

    function hideError() {
        errorMessageDiv.style.display = 'none';
    }

    uploadOcrButton.addEventListener('click', function () {
        if (!fileInput.files.length || !categorySelect.value || !specialistSelect.value) {
            showError('Моля, изберете вид документ, специалист и файл.');
            return;
        }
        hideError();
        this.disabled = true;
        this.innerHTML = `Обработка...`;

        const formData = new FormData();
        formData.append('document', fileInput.files[0]);

        fetch('/api/perform-ocr/', {
            method: 'POST',
            headers: { 'X-CSRFToken': csrfToken },
            body: formData
        })
        .then(response => response.json().then(data => ({ ok: response.ok, data })))
        .then(({ ok, data }) => {
            if (!ok) throw new Error(data.message);

            uploadStateDiv.style.display = 'none';
            reviewStateDiv.style.display = 'block';

            ocrTextArea.value = data.ocr_text;
            rawOcrOutput.textContent = data.ocr_text;
            currentFileHash = data.file_hash;

            categoryReview.value = categorySelect.options[categorySelect.selectedIndex].text;
            specialistReview.value = specialistSelect.options[specialistSelect.selectedIndex].text;

            if (fileInput.files[0] && fileInput.files[0].type.startsWith('image/')) {
                imagePreview.style.display = 'block';
                const reader = new FileReader();
                reader.onload = e => { imagePreview.src = e.target.result; };
                reader.readAsDataURL(fileInput.files[0]);
            } else {
                imagePreview.style.display = 'none';
            }
        })
        .catch(err => {
            showError(err.message);
            this.disabled = false;
            this.innerHTML = `Качи`;
        });
    });

    analyzeButton.addEventListener('click', function () {
        hideError();
        this.disabled = true;
        this.innerHTML = `Анализ с AI...`;

        const dataToSend = {
            edited_text: ocrTextArea.value,
            category: categorySelect.value,
            specialist: specialistSelect.value,
            file_hash: currentFileHash
        };

        fetch('/api/analyze-document/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
            body: JSON.stringify(dataToSend)
        })
        .then(response => response.json().then(data => ({ ok: response.ok, data })))
        .then(({ ok, data }) => {
            if (!ok) throw new Error(data.message);
           //window.location.href = `/document/${data.new_document_id}/`;
            console.log(data)
            summaryMessageDiv.style.display = 'block';
            summaryMessageDiv.innerHTML = data.new_document_id.summary;
        })
        .catch(err => {
            showError(err.message);
            this.disabled = false;
            this.innerHTML = `Одобри и анализирай...`;
        });
    });
});