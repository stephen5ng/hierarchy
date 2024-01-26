document.getElementById('guess-form').addEventListener('submit', (event) => {
    event.preventDefault();  // Prevent default form submission
    const guess_element = document.getElementById('guess');
    guess_element.select();
    guessWord(guess_element.value);
});
document.documentElement.style.setProperty('--my-start-top', '10%');

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
          errors.textContent = "ERROR: " + error.message + " [" + url + "]";
        })
}

function guessWord(guess) {
  tryFetch('/guess_word?guess=' + guess)
    .then(response => {
        return response.json();
    })
    .then(data => {
        document.getElementById('status').textContent = data.status;
        if (data.score > 0) {
            diving_board_y = Math.max(0, diving_board_y - 2);
            document.documentElement.style.setProperty('--my-start-top', diving_board_y + '%');
            document.getElementById('start-line').style.top = diving_board_y + "%";
        }
    });
  tryFetch('/get_previous_guesses')
    .then(response => response.text())
    .then(previous_guesses => {
        document.getElementById('previous-guesses').textContent = previous_guesses;
    });
}

var diving_board_y = 0;
var fall_rate = 0.005;
function animationFrame() {
  const animatedObject = document.getElementById("falling-x");
  if (animatedObject == null) {
    return;
  }
  const rect = animatedObject.getBoundingClientRect();
  const y = rect.top + rect.height;
  diving_board_y += fall_rate;
  fall_rate *= 1.0003;
  document.documentElement.style.setProperty('--my-start-top', diving_board_y.toFixed(2) + '%');
  document.getElementById('start-line').style.top = (diving_board_y+12) + "%";

  if (y > 200) {
    animatedObject.remove();
    if (diving_board_y > 80) {
        document.getElementById('tiles').textContent = "GAME OVER";
        return;
    }

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