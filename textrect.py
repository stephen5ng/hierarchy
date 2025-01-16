#! /usr/bin/env python

import pygame

# https://www.pygame.org/pcr/text_rect/index.php

class TextRectException(BaseException):
    def __init__(self, message = None):
        self.message = message
    def __str__(self):
        return self.message

class TextRectRenderer():
    def __init__(self, font, rect, text_color):
        self._font = font
        self._rect = rect
        self._text_color = text_color

    def render(self, string):
        return render_textrect(string, self._font, self._rect, self._text_color)

def render_textrect(string, font, rect, text_color):
    """Returns a surface containing the passed text string, reformatted
    to fit within the given rect, word-wrapping as necessary. The text
    will be anti-aliased.

    Takes the following arguments:

    string - the text you wish to render. \n begins a new line.
    font - a Font object
    rect - a rectstyle giving the size of the surface requested.
    text_color - a three-byte tuple of the rgb value of the
                 text color. ex (0, 0, 0) = BLACK

    Returns the following values:

    Success - a surface object with the text rendered onto it.
    Failure - raises a TextRectException if the text won't fit onto the surface.
    """
    final_lines = []

    requested_lines = string.splitlines()

    # Create a series of lines that will fit on the provided
    # rectangle.

    for requested_line in requested_lines:
        if font.get_rect(requested_line).width > rect.width:
            words = requested_line.split(' ')

            # if any of our words are too long to fit, return.
            for word in words:
                if font.get_rect(word).width >= rect.width:
                    raise TextRectException("The word " + word + " is too long to fit in the rect passed.")

            # Start a new line
            accumulated_line = ""
            for word in words:
                test_line = accumulated_line + word + " "

                # Build the line while the words fit.
                if font.get_rect(test_line).width < rect.width:
                    accumulated_line = test_line
                else:
                    final_lines.append(accumulated_line)
                    accumulated_line = word + " "
            final_lines.append(accumulated_line)
        else:
            final_lines.append(requested_line)

    # Let's try to write the text out on the surface.
    surface = pygame.Surface(rect.size, pygame.SRCALPHA)

    accumulated_height = 0
    for line in final_lines:
        line_rect = font.get_rect(line)
        if accumulated_height + line_rect.height >= rect.height:
            raise TextRectException("Once word-wrapped, the text string was too tall to fit in the rect.")
        if line != "":
            tempsurface = font.render(line, text_color)[0]
            surface.blit(tempsurface, (0, accumulated_height))
        accumulated_height += line_rect.height + int(line_rect.height/3)

    return surface

def textrect_loop(my_string, my_font, my_rect):
    for i in range(1000):
        render_textrect(my_string, my_font, my_rect, (216, 216, 216))

if __name__ == '__main__':
    import cProfile
    import pygame
    import pygame.font
    import pygame.freetype
    import sys
    from pygame.locals import *

    pygame.init()

    display = pygame.display.set_mode((400, 400))

    my_font = pygame.freetype.Font(None, 22)

    my_string = "Hi there! I'm a nice bit of wordwrapped text. Won't you be my friend? Honestly, wordwrapping is easy, with David's fancy new render_textrect () function.\nThis is a new line.\n\nThis is another one.\n\n\nAnother line, you lucky dog."

    my_rect = pygame.Rect((40, 40, 300, 400))

    cProfile.run('textrect_loop(my_string, my_font, my_rect)')
    rendered_text = render_textrect(my_string, my_font, my_rect, (216, 216, 216))

    display.blit(rendered_text, my_rect.topleft)
    pygame.image.save(rendered_text, "textrect.png")

    if len(sys.argv) <= 1:
        pygame.display.update()

        while not pygame.event.wait().type in (QUIT, KEYDOWN):
            pass
