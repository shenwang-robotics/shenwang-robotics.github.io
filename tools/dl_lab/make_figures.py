"""Result figures for projects/dl_lab/.

- pred_id.png    slide 18 of the final deck (in-distribution PoliMi test), title cropped, axes relabelled
- ood_idsia.png  slide 19 of the final deck (a test sequence from the IDSIA dataset), same clean-up, and the
                 legend rebuilt because it showed an internal file name instead of "Ground Truth"

The deck comes from an environment variable so no private path is written here:
  DL_PPTX  final presentation (.pptx)

Run with any Python that has numpy, matplotlib, Pillow and python-pptx:
  DL_PPTX=... python3 tools/dl_lab/make_figures.py
"""
import io
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation

OUT = Path(__file__).resolve().parents[2] / "images" / "dl_lab"
PPTX = Path(os.environ["DL_PPTX"]).expanduser()

DPI = 300                   # the slide plots are matplotlib figures saved at 300 dpi
FONT = Path(matplotlib.get_data_path()) / "fonts" / "ttf" / "DejaVuSans.ttf"
FONT_PX = round(10 * DPI / 72)  # matplotlib's default 10 pt label size at that dpi
OUT_WIDTH = 1800
TITLE_END = 78              # rows 0..77 of the slide plots hold the "Original Data Plot" title


def slide_picture(n):
    slide = Presentation(PPTX).slides[n - 1]
    pic = next(s for s in slide.shapes if s.shape_type == 13)
    return Image.open(io.BytesIO(pic.image.blob)).convert("RGB")


def ink_box(a, x0, y0, x1, y1):
    """Bounding box of dark pixels inside a region, in full-image coordinates."""
    ys, xs = np.nonzero(a[y0:y1, x0:x1].min(axis=2) < 128)
    return x0 + xs.min(), y0 + ys.min(), x0 + xs.max() + 1, y0 + ys.max() + 1


def text_image(text):
    font = ImageFont.truetype(str(FONT), FONT_PX)
    l, t, r, b = font.getbbox(text)
    im = Image.new("RGB", (r - l, b - t), "white")
    ImageDraw.Draw(im).text((-l, -t), text, font=font, fill="black")
    return im


def relabel(im, xlabel, ylabel):
    """Replace matplotlib's 'Index' / 'Value' axis labels with real ones, same font and size."""
    a = np.asarray(im)
    h, w = a.shape[:2]
    for text, box, rotate in (
        (xlabel, ink_box(a, 0, h - 80, w, h), False),
        (ylabel, ink_box(a, 0, 0, 70, h), True),
    ):
        x0, y0, x1, y1 = box
        ImageDraw.Draw(im).rectangle((x0 - 2, y0 - 2, x1 + 2, y1 + 2), fill="white")
        t = text_image(text)
        if rotate:
            t = t.rotate(90, expand=True)
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        im.paste(t, (cx - t.width // 2, cy - t.height // 2))
    return im


def finish(im, name):
    im = im.crop((0, TITLE_END, im.width, im.height))
    pad = Image.new("RGB", (im.width, im.height + 16), "white")
    pad.paste(im, (0, 16))
    out = pad.resize((OUT_WIDTH, round(pad.height * OUT_WIDTH / pad.width)), Image.LANCZOS)
    out.save(OUT / name, optimize=True)
    print(OUT / name, out.size)


HANDLES = [
    ("Ground Truth", dict(color="black", lw=2)),
    ("Data Driven", dict(color="gray", lw=1, ls="--")),
    ("Hunt Crossley", dict(color="tab:orange", lw=1)),
    ("MCK Matrix", dict(color="tab:green", lw=1)),
    ("MCK", dict(color="tab:blue", lw=1)),
]


def legend_image(entries):
    fig = plt.figure(figsize=(6, 4), dpi=DPI)
    leg = fig.legend([Line2D([], [], **kw) for _, kw in entries], [n for n, _ in entries], loc="center")
    fig.canvas.draw()
    bbox = leg.get_window_extent().padded(2).transformed(fig.dpi_scale_trans.inverted())
    buf = io.BytesIO()
    fig.savefig(buf, dpi=DPI, transparent=True, bbox_inches=bbox)
    plt.close(fig)
    return Image.open(buf).convert("RGBA")


def fix_idsia_legend(im):
    """Slide 19's legend listed the ground truth under its CSV file name. Clear the old legend, restore the
    grid lines it covered, and draw a legend with the same entries in the order used on slide 18."""
    GRID = (231, 231, 231)
    left, top, right, bottom = 3700, 104, 4600, 447   # old legend box (outer edge 3709..4593 x 111..442) + margin
    a = np.asarray(im)
    region = a[top:bottom, left:right].min(axis=2)
    outside = np.ones_like(region, bool)
    outside[111 - top:443 - top, 3709 - left:4594 - left] = False
    assert region[outside].min() >= 225, "a curve runs next to the legend; only grid and white may be cleared"
    d = ImageDraw.Draw(im)
    d.rectangle((left, top, right - 1, bottom - 1), fill="white")
    d.rectangle((left, 285, right - 1, 287), fill=GRID)                  # horizontal grid at 13 N
    for x in (4006, 4545):                                               # vertical grid at 2600 and 2800
        d.rectangle((x, top, x + 2, bottom - 1), fill=GRID)
    leg = legend_image(HANDLES)
    base = im.convert("RGBA")
    base.alpha_composite(leg, (4594 - leg.width, 111))
    return base.convert("RGB")


if __name__ == "__main__":
    finish(relabel(slide_picture(18), "Sample", "Force z (N)"), "pred_id.png")
    finish(relabel(fix_idsia_legend(slide_picture(19)), "Sample", "Force z (N)"), "ood_idsia.png")
