"""Write the DroughtLens logo files to assets/logo/ (SVG and PNG). Run from the repo root: python scripts/make_logo_assets.py"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from droughtlens import logo  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "assets" / "logo"
OUT.mkdir(parents=True, exist_ok=True)
FOREST, OLIVE, SOIL = (0x24, 0x3D, 0x2D), (0x73, 0x7B, 0x43), (0x6C, 0x55, 0x42)


def bezier(p0, p1, p2, p3, n=24):
    pts = []
    for i in range(n + 1):
        t = i / n
        a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t ** 2, t ** 3
        pts.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return pts


def quad(p0, p1, p2, n=20):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0], (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1])
            for t in (i / n for i in range(n + 1))]


def png(size, path, scale=8):
    """The same geometry as the SVG mark, drawn with Pillow at 8x and shrunk for smooth edges."""
    s = scale * size / 64
    img = Image.new("RGBA", (size * scale, size * scale), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    P = lambda pts: [(x * s, y * s) for x, y in pts]

    def line(pts, width, colour):
        d.line(P(pts), fill=colour, width=int(width * s), joint="curve")
        for x, y in (pts[0], pts[-1]):
            r = width * s / 2
            d.ellipse((x * s - r, y * s - r, x * s + r, y * s + r), fill=colour)

    d.ellipse(((27 - 19) * s, (27 - 19) * s, (27 + 19) * s, (27 + 19) * s), outline=FOREST, width=int(4 * s))
    line([(41, 41), (58, 58)], 6, SOIL)
    line([(27, 34.5), (27, 22)], 2.5, FOREST)
    d.polygon(P(bezier((27, 27), (20, 27), (17, 22), (17, 17)) + bezier((17, 17), (23, 17), (27, 20), (27, 27))), fill=OLIVE)
    d.polygon(P(bezier((27, 23), (33, 23), (37, 19), (37, 14)) + bezier((37, 14), (31, 14), (27, 17), (27, 23))), fill=FOREST)
    line(quad((15, 37), (27, 33), (39, 37)), 2.5, SOIL)
    for a, b in (((21, 40), (23, 43)), ((30, 40), (28, 43)), ((34, 40), (36, 42))):
        line([a, b], 1.6, SOIL)
    img.resize((size, size), Image.LANCZOS).save(path)


files = {
    "droughtlens-icon.svg": logo.icon(),
    "droughtlens-horizontal.svg": logo.horizontal(),
    "droughtlens-compact.svg": logo.compact(),
    "droughtlens-mono.svg": logo.mono(colour="#292D29"),
}
for name, svg in files.items():
    (OUT / name).write_text(svg, encoding="utf-8")
png(512, OUT / "droughtlens-icon-512.png")
png(64, OUT / "favicon-64.png")
print("wrote", ", ".join(sorted(p.name for p in OUT.iterdir())))
