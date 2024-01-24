document.getElementById('guess-form').addEventListener('submit', (event) => {
    event.preventDefault();  // Prevent default form submission
    const guess_element = document.getElementById('guess');
    guess_element.select();
    guessWord(guess_element.value);
});

function guessWord(guess) {
  fetch('/guess_word?guess=' + guess)
    .then(response => response.text())
    .then(status => {
        document.getElementById('status').textContent = status;
    })
}
