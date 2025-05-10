#!/usr/bin/env python3
# magick images/planets/sun.png -background black -alpha remove -depth 8 -colorspace RGB rgb:- | ./rgb888_to_rgb565.py| base64 > images/planets/sun.565.b64

import sys

data = sys.stdin.buffer.read()

out = bytearray()
for i in range(0, len(data), 3):
    r = data[i] >> 3
    g = data[i + 1] >> 2
    b = data[i + 2] >> 3
    rgb565 = (r << 11) | (g << 5) | b
    out += rgb565.to_bytes(2, byteorder="little")

sys.stdout.buffer.write(out)
