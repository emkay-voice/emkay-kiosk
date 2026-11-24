"""Puts the EMKAY wordmark (emkay.ai style: light, wide letter spacing) on a render.
Usage: python3 overlay.py in.png out.png "On the wall"
Needs Roboto (variable font); set ROBOTO to its path if it lives elsewhere."""
import os
import sys
from PIL import Image, ImageDraw, ImageFont

ROBOTO = os.environ.get("ROBOTO", "/usr/share/fonts/truetype/google-fonts/ofl/roboto/Roboto[wdth,wght].ttf")


def font(size, style):
    f = ImageFont.truetype(ROBOTO, size)
    f.set_variation_by_name(style)
    return f


def spaced(draw, xy, text, f, fill, spacing):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=f, fill=fill)
        x += draw.textlength(ch, font=f) + spacing


def main(src, dst, subtitle):
    im = Image.open(src).convert("RGB")
    w, _ = im.size
    d = ImageDraw.Draw(im)
    size = int(w * 0.052)
    x0 = y0 = int(w * 0.06)
    spaced(d, (x0, y0), "EMKAY", font(size, "Light"), (20, 24, 30), size * 0.3)
    spaced(d, (x0 + 2, y0 + int(size * 1.35)), subtitle.upper(), font(int(size * 0.42), "Regular"),
           (34, 167, 240), size * 0.12)
    im.save(dst)


if __name__ == "__main__":
    main(*sys.argv[1:4])
