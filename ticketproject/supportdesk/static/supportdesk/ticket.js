const button = document.getElementById('check-priority');
const result = document.getElementById('priority-result');

button.addEventListener('click', async function () {
    const data = new URLSearchParams();
    data.append('severity', document.getElementById('id_severity').value);
    data.append('description', document.getElementById('id_description').value);
    const token = document.querySelector('[name=csrfmiddlewaretoken]').value;
    try {
        const response = await fetch(button.dataset.url, {
            method: 'POST',
            headers: {'X-CSRFToken': token},
            body: data
        });
        const answer = await response.json();
        result.textContent = response.ok ? 'Suggested priority: ' + answer.priority : 'Enter a valid severity and description (10–1000 characters).';
    } catch (error) {
        result.textContent = 'Could not check priority. Please try again.';
    }
});
