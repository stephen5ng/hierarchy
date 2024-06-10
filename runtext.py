#!/usr/bin/env python
# Display a runtext with double-buffering.
from samplebase import SampleBase
from rgbmatrix import graphics
import time


class RunText(SampleBase):
    def __init__(self, *args, **kwargs):
        super(RunText, self).__init__(*args, **kwargs)
        self.parser.add_argument("-t", "--text", help="The text to scroll on the RGB LED panel", default="Hello world!")

    def run(self, offscreen_canvas, font, textColor, pos, my_text):
#        offscreen_canvas = self.matrix.CreateFrameCanvas()
#        font = graphics.Font()
#        font.LoadFont("7x13.bdf")
#        textColor = graphics.Color(255, 255, 0)
#        pos = offscreen_canvas.width
#        my_text = self.args.text
#        pos -= 40
#        len = graphics.DrawText(offscreen_canvas, font, pos, 10, textColor, my_text)
#        offscreen_canvas = self.matrix.SwapOnVSync(offscreen_canvas)
        time.sleep(40)
        return
        while True:
            offscreen_canvas.Clear()
            len = graphics.DrawText(offscreen_canvas, font, pos, 10, textColor, my_text)
            pos -= 1
            if (pos + len < 0):
                pos = offscreen_canvas.width

            offscreen_canvas = self.matrix.SwapOnVSync(offscreen_canvas)
            time.sleep(0.05)
            time.sleep(100)
            return

# Main function
if __name__ == "__main__":
    run_text = RunText()
    if (not run_text.process()):
        run_text.print_help()
