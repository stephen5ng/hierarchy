import platform

from PIL import Image
from pygame.image import tobytes
from pygame.time import get_ticks

if platform.system() != "Darwin":
    from rgbmatrix import graphics, RGBMatrix, RGBMatrixOptions
else:
    from RGBMatrixEmulator import graphics, RGBMatrix, RGBMatrixOptions
    import RGBMatrixEmulator
from typing import Union

from runtext import RunText

matrix: RGBMatrix = None
offscreen_canvas: Union["RGBMatrixEmulator.emulation.canvas.Canvas","RGBMatrix.Canvas"]

def init():
    global matrix, offscreen_canvas
    run_text = RunText()
    run_text.process()

    matrix = run_text.matrix
    offscreen_canvas = matrix.CreateFrameCanvas()
    font = graphics.Font()
    font.LoadFont("7x13.bdf")
    textColor = graphics.Color(255, 255, 0)
    pos = offscreen_canvas.width - 40
    my_text = "HELLO"
    graphics.DrawText(offscreen_canvas, font, pos, 10, textColor, my_text)
    offscreen_canvas = matrix.SwapOnVSync(offscreen_canvas)

last_image: bytes = b''
update_count = 0
total_time = 1
def update(screen):
    global last_image, total_time,update_count
    pixels = tobytes(screen, "RGB")
    if pixels == last_image:
        return
    last_image = pixels
    img = Image.frombytes("RGB", (screen.get_width(), screen.get_height()), pixels)

    if platform.system() != "Darwin":
# mypy: disable-error-code=attr-defined
        img = img.rotate(270, Image.NEAREST, expand=1)

    start = get_ticks()
    offscreen_canvas.SetImage(img)
    matrix.SwapOnVSync(offscreen_canvas)
    total_time += get_ticks() - start
    update_count += 1
    # print(f"fps: {1000*update_count/total_time}")