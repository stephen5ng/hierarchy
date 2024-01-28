var diving_board_y = 0;
var fall_rate = 0.005;

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
  tryFetch('/guess_word?guess=' + guess + "&bonus=" + (diving_board_y <= 5))
    .then(response => {
        return response.json();
    })
    .then(data => {
        document.getElementById('status').innerHTML = data.status;
        current_score = data.current_score;
        if (data.current_score > 0) {
            diving_board_y = Math.max(0, diving_board_y - current_score);
            document.documentElement.style.setProperty('--my-start-top', diving_board_y + '%');
            document.getElementById('start-line').style.top = diving_board_y + "%";
            document.getElementById('score').innerHTML = "<span style=red>" + data.score + "</span>";
            document.getElementById('tiles').textContent = data.tiles;
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

function resetLetter(animatedObject) {
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
  fall_rate *= 1.0001;
  document.documentElement.style.setProperty('--my-start-top', diving_board_y.toFixed(2) + '%');
  document.getElementById('start-line').style.top = (diving_board_y+12) + "%";

  if (y > 205) {
    if (diving_board_y > 80) {
        animatedObject.remove();
        document.getElementById('tiles').textContent = "GAME OVER";
        document.getElementById('play').setAttribute('disabled', true);
        document.getElementById('guess').setAttribute('disabled', true);
        return;
    }

    resetLetter(animatedObject);
  }
  requestAnimationFrame(animationFrame);
}

requestAnimationFrame(animationFrame);