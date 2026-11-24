"""Emkay face screens in any aspect (same look as emkay-capsule/render/screens).
portrait.png is the capsule's own screen_face.png; the others are drawn here."""
import sys
from PIL import Image, ImageDraw, ImageFont

ROBOTO = "/usr/share/fonts/truetype/google-fonts/ofl/roboto/Roboto[wdth,wght].ttf"
BG = (5, 7, 10)


def font(size, style="Light"):
    f = ImageFont.truetype(ROBOTO, size)
    try:
        f.set_variation_by_name(style)
    except Exception:
        pass
    return f


def eye(d, cx, cy, r, t, look=0.0):
    box = [cx - r, cy - r, cx + r, cy + r]
    d.ellipse(box, fill=(110, 110, 110))
    d.pieslice(box, 180, 360, fill=(244, 244, 244))
    # rounded ends of the white half
    for x in (cx - r + t / 2, cx + r - t / 2):
        d.ellipse([x - t / 2, cy - t / 2, x + t / 2, cy + t / 2], fill=(244, 244, 244))
    ir = r - t
    d.ellipse([cx - ir + look, cy - ir, cx + ir + look, cy + ir], fill=BG)


def face(w, h, clock=True, mood="smile"):
    S = 3  # supersample
    W, H = w * S, h * S
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    u = min(W, H)
    cx, cy = W / 2, H / 2 - u * 0.02
    if clock:
        cr = u * 0.29
        d.ellipse([cx - cr, cy - cr + u * 0.05, cx + cr, cy + cr + u * 0.05],
                  outline=(10, 22, 34), width=int(u * 0.018))
        f = font(int(u * 0.15))
        d.text((cx, cy + u * 0.03), "10:21", font=f, fill=(24, 28, 34), anchor="mm")
    er, et = u * 0.105, u * 0.04
    ex = u * 0.22
    ey = cy - u * 0.13
    eye(d, cx - ex, ey, er, et)
    eye(d, cx + ex, ey, er, et)
    # mouth: half-ellipse outline
    mw, mh = u * 0.115, u * 0.085
    my = cy + u * 0.19
    t = int(u * 0.032)
    d.chord([cx - mw, my - mh, cx + mw, my + mh], 0, 180, fill=(250, 250, 250))
    d.rounded_rectangle([cx - mw, my - t / 2, cx + mw, my + t / 2], radius=t / 2, fill=(250, 250, 250))
    iw, ih = mw - t * 1.15, mh - t * 1.15
    d.chord([cx - iw, my + t * 0.5 - ih, cx + iw, my + t * 0.5 + ih], 0, 180, fill=BG)
    return im.resize((w, h), Image.LANCZOS)


if __name__ == "__main__":
    out = sys.argv[1]
    for name, (w, h) in {"tablet_land": (1600, 1000),
                         "laptop": (1600, 1000),
                         "pi": (1280, 800)}.items():
        face(w, h).save(f"{out}/{name}.png")
