import sys
from PIL import Image, ImageDraw, ImageFont

if len(sys.argv) < 2:
    print(f"Usage: {sys.argv[0]} <text>")
    sys.exit(1)

text = sys.argv[1]
lines = text.split('\n')

img_size = 64
bg_color = (0, 0, 0)
fg_color = (255, 255, 255)
font_path = "/Library/Fonts/Arial.ttf"  # Change if needed

def get_max_font_size():
    size = img_size
    temp_width = img_size * 2
    while size > 0:
        font = ImageFont.truetype(font_path, size)
        temp_img = Image.new("L", (temp_width, img_size*2), 0)
        draw = ImageDraw.Draw(temp_img)
        y = 0
        for line in lines:
            bbox = font.getbbox(line)
            line_width = bbox[2] - bbox[0]
            x = (temp_width - line_width) // 2
            draw.text((x, y), line, font=font, fill=255)
            y += bbox[3] - bbox[1]
        bbox = temp_img.getbbox()
        if bbox:
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            if width <= img_size and height <= img_size:
                return size, font, bbox
        size -= 1
    raise RuntimeError("Could not fit text in image")

font_size, font, bbox = get_max_font_size()

temp_width = img_size * 2
temp_img = Image.new("L", (temp_width, img_size*2), 0)
draw = ImageDraw.Draw(temp_img)
y = 0
for line in lines:
    bbox_line = font.getbbox(line)
    line_width = bbox_line[2] - bbox_line[0]
    x = (temp_width - line_width) // 2
    draw.text((x, y), line, font=font, fill=255)
    y += bbox_line[3] - bbox_line[1]
cropped = temp_img.crop(temp_img.getbbox())

final_img = Image.new("RGB", (img_size, img_size), bg_color)
paste_x = (img_size - cropped.width) // 2
paste_y = (img_size - cropped.height) // 2
final_img.paste(Image.merge("RGB", (cropped, cropped, cropped)).point(lambda p: fg_color[0] if p else 0), (paste_x, paste_y), cropped)

final_img.save("output.png")
print(f"Created output.png with font size {font_size}") 