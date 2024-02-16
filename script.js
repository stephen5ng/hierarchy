const INITIAL_FALL_RATE = 0.005;
const INITIAL_LETTER_FALL_TIME = 10;
const MAX_LETTERS = 6;
var diving_board_y = 0;
var fall_rate = INITIAL_FALL_RATE;
var letter_fall_time = INITIAL_LETTER_FALL_TIME;
document.documentElement.style.setProperty('--my-start-top', '10%');

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
          errors.textContent = "ERROR: " + error.message + " [" + url + "]";
        })
}

function guessWord(guess) {
  tryFetch('/guess_word?guess=' + guess + "&bonus=" + (diving_board_y <= 3))
    .then(response => {
        return response.json();
    })
    .then(data => {
        document.getElementById('tiles').innerHTML = data.tiles;
        current_score = data.current_score;
        if (data.current_score > 0) {
            diving_board_y = Math.max(0, diving_board_y - current_score/2);
            if (guess.length == MAX_LETTERS) { // Reset on bingo
                fall_rate = INITIAL_FALL_RATE;
                letter_fall_time = INITIAL_LETTER_FALL_TIME;
                diving_board_y = 0;
            }
            document.documentElement.style.setProperty('--my-start-top', diving_board_y + '%');
            document.getElementById('start-line').style.top = diving_board_y + "%";
            document.getElementById('score').innerHTML = "<span style=red>" + data.score + "</span>";

            const falling_x = document.getElementById("falling-x");
            falling_x.remove();
            document.getElementById("vertical-panel").appendChild(falling_x);
            falling_x.offsetHeight;
        }
    });

  tryFetch('/get_previous_guesses')
    .then(response => response.text())
    .then(previous_guesses => {
        document.getElementById('previous-guesses').textContent = previous_guesses;
    });
}

function acceptNewLetter(animatedObject) {
    animatedObject.remove();

    tryFetch('/get_rack?next_letter=' + animatedObject.textContent)
        .then(response => response.text())
        .then(new_tiles => {
            document.getElementById('tiles').textContent = new_tiles;
        });
    tryFetch('/next_tile')
        .then(response => response.text())
        .then(next_tile => {
            animatedObject.textContent = next_tile;
        });

    tryFetch('/get_previous_guesses')
        .then(response => response.text())
        .then(previous_guesses => {
            document.getElementById('previous-guesses').textContent = previous_guesses;
        });
    document.getElementById("vertical-panel").appendChild(animatedObject);
}

function animationFrame() {
  const animatedObject = document.getElementById("falling-x");
  if (animatedObject == null) {
    return;
  }
  const rect = animatedObject.getBoundingClientRect();
  const y = animatedObject.offsetTop + rect.height;  
  diving_board_y += fall_rate;
  document.documentElement.style.setProperty('--my-start-top', diving_board_y.toFixed(2) + '%');
  document.documentElement.style.setProperty('--letter-fall-time', letter_fall_time.toFixed(2) + 's');
  document.getElementById('start-line').style.top = (diving_board_y+12) + "%";

  if (y > 410) {
    if (diving_board_y > 160) {
        animatedObject.remove();
        document.getElementById('tiles').textContent = "GAME OVER";
        document.getElementById('play').setAttribute('disabled', true);
        document.getElementById('guess').setAttribute('disabled', true);
        return;
    }
    fall_rate *= 1.1;
    letter_fall_time *= 0.9;

    acceptNewLetter(animatedObject);
  }
  requestAnimationFrame(animationFrame);
}

requestAnimationFrame(animationFrame);