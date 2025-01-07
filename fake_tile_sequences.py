#!/usr/bin/env python3
import random

def generate_string(length):
  """
  Generates a string of random length with no repeated characters.

  Args:
    length: The desired length of the string.

  Returns:
    A string of random length with no repeated characters.
  """
  chars = list(map(str, range(6)))  # Create a list of characters from '0' to '6'
  random.shuffle(chars)  # Shuffle the characters randomly
  return ''.join(chars[:length])  # Take the first 'length' characters

# Generate a random length between 3 and 6
random_length = random.randint(3, 6)

# Generate and print the string
generated_string = generate_string(random_length)
print(generated_string)