#! /usr/bin/env python

import pygame
import functools
# https://www.pygame.org/pcr/text_rect/index.php

class TextRectException(BaseException):
    def __init__(self, message = None):
        self.message = message
    def __str__(self):
        return self.message

class FontRectGetter():
    def __init__(self, font):
        self._font = font

    @functools.lru_cache(maxsize=64)
    def get_rect(self, text):
        return self._font.get_rect(text)

class Blitter():
    def __init__(self, font, color, rect):
        self._font = font
        self._color = color
        self._rect = rect

    def _render_blit(self, surface, line, height):
        tempsurface = self._font.render(line, self._color)[0]
        surface.blit(tempsurface, (0, height))
        return surface

    @functools.lru_cache(maxsize=64)
    def blit(self, lines, heights):
        if len(lines) == 0:
            return pygame.Surface(self._rect.size, pygame.SRCALPHA)
        if len(lines) == 1:
            return self._render_blit(self.blit((), ()).copy(), lines[0], heights[0])

        previous_lines_surface = self.blit(lines[:-1], heights[:-1]).copy()
        return self._render_blit(previous_lines_surface, lines[-1], heights[-1])

class TextRectRenderer():
    def __init__(self, font, rect, color):
        self._font = font
        self._rect = rect
        self._color = color
        self._font_rect_getter = FontRectGetter(font)
        self._blitter = Blitter(font, color, rect)

    def render(self, string):
        return render_textrect(string, self._blitter, self._font, self._rect, self._color, self._font_rect_getter)

def render_textrect(string, blitter, font, rect, text_color, rg):
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
        if rg.get_rect(requested_line).width > rect.width:
            words = requested_line.split(' ')

            # if any of our words are too long to fit, return.
            for word in words:
                if rg.get_rect(word).width >= rect.width:
                    raise TextRectException("The word " + word + " is too long to fit in the rect passed.")

            # Start a new line
            accumulated_line = ""
            for word in words:
                test_line = accumulated_line + word + " "

                # Build the line while the words fit.
                if rg.get_rect(test_line).width < rect.width:
                    accumulated_line = test_line
                else:
                    final_lines.append(accumulated_line[:-1])
                    accumulated_line = word + " "
            final_lines.append(accumulated_line[:-1])
        else:
            final_lines.append(requested_line)


    accumulated_height = 0
    accumulated_lines = []
    heights = []
    for line in final_lines:
        accumulated_lines.append(line)
        heights.append(accumulated_height)
        line_rect = rg.get_rect(line)
        if accumulated_height + line_rect.height >= rect.height:
            raise TextRectException("Once word-wrapped, the text string was too tall to fit in the rect.")
        accumulated_height += line_rect.height + int(line_rect.height/3)

    surface = blitter.blit(tuple(accumulated_lines), tuple(heights))

    return surface

def textrect_loop(trr, my_string):
    for i in range(1000):
        trr.render(my_string)

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
    trr = TextRectRenderer(my_font, my_rect, (216, 216, 216))
    cProfile.run('textrect_loop(trr, my_string)')
    rendered_text = trr.render(my_string)

    display.blit(rendered_text, my_rect.topleft)
    pygame.image.save(rendered_text, "textrect.png")

    if len(sys.argv) <= 1:
        pygame.display.update()

        while not pygame.event.wait().type in (QUIT, KEYDOWN):
            pass
