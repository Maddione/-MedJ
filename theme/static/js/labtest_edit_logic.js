document.addEventListener('DOMContentLoaded', function() {
    const saveButton = document.querySelector('button.bg-checkmark-green');
    const medicalEventId = document.getElementById('medical-event-id').dataset.eventId;
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    if (saveButton) {
        saveButton.addEventListener('click', function() {
            const table = document.querySelector('.grid.grid-cols-[auto_repeat(6,minmax(120px,1fr))]');
            const indicatorRows = Array.from(table.children).slice(1);

            const updatedData = [];

            const dateElements = Array.from(table.children).slice(1, 7);
            const dates = dateElements.map(el => el.textContent.trim());

            indicatorRows.forEach((row, rowIndex) => {
                const indicatorName = row.children[0].textContent.trim();

                for (let i = 1; i < row.children.length; i++) {
                    const cell = row.children[i];
                    const date = dates[i-1];
                    const value = cell.querySelector('input').value.trim();

                    if (value) {
                        updatedData.push({
                            indicator_name: indicatorName,
                            date: date,
                            value: value
                        });
                    }
                }
            });

            fetch(`/api/save-blood-tests/${medicalEventId}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ data: updatedData })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    alert('Данните са успешно запазени!');
                } else {
                    alert('Грешка при запазване: ' + (data.message || 'Неизвестна грешка.'));
                }
            })
            .catch(error => {
                console.error('Fetch Error:', error);
                alert('Мрежова грешка при запазване.');
            });
        });
    }
});
