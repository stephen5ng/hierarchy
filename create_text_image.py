import sys
from PIL import Image, ImageDraw, ImageFont
import os

if len(sys.argv) < 2:
    print(f"Usage: {sys.argv[0]} <text>")
    sys.exit(1)

text = sys.argv[1]
lines = text.split('\n')

# Settings
img_size = 64
bg_color = (0, 0, 0)
fg_color = (255, 255, 255)
font_path = "/Library/Fonts/Arial.ttf"  # Change if needed

# Find the largest font size that fits
def get_max_font_size():
    size = img_size
    while size > 0:
        font = ImageFont.truetype(font_path, size)
        line_heights = [font.getbbox(line)[3] - font.getbbox(line)[1] for line in lines]
        total_height = sum(line_heights)
        max_width = max([font.getbbox(line)[2] - font.getbbox(line)[0] for line in lines])
        if total_height <= img_size and max_width <= img_size:
            return size, line_heights
        size -= 1
    raise RuntimeError("Could not fit text in image")

font_size, line_heights = get_max_font_size()
font = ImageFont.truetype(font_path, font_size)

# Create image
img = Image.new("RGB", (img_size, img_size), bg_color)
draw = ImageDraw.Draw(img)

y = (img_size - sum(line_heights)) // 2  # Center vertically
for i, line in enumerate(lines):
    w = font.getbbox(line)[2] - font.getbbox(line)[0]
    x = (img_size - w) // 2  # Center horizontally
    draw.text((x, y), line, font=font, fill=fg_color)
    y += line_heights[i]  # No extra spacing

img.save("output.png")
print(f"Created output.png with font size {font_size}") 