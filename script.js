document.getElementById('guess-form').addEventListener('submit', (event) => {
    event.preventDefault();  // Prevent default form submission
    document.getElementById('guess').select();
});
