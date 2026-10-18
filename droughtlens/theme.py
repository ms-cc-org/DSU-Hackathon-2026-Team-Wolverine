"""DroughtLens design system: colour tokens, global styles and the small HTML helpers every page uses."""
import base64
from html import escape
from pathlib import Path

import streamlit as st

ASSETS = Path(__file__).resolve().parents[1] / "assets"

# --- Colour tokens (brand palette) -----------------------------------------
FOREST = "#243D2D"
OLIVE = "#737B43"
IVORY = "#F7F5EF"
SILK = "#E7D8A8"       # corn silk
SOIL = "#6C5542"
CHARCOAL = "#292D29"
AMBER = "#C58B35"      # warnings only
RED = "#A94B3F"        # drought risk only
# derived neutrals
PAPER = "#FCFBF7"      # fields and panels, a step lighter than ivory
TINT = "#ECEEDF"       # quiet olive tint for hover and table headers
RULE = "#DDD8C8"
MUTED = "#5E6258"

# Drought Monitor levels on the dataset's 0..5 scale (the dataset's scale is offset by one from the D labels).
DROUGHT_LEVELS = [
    # level, name, short, colour, text colour on that colour, what it means on the farm
    (0, "No drought", "None", OLIVE, "#fff", "Normal moisture."),
    (1, "Abnormally dry (D0)", "D0", SILK, CHARCOAL, "Going into drought. Crops may begin to stress."),
    (2, "Moderate drought (D1)", "D1", "#D9B25F", CHARCOAL, "Some crop damage is likely. Fields and pastures are dry."),
    (3, "Severe drought (D2)", "D2", AMBER, CHARCOAL, "Crop losses are likely. Water shortages are common."),
    (4, "Extreme drought (D3)", "D3", RED, "#fff", "Major crop losses. Widespread water shortages."),
    (5, "Exceptional drought (D4)", "D4", "#6E2B24", "#fff", "Exceptional and widespread losses."),
]
LEVEL_NAME = {lv: name for lv, name, *_ in DROUGHT_LEVELS}
LEVEL_SHORT = {lv: short for lv, _, short, *_ in DROUGHT_LEVELS}
LEVEL_COLOR = {lv: color for lv, _, _, color, *_ in DROUGHT_LEVELS}
LEVEL_INK = {lv: ink for lv, _, _, _, ink, _ in DROUGHT_LEVELS}
LEVEL_MEANING = {lv: text for lv, *_, text in DROUGHT_LEVELS}

CORN_SVG = f"""<svg viewBox="0 0 64 64" width="{{s}}" height="{{s}}" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
<path d="M32 58 C12 50 8 34 14 22 C20 30 26 40 32 58Z" fill="{OLIVE}"/>
<path d="M32 58 C52 50 56 34 50 22 C44 30 38 40 32 58Z" fill="{OLIVE}"/>
<ellipse cx="32" cy="29" rx="12" ry="22" fill="{SILK}" stroke="{FOREST}" stroke-width="2"/>
<g fill="{AMBER}" opacity=".8"><circle cx="27" cy="14" r="1.6"/><circle cx="32" cy="12" r="1.6"/><circle cx="37" cy="14" r="1.6"/>
<circle cx="25" cy="21" r="1.6"/><circle cx="32" cy="20" r="1.6"/><circle cx="39" cy="21" r="1.6"/>
<circle cx="24" cy="28" r="1.6"/><circle cx="32" cy="27" r="1.6"/><circle cx="40" cy="28" r="1.6"/>
<circle cx="25" cy="35" r="1.6"/><circle cx="32" cy="34" r="1.6"/><circle cx="39" cy="35" r="1.6"/>
<circle cx="28" cy="42" r="1.6"/><circle cx="36" cy="42" r="1.6"/></g></svg>"""

SOY_SVG = f"""<svg viewBox="0 0 64 64" width="{{s}}" height="{{s}}" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
<path d="M10 44 C8 20 30 8 54 14 C56 38 36 56 10 44Z" fill="{OLIVE}" stroke="{FOREST}" stroke-width="2"/>
<circle cx="22" cy="38" r="7" fill="{IVORY}" stroke="{FOREST}" stroke-width="1.5"/>
<circle cx="33" cy="30" r="7" fill="{IVORY}" stroke="{FOREST}" stroke-width="1.5"/>
<circle cx="44" cy="22" r="6" fill="{IVORY}" stroke="{FOREST}" stroke-width="1.5"/>
<path d="M10 44 C6 50 4 54 4 58" stroke="{FOREST}" stroke-width="3" fill="none" stroke-linecap="round"/></svg>"""
CROP_ICONS = {"CORN": CORN_SVG, "SOYBEANS": SOY_SVG}


def crop_icon(crop, size=40):
    return CROP_ICONS[crop].replace("{s}", str(size))


@st.cache_data
def photo(name):
    """A photo from assets/ as a data URI, for use in CSS backgrounds. Empty if the file is missing."""
    path = ASSETS / name
    if not path.exists():
        return ""
    return "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode()


def html(s):
    """Render raw HTML. Collapsing newlines keeps markdown from treating indented lines as code."""
    st.markdown(" ".join(s.split("\n")), unsafe_allow_html=True)


def tip(text, label="How we worked this out"):
    """A small hover button. Hover, focus or tap it to read the explanation."""
    return (f"<span class='tip' tabindex='0' role='button' aria-label='{escape(label)}'>?"
            f"<span class='tipbody'>{escape(text)}</span></span>")


def chapter(eyebrow, title=None, lead=None, hint=None):
    """Section header: small label, title, optional one-line intro and optional hover explanation."""
    if title is None:
        eyebrow, title = "", eyebrow
    eyebrow_html = f"<div class='eyebrow'>{eyebrow}</div>" if eyebrow else ""
    lead_html = f"<p class='lead'>{lead}</p>" if lead else ""
    hint_html = tip(hint) if hint else ""
    html(f"<div class='sec'>{eyebrow_html}<div class='h2row'><h2>{title}</h2>{hint_html}</div>{lead_html}</div>")


def question(n, text, hint):
    """A numbered question with a hover button that explains how its answer was worked out."""
    html(f"<div class='q'>{tip(hint)}<div class='qtext'><span class='qn'>Question {n}</span>{escape(text)}</div></div>")


def callout(text, kind="finding"):
    """kind: finding (data-backed, olive rule), guidance (general advice, soil rule) or warning (amber rule)."""
    html(f"<div class='callout {kind}'>{text}</div>")


def apply_theme():
    html(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,700&family=Lora:wght@500;600;700&display=swap');
html, body, .stApp, [class*="css"] {{ font-family: 'DM Sans', system-ui, sans-serif; color: {CHARCOAL}; }}
.stApp {{ background: {IVORY}; }}
header[data-testid="stHeader"] {{ background: transparent; height: 0; }}
#MainMenu, footer {{ visibility: hidden; }}
.block-container {{ max-width: 1120px; padding: .6rem 1.2rem 4rem; }}
p, li, label, div[data-testid="stMarkdownContainer"] p {{ font-size: 1.06rem; line-height: 1.55; }}
h1, h2, h3, h4 {{ font-family: 'Lora', Georgia, serif; color: {FOREST}; letter-spacing: -0.01em; }}
h2 {{ font-size: 1.85rem; line-height: 1.2; margin: .15rem 0 .4rem; padding: 0; }}
h3 {{ font-size: 1.25rem; margin: 1.4rem 0 .3rem; }}
.eyebrow {{ font-size: .8rem; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: {OLIVE}; }}
.lead {{ color: {MUTED}; font-size: 1.12rem; max-width: 46rem; margin: 0 0 .6rem; }}
.sec {{ border-top: 1px solid {RULE}; padding-top: 1.4rem; margin-top: 2.4rem; }}
.h2row {{ display: flex; align-items: flex-start; gap: .7rem; }}
.small {{ font-size: .93rem; color: {MUTED}; }}

/* Controls: 48px touch targets, flat, 4px radius */
.stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {{ min-height: 48px; border-radius: 4px; border: 1px solid {FOREST};
  background: transparent; color: {FOREST}; font-weight: 700; font-size: 1.02rem; box-shadow: none; }}
.stButton > button:hover, .stFormSubmitButton > button:hover, .stDownloadButton > button:hover {{ background: {TINT}; border-color: {FOREST}; color: {FOREST}; }}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {{ background: {FOREST}; color: {IVORY}; }}
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover {{ background: {OLIVE}; border-color: {OLIVE}; color: #fff; }}
.stButton > button[kind="tertiary"] {{ border: none; border-bottom: 3px solid transparent; border-radius: 0; color: {FOREST}; font-weight: 500; }}
.stButton > button[kind="tertiary"]:hover {{ background: transparent; border-bottom-color: {SILK}; }}
.stButton > button:focus-visible {{ outline: 3px solid {CHARCOAL}; outline-offset: 2px; }}
div[data-baseweb="select"] > div, div[data-baseweb="input"] > div, div[data-baseweb="base-input"], textarea {{
  background: {PAPER}; border-radius: 4px; border-color: {MUTED}; }}
div[data-baseweb="select"] > div, div[data-baseweb="input"] > div {{ min-height: 48px; }}
div[data-testid="stForm"], div[data-testid="stExpander"] {{ border: 1px solid {RULE}; border-radius: 4px; background: {PAPER}; }}
div[data-testid="stForm"] {{ padding: 1.4rem; }}
div[data-testid="stAlert"] {{ border-radius: 4px; }}
div[data-testid="stMetric"] {{ border-left: 3px solid {OLIVE}; padding-left: .9rem; }}
div[data-testid="stMetricValue"] {{ font-family: 'Lora', Georgia, serif; color: {FOREST}; }}
div[data-testid="stChatMessage"] {{ background: {PAPER}; border: 1px solid {RULE}; border-radius: 4px; }}

/* Navigation */
.navbar {{ display: flex; align-items: center; min-height: 52px; }}
.navrule {{ border-bottom: 1px solid {RULE}; margin: .2rem 0 1rem; }}

/* Hero */
.hero {{ display: grid; grid-template-columns: 1.05fr 1fr; background: {FOREST}; border-radius: 4px; overflow: hidden; }}
.hero .copy {{ padding: 2.6rem 2.2rem; color: {IVORY}; display: flex; flex-direction: column; justify-content: center; }}
.hero .eyebrow {{ color: {SILK}; }}
.hero h1 {{ color: {IVORY}; font-size: 2.7rem; line-height: 1.1; margin: .5rem 0 1rem; padding: 0; }}
.hero p {{ color: {TINT}; font-size: 1.12rem; margin: 0 0 .8rem; }}
.hero .pic {{ min-height: 380px; background-size: cover; background-position: center; position: relative; }}
.hero .caption {{ position: absolute; left: 0; right: 0; bottom: 0; background: rgba(36,61,45,.92); color: {IVORY}; padding: .7rem 1rem; font-size: .92rem; line-height: 1.4; }}
.hero .caption b {{ color: {SILK}; }}
@media (max-width: 760px) {{ .hero {{ grid-template-columns: 1fr; }} .hero .pic {{ min-height: 220px; order: -1; }}
  .hero .copy {{ padding: 1.6rem 1.2rem; }} .hero h1 {{ font-size: 2.05rem; }} }}

/* Plain stat rows, steps */
.stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 1.4rem; margin: 1rem 0; }}
.stat {{ border-left: 3px solid {OLIVE}; padding-left: .9rem; }}
.stat .n {{ font-family: 'Lora', Georgia, serif; font-size: 2.2rem; font-weight: 700; line-height: 1.1; color: {FOREST}; }}
.stat .t {{ color: {MUTED}; font-size: .98rem; line-height: 1.35; }}
.steps {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1.4rem; }}
.step b {{ display: block; font-size: 1.12rem; color: {FOREST}; margin-bottom: .15rem; }}
.step .k {{ font-family: 'Lora', Georgia, serif; font-size: 1.6rem; color: {OLIVE}; }}

/* Drought level strip */
.legend {{ display: grid; grid-template-columns: repeat(6, 1fr); gap: 3px; margin: .6rem 0 .5rem; }}
.legend div {{ text-align: center; padding: .55rem .1rem; font-weight: 700; font-size: .93rem; border-radius: 2px; border: 3px solid transparent; opacity: .5; }}
.legend div.on {{ opacity: 1; border-color: {CHARCOAL}; }}

/* Crop photo cards */
.crop {{ border: 1px solid {RULE}; border-radius: 4px; background: {PAPER}; overflow: hidden; margin-bottom: .5rem; }}
.crop.on {{ border: 2px solid {FOREST}; }}
.crop .img {{ height: 130px; background-size: cover; background-position: center; }}
.crop .row {{ display: flex; align-items: center; gap: .8rem; padding: .7rem .9rem; }}
.crop .row b {{ font-size: 1.12rem; display: block; line-height: 1.2; }}
.crop .row span {{ font-size: .93rem; color: {MUTED}; }}

/* Result, callouts, quote */
.result {{ border: 1px solid {RULE}; border-left: 8px solid var(--c); border-radius: 4px; background: {PAPER}; padding: 1.2rem 1.4rem; margin: .6rem 0 1rem; }}
.result .head {{ display: flex; gap: 1rem; align-items: center; }}
.result .big {{ font-family: 'Lora', Georgia, serif; font-size: 2.7rem; font-weight: 700; line-height: 1.1; color: var(--c); }}
.result .sub {{ font-size: 1.06rem; }}
.callout {{ border-left: 4px solid {SILK}; padding: .25rem 0 .25rem 1rem; margin: .8rem 0; }}
.callout.finding {{ border-left-color: {OLIVE}; }}
.callout.guidance {{ border-left-color: {SOIL}; }}
.callout.warning {{ border-left-color: {AMBER}; }}
.tagline {{ display: block; font-size: .78rem; font-weight: 700; letter-spacing: .09em; text-transform: uppercase; margin-bottom: .1rem; }}
.finding .tagline {{ color: {OLIVE}; }} .guidance .tagline {{ color: {SOIL}; }} .warning .tagline {{ color: {AMBER}; }}
.quote {{ border: 1px solid {RULE}; border-left: 6px solid {FOREST}; border-radius: 4px; background: {PAPER}; padding: 1rem 1.2rem;
  font-family: 'Lora', Georgia, serif; font-size: 1.3rem; line-height: 1.4; color: {FOREST}; margin: .8rem 0 1rem; }}
.photo-band {{ height: 240px; border-radius: 4px; background-size: cover; background-position: center; margin: 1rem 0 .3rem; }}
.ok {{ color: {FOREST}; font-weight: 700; }} .miss {{ color: {RED}; font-weight: 700; }} .na {{ color: {MUTED}; font-weight: 700; }}

/* Tables */
.vt {{ width: 100%; border-collapse: collapse; margin: .4rem 0 1rem; font-size: 1.02rem; }}
.vt th {{ text-align: left; font-size: .8rem; letter-spacing: .06em; text-transform: uppercase; color: {MUTED}; border-bottom: 2px solid {RULE}; padding: .4rem .5rem; }}
.vt td {{ border-bottom: 1px solid {RULE}; padding: .6rem .5rem; vertical-align: top; }}
.status td:first-child {{ font-weight: 700; white-space: nowrap; }}

/* Questions and hover tips */
.q {{ display: flex; gap: .8rem; align-items: flex-start; margin: 2rem 0 .4rem; padding-top: 1.2rem; border-top: 1px solid {RULE}; }}
.q .qtext {{ font-family: 'Lora', Georgia, serif; font-size: 1.3rem; font-weight: 600; line-height: 1.3; color: {FOREST}; }}
.q .qn {{ display: block; font-family: 'DM Sans', sans-serif; font-size: .8rem; letter-spacing: .1em; text-transform: uppercase; color: {OLIVE}; font-weight: 700; }}
.tip {{ position: relative; flex: none; display: inline-flex; align-items: center; justify-content: center; width: 1.7rem; height: 1.7rem; margin-top: .15rem;
  border: 2px solid {FOREST}; border-radius: 50%; background: {PAPER}; color: {FOREST}; font: 700 1rem 'DM Sans', sans-serif; cursor: help; }}
.tip:hover, .tip:focus {{ background: {FOREST}; color: #fff; outline: none; }}
.tip .tipbody {{ visibility: hidden; opacity: 0; position: absolute; left: 0; top: 2.2rem; z-index: 100; width: min(24rem, 78vw); padding: .8rem 1rem;
  background: {CHARCOAL}; color: {IVORY}; border-radius: 4px; font: 400 .96rem/1.5 'DM Sans', sans-serif; text-align: left; transition: opacity .12s; }}
.tip:hover .tipbody, .tip:focus .tipbody {{ visibility: visible; opacity: 1; }}

.action {{ display: grid; grid-template-columns: 2.2rem 1fr; gap: .6rem; padding: .8rem 0; border-top: 1px solid {RULE}; }}
.action .num {{ font-family: 'Lora', Georgia, serif; font-weight: 700; font-size: 1.4rem; color: {OLIVE}; }}
.action b {{ display: block; }}
.footer {{ border-top: 1px solid {RULE}; margin-top: 3rem; padding-top: 1rem; }}
@media (max-width: 760px) {{ .vt {{ font-size: .93rem; overflow-x: auto; display: block; }} .quote {{ font-size: 1.12rem; }} .result .big {{ font-size: 2.1rem; }} }}
</style>
""")
