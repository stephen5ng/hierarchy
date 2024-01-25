document.getElementById('guess-form').addEventListener('submit', (event) => {
    event.preventDefault();  // Prevent default form submission
    const guess_element = document.getElementById('guess');
    guess_element.select();
    guessWord(guess_element.value);
});

function tryFetch(url) {
    return fetch(url)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response;
        })    
        .catch(error => {
          const errors = document.getElementById("errors");
          errors.textContent = "ERROR:" + error.message + "fetching " + url;
        })
}

function guessWord(guess) {
  tryFetch('/guess_word?guess=' + guess)
    .then(response => response.text())
    .then(status => {
        document.getElementById('status').textContent = status;
    })
}

function animationFrame() {
  const animatedObject = document.getElementById("falling-x");
  if (animatedObject == null) {
    return;
  }
  const rect = animatedObject.getBoundingClientRect();
  const y = rect.top + rect.height;

  if (y > 200) {
    animatedObject.remove();
    tryFetch('/get_tiles?next_tile=' + animatedObject.textContent)
        .then(response => response.text())
        .then(new_tiles => {
            document.getElementById('tiles').textContent = new_tiles;
        });
    tryFetch('/next_tile')
        .then(response => response.text())
        .then(next_tile => {
            animatedObject.textContent = next_tile;
        });

    document.getElementById("container").appendChild(animatedObject);
  }
  requestAnimationFrame(animationFrame);
}

requestAnimationFrame(animationFrame);