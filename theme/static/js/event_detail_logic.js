document.addEventListener('DOMContentLoaded', function() {
    const medicalEventId = document.getElementById('medical-event-id').dataset.eventId;
    const saveEventDetailsButton = document.getElementById('save-event-details-button');
    const deleteEventButton = document.getElementById('delete-event-button');
    const editBloodTestsButton = document.getElementById('edit-blood-tests-button'); // Бутон за редактиране на показатели

    const summaryInput = document.getElementById('id_summary');
    const eventDateInput = document.getElementById('id_event_date');
    const tagsInput = document.getElementById('id_tags_input'); // Предполагаме, че има инпут за тагове

    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    if (saveEventDetailsButton) {
        saveEventDetailsButton.addEventListener('click', function() {
            const payload = {
                summary: summaryInput ? summaryInput.value : '',
                event_date: eventDateInput ? eventDateInput.value : '',
                tags: tagsInput ? tagsInput.value : ''
            };

            fetch(`/api/update-event-details/${medicalEventId}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(payload)
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    alert('Успешно запазено!'); // MESSAGES.save_success
                } else {
                    alert('Грешка при запазване: ' + (data.message || 'Неизвестна грешка.')); // MESSAGES.save_error
                }
            })
            .catch(error => {
                console.error('Fetch Error:', error);
                alert('Мрежова грешка при запазване.'); // MESSAGES.network_server_error
            });
        });
    }

    if (deleteEventButton) {
        deleteEventButton.addEventListener('click', function(event) {
            event.preventDefault();
            if (confirm('Сигурни ли сте, че искате да изтриете това медицинско събитие и свързания с него документ?')) { // MESSAGES.confirm_delete_event
                fetch(`/api/delete-document/${medicalEventId}/`, { // Използваме event_id като document_id, защото source_document е OneToOne
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrfToken
                    },
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        alert('Събитието и документът бяха успешно изтрити!'); // MESSAGES.event_deleted_success
                        window.location.href = data.redirect_url;
                    } else {
                        alert('Грешка при изтриване: ' + (data.message || 'Неизвестна грешка.')); // MESSAGES.delete_error
                    }
                })
                .catch(error => {
                    console.error('Fetch Error:', error);
                    alert('Критична грешка при изтриване.'); // MESSAGES.critical_delete_error
                });
            }
        });
    }
});
