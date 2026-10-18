"""The DroughtLens logo as reusable SVG: a magnifying glass over a two-leaf seedling and a strip of dry soil.

Four versions: icon (square, app icon and favicon), horizontal (icon plus wordmark), compact (navigation bar)
and mono (one colour, any background). All have transparent backgrounds. `python scripts/make_logo_assets.py`
writes them to assets/logo/ together with PNG icons.
"""

FOREST, OLIVE, SOIL = "#243D2D", "#737B43", "#6C5542"
WORD_FONT = "Lora, Georgia, 'Times New Roman', serif"


def _mark(forest=FOREST, olive=OLIVE, soil=SOIL, leaf_b_opacity=1.0, leaf_a_opacity=1.0):
    """The 64 x 64 symbol, drawn from simple geometric shapes so it stays legible at favicon size."""
    return (
        f'<circle cx="27" cy="27" r="19" fill="none" stroke="{forest}" stroke-width="4"/>'
        f'<line x1="41" y1="41" x2="58" y2="58" stroke="{soil}" stroke-width="6" stroke-linecap="round"/>'
        f'<path d="M27 34.5 L27 22" stroke="{forest}" stroke-width="2.5" stroke-linecap="round" fill="none"/>'
        f'<path d="M27 27 C20 27 17 22 17 17 C23 17 27 20 27 27 Z" fill="{olive}" opacity="{leaf_a_opacity}"/>'
        f'<path d="M27 23 C33 23 37 19 37 14 C31 14 27 17 27 23 Z" fill="{forest}" opacity="{leaf_b_opacity}"/>'
        f'<path d="M15 37 Q27 33 39 37" stroke="{soil}" stroke-width="2.5" stroke-linecap="round" fill="none"/>'
        f'<path d="M21 40 L23 43 M30 40 L28 43 M34 40 L36 42" stroke="{soil}" stroke-width="1.6" stroke-linecap="round" fill="none"/>'
    )


def _wordmark(x, y, size, forest=FOREST, olive=OLIVE):
    return (f'<text x="{x}" y="{y}" font-family="{WORD_FONT}" font-size="{size}" font-weight="700" letter-spacing="-0.3">'
            f'<tspan fill="{forest}">Drought</tspan><tspan fill="{olive}">Lens</tspan></text>')


def _svg(viewbox, body, width=None, height=None, title="DroughtLens"):
    size = (f' width="{width}"' if width else "") + (f' height="{height}"' if height else "")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{viewbox}"{size} role="img" aria-label="{title}">'
            f'<title>{title}</title>{body}</svg>')


def icon(size=None):
    """Square icon for the app and favicon."""
    return _svg("0 0 64 64", _mark(), size, size)


def horizontal(height=None):
    """Primary logo: icon and wordmark."""
    return _svg("0 0 300 64", _mark() + _wordmark(74, 43, 36), None, height)


def compact(height=None):
    """Navigation-bar logo: smaller wordmark, tighter spacing."""
    return _svg("0 0 190 40", f'<g transform="scale(0.625)">{_mark()}</g>' + _wordmark(46, 28, 24), None, height)


def mono(height=None, colour="currentColor"):
    """One colour on any background: the leaves and soil are told apart by weight and opacity, not hue."""
    body = _mark(forest=colour, olive=colour, soil=colour, leaf_a_opacity=0.55) + (
        f'<text x="74" y="43" font-family="{WORD_FONT}" font-size="36" font-weight="700" letter-spacing="-0.3" fill="{colour}">DroughtLens</text>')
    return _svg("0 0 300 64", body, None, height)
