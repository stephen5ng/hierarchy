from collections import Counter
import random

MAX_LETTERS = 6
SCRABBLE_LETTER_FREQUENCIES = Counter({
    'A': 9, 'B': 2, 'C': 2, 'D': 4, 'E': 12, 'F': 2, 'G': 3, 'H': 2, 'I': 9, 'J': 1, 'K': 1, 'L': 4, 'M': 2,
    'N': 6, 'O': 8, 'P': 2, 'R': 6, 'S': 4, 'T': 6, 'U': 4, 'V': 2, 'W': 2, 'X': 1, 'Y': 2, 'Z': 1
})
BAG_SIZE = sum(SCRABBLE_LETTER_FREQUENCIES.values())

def remove_letters(source_string, letters_to_remove):
    for char in letters_to_remove:
        source_string = source_string.replace(char, '', 1)
    return source_string

class Tiles:
    def __init__(self, letters):
        self._letters = letters
        self._last_guess = ""
        self._unused_letters = letters
        self._used_counter = Counter(set(self._letters))

    def last_guess(self):
        return self._last_guess

    def unused_letters(self):
        return self._unused_letters

    def display(self):
        return f"{self._last_guess} {self._unused_letters}"

    def guess(self, guess):
        self._last_guess = guess
        self._unused_letters = remove_letters(self._letters, guess)
        self._used_counter.update(guess)
        print(f"guess({guess}): Counter: {self._used_counter}")

    def missing_letters(self, word):
        rack_hash = Counter(self._letters)
        word_hash = Counter(word)
        if all(word_hash[letter] <= rack_hash[letter] for letter in word):
            return ""
        else:
            return "".join([l for l in word_hash if word_hash[l] > rack_hash[l]])

    def letters(self):
        return self._letters

    def next_letter(self):
        c = Counter(self._letters)
        for k in c.keys():
            c[k] *= int(BAG_SIZE / MAX_LETTERS)
        frequencies = Counter(SCRABBLE_LETTER_FREQUENCIES) # make a copy
        frequencies.subtract(c)

        bag = [letter for letter, frequency in frequencies.items() for _ in range(frequency)]
        return random.choice(bag)

    def replace_letter(self, new_letter):
        # new_letter_html = f"<span style='blue'><bold>{new_letter}</bold></span>"
        print(f"replace_letter() new_letter: {new_letter}, last_guess: {self._last_guess}, unused: {self._unused_letters}, used_counter: {self._used_counter}")
        if self._unused_letters:
            lowest_count = self._used_counter.most_common()[-1][1]
            # Counter ordering is non-deterministic; sort so that tests will be consistent.
            least_used_letters = sorted([c[0] for c in self._used_counter if self._used_counter[c] == lowest_count])
            remove_letter = random.choice(least_used_letters)
            print(f"removing: {remove_letter} from {least_used_letters}")
            if remove_letter in self._unused_letters:
                remove_ix = self._unused_letters.index(remove_letter)
                self._unused_letters = "".join(self._unused_letters[:remove_ix] + new_letter +
                    self._unused_letters[remove_ix+1:])
            else:
                remove_ix = self._last_guess.index(remove_letter)
                self._last_guess = (self._last_guess[:remove_ix] + self._last_guess[remove_ix+1:])
                self._unused_letters = "".join(self._unused_letters + new_letter)
            print(f"least_used_letters: {least_used_letters}, remove_letter: {remove_letter}, last_guess: {self._last_guess}, unused: {self._unused_letters}")
        else:
            print(f"no unused letters")
            remove_ix = random.randint(0, len(self._last_guess)-1)
            self._last_guess = self._last_guess[:remove_ix] + self._last_guess[remove_ix+1:]
            self._unused_letters = new_letter

        self._letters = self._last_guess + self._unused_letters

        # Initialize so that each letter appears at least once.
        self._used_counter = Counter(set(self._letters))
        print(f"replace_letter() done used: {self._used_counter}, last guess: {self._last_guess}, unused: {self._unused_letters}")
        return self.display()
