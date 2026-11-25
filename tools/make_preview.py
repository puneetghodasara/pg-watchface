"""Turns a watch screenshot into proj/res/drawable/preview.png (the face picker thumbnail).

Usage: .venv/bin/python tools/make_preview.py <screenshot.png>
Capture one first with:  platform-tools/adb exec-out screencap -p > shot.png
Removes Samsung's orange notification dot (system overlay, not part of the face) and masks to the round dial.
"""
import sys
from PIL import Image, ImageDraw

im = Image.open(sys.argv[1]).convert('RGB').resize((450, 450))
px = im.load()
# notification dot: saturated orange pixels near the left edge, mid-height
for y in range(200, 250):
    for x in range(0, 40):
        r, g, b = px[x, y]
        if r > 40 and r > g + 15 and r > b + 20:
            px[x, y] = (0, 0, 0)
mask = Image.new('L', (450, 450), 0)
ImageDraw.Draw(mask).ellipse((0, 0, 449, 449), fill=255)
out = Image.new('RGBA', (450, 450), (0, 0, 0, 0))
out.paste(im, (0, 0), mask)
out.save('proj/res/drawable/preview.png')
print('wrote proj/res/drawable/preview.png')
