"""Build the bsc_thesis page figures from the images embedded in the thesis PDF.

    pdfimages -f 18 -l 25 -png thesis.pdf "$THESIS_IMG/i"
    THESIS_IMG=... python3 tools/bsc_thesis/make_figures.py

Only photos and SolidWorks renders are used; the Chinese labels of the
original figures are replaced by English ones drawn here.
"""
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

SRC = Path(os.environ["THESIS_IMG"])
OUT = Path(__file__).resolve().parents[2] / "images" / "bsc_thesis"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
INK = (68, 68, 68)


def img(i, mask=None):
    """Embedded image i, composited on white if it has a soft mask (pdfimages writes it as i+1)."""
    im = Image.open(SRC / f"i-{i:03d}.png").convert("RGB")
    if mask is not None:
        a = Image.open(SRC / f"i-{mask:03d}.png").convert("L")
        bg = Image.new("RGB", im.size, "white")
        bg.paste(im, (0, 0), a)
        im = bg
    return im


def fit_h(im, h):
    return im.resize((round(im.width * h / im.height), h), Image.LANCZOS)


def fit_w(im, w):
    return im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)


def text_c(d, xc, y, s, font):
    w = d.textlength(s, font=font)
    d.text((xc - w / 2, y), s, fill=INK, font=font)


def save(im, name):
    p = OUT / name
    im.save(p, quality=88, optimize=True) if p.suffix == ".jpg" else im.save(p, optimize=True)
    print(p.name, im.size, p.stat().st_size // 1024, "KB")


OUT.mkdir(parents=True, exist_ok=True)
f22 = ImageFont.truetype(FONT, 22)
f24 = ImageFont.truetype(FONT, 24)
f28 = ImageFont.truetype(FONT, 28)

# --- rig photo (thesis Fig. 3.8): page teaser + 16:9 homepage thumbnail
rig = img(22)
save(rig, "rig.jpg")
save(rig.crop((0, 22, 694, 412)), "thumb.jpg")

# --- elements (Fig. 3.1): photo + model, plain alloy element vs element with a PTFE block
pairs = [(img(0), img(2, 3), "Alloy element"), (img(4), img(6, 7), "Element with a PTFE block")]
H, gap, pad, lab = 400, 16, 60, 44
tiles = []
for photo, cad, label in pairs:
    photo, cad = fit_h(photo, round(H * 0.72)), fit_h(cad, H)
    t = Image.new("RGB", (photo.width + gap + cad.width, H + lab), "white")
    t.paste(photo, (0, H - photo.height - 12))
    t.paste(cad, (photo.width + gap, 0))
    text_c(ImageDraw.Draw(t), t.width / 2, H + 10, label, f24)
    tiles.append(t)
W = sum(t.width for t in tiles) + pad
el = Image.new("RGB", (W, H + lab), "white")
el.paste(tiles[0], (0, 0)); el.paste(tiles[1], (tiles[0].width + pad, 0))
save(el, "elements.jpg")

# --- units (Fig. 3.2) + their arrangement in the tank (Fig. 3.3)
strips = [fit_h(img(i), 400) for i in (8, 9, 10, 11)]
arr = fit_h(img(12, 13), 440)
sw = sum(s.width for s in strips) + 3 * 22
un = Image.new("RGB", (sw + 70 + arr.width, 440 + 36), "white")
d = ImageDraw.Draw(un)
x = 0
for k, s in enumerate(strips):
    un.paste(s, (x, 0))
    text_c(d, x + s.width / 2, 410, f"{k} slot" + ("" if k == 1 else "s"), f22)
    x += s.width + 22
un.paste(arr, (sw + 70, 0))
save(un, "units.jpg")

# --- design (Figs. 3.5-3.7): rig model, motor bracket (alone / on the lid), impeller
model = fit_h(img(15, 16), 560)
br1, br2 = fit_w(img(17), 400), fit_w(img(18, 19), 400)
imp = fit_h(img(20, 21), 400)
g = 50
dz = Image.new("RGB", (model.width + g + 400 + g + imp.width, 560 + 42), "white")
d = ImageDraw.Draw(dz)
dz.paste(model, (0, 0))
x = model.width + g
dz.paste(br1, (x, 20)); dz.paste(br2, (x, 560 - br2.height))
dz.paste(imp, (x + 400 + g, (560 - imp.height) // 2 + 40))
for xc, s in ((model.width / 2, "(a)"), (x + 200, "(b)"), (x + 400 + g + imp.width / 2, "(c)")):
    text_c(d, xc, 568, s, f24)
save(dz, "design.jpg")

# --- coupons every 2 h (Fig. 3.9): rows = groups, columns = time
rows = ["Blank", "Alloy only", "10 PTFE", "20 PTFE", "30 PTFE"]
CW, CH, LW, TH = 72, 362, 170, 44
cp = Image.new("RGB", (LW + 10 * CW, TH + 5 * CH), "white")
d = ImageDraw.Draw(cp)
for c in range(10):
    text_c(d, LW + c * CW + CW / 2, 8, f"{2 * (c + 1)} h", f24)
for r, name in enumerate(rows):
    y0 = TH + r * CH
    d.text((6, y0 + CH / 2 - 16), name, fill=INK, font=f28)
    for c in range(10):
        s = img(23 + 10 * r + c)
        s = s.resize((62, 346), Image.LANCZOS)
        cp.paste(s, (LW + c * CW + 5, y0 + 4))
save(cp, "coupons.jpg")
