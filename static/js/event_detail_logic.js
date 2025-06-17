document.addEventListener('DOMContentLoaded', function() {
    const summaryTextarea = document.getElementById('summary_textarea');
    const eventDateInput = document.getElementById('event_date_input');
    const tagsInput = document.getElementById('tags_input');
    const saveDetailsButton = document.getElementById('save-details-button');
    const deleteButton = document.getElementById('delete-button');
    
    const eventId = saveDetailsButton ? saveDetailsButton.dataset.eventId : null;
    const documentId = deleteButton ? deleteButton.dataset.documentId : null;

    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    const languagePrefix = '/' + document.documentElement.lang;


    // --- Save Details Button Logic --


    if (saveDetailsButton) {
        saveDetailsButton.addEventListener('click', function() {
            if (!eventId) {
                alert(MESSAGES.save_error || "Error: Event ID not found for saving.");
                return;
            }

            saveDetailsButton.disabled = true;
            saveDetailsButton.innerHTML = `<span class="spinner-border spinner-border-sm"></span> ${MESSAGES.saving_text || 'Запазва се...'}`;

            const dataToSend = {
                summary: summaryTextarea ? summaryTextarea.value : '',
                event_date: eventDateInput ? eventDateInput.value : '', // YYYY-MM-DD
                tags: tagsInput ? tagsInput.value.split(',').map(tag => tag.trim()).filter(tag => tag.length > 0) : [],
            };

            fetch(`${languagePrefix}/api/update-event-details/${eventId}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(dataToSend)
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
                    alert(MESSAGES.save_success || "Промените бяха запазени успешно!");
                    window.location.reload(); // Reload to reflect changes
                } else {
                    alert(`${MESSAGES.save_error || 'Save error'}: ${data.message}`);
                }
            })
            .catch(error => {
                console.error('Save Details Error:', error);
                alert(`${MESSAGES.save_error || 'Save error'}: ${error.message}`);
            })
            .finally(() => {
                saveDetailsButton.disabled = false;
                saveDetailsButton.innerHTML = MESSAGES.save_details_button_text || 'Запази промените';
            });
        });
    }

    // --- Delete Button Logic ---
    if (deleteButton) {
        deleteButton.addEventListener('click', function() {
            if (!documentId) {
                alert(MESSAGES.delete_error || "Error: Document ID not found for deletion.");
                return;
            }

            if (!confirm(MESSAGES.confirm_delete_event || "Сигурни ли сте, че искате да изтриете това медицинско събитие и свързания с него документ?")) {
                return;
            }

            deleteButton.disabled = true;
            deleteButton.innerHTML = `<span class="spinner-border spinner-border-sm"></span> ${MESSAGES.deleting_event_text || 'Изтрива се...'}`;

            fetch(`${languagePrefix}/api/delete-document/${documentId}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'Content-Type': 'application/json'
                },
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
                    alert(MESSAGES.event_deleted_success || "Събитието и документът бяха успешно изтрити!");
                    window.location.href = data.redirect_url || '{% url "medj:history" %}'; // Redirect after deletion
                } else {
                    alert(`${MESSAGES.delete_error || 'Delete error'}: ${data.message}`);
                }
            })
            .catch(error => {
                console.error('Delete Error:', error);
                alert(`${MESSAGES.critical_delete_error || 'Critical delete error'}: ${error.message}`);
            })
            .finally(() => {
                deleteButton.disabled = false;
                deleteButton.innerHTML = MESSAGES.delete_button_text || 'Изтрий документ';
            });
        });
    }
});
