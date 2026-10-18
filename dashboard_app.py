import base64
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from wolverine import data_prep, drought_timing as dt, reality_table as rt
from wolverine.contracts import CROPS, STATES, TRAIN_YEARS, TEST_YEARS, TOLERANCE_PTS, MIN_CELL_N, STRICT_ANOM

st.set_page_config(page_title="Drought Category Reality Check", page_icon=":ear_of_corn:", layout="wide")

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------
FOREST = "#2F5233"
FOREST_DK = "#1F3A24"
CREAM = "#F7F2E7"
PAPER = "#FCFAF4"
SAGE = "#C5D0B5"
SAGE_LT = "#E6EBDB"
CHARCOAL = "#2B2E2B"
MUTED = "#5B6157"
RULE = "#D5D9C8"

# Drought severity scale: green (fine) to deep red (exceptional).
DROUGHT_LEVELS = [
    # level, label, short, colour, what it means on the farm
    (0, "No drought", "None", "#4F7D4F", "Normal moisture."),
    (1, "Abnormally dry (D0)", "D0", "#C2BE5A", "Going into drought. Crops may begin to stress."),
    (2, "Moderate drought (D1)", "D1", "#DDAE3A", "Some crop damage is likely. Fields and pastures are dry."),
    (3, "Severe drought (D2)", "D2", "#D9772B", "Crop losses are likely. Water shortages are common."),
    (4, "Extreme drought (D3)", "D3", "#B5402E", "Major crop losses. Widespread water shortages."),
    (5, "Exceptional drought (D4)", "D4", "#7A2417", "Exceptional and widespread losses."),
]
LEVEL_NAME = {lv: name for lv, name, *_ in DROUGHT_LEVELS}
LEVEL_COLOR = {lv: c for lv, _, _, c, _ in DROUGHT_LEVELS}
LEVEL_SHORT = {lv: s for lv, _, s, *_ in DROUGHT_LEVELS}

STATE_NAMES = {"IA": "Iowa", "NE": "Nebraska"}
IRRIG_LABEL = {"mostly irrigated": "irrigated counties", "mostly dryland": "dryland counties"}
CROP_NAMES = {"CORN": "Corn", "SOYBEANS": "Soybeans"}
CROP_BLURB = {"CORN": "Grain corn, bushels per acre", "SOYBEANS": "Soybeans, bushels per acre"}
TIMING_CHOICES = {
    "Not sure": None,
    "Early (May to June)": "early",
    "Peak season (July to August)": "peak",
    "Late (September on)": "late",
}
TIMING_LABEL = {"none": "No severe drought (below D2)", "early": "Early (May to June)",
                "peak": "Peak (July to August)", "late": "Late (September on)"}
IRRIG_CHOICES = {"Irrigated": "mostly irrigated", "Rain only (dryland)": "mostly dryland"}


# Demo accounts only: replace with a real user store before sharing outside the team.
DEMO_USERS = {"farmer": "wolverine", "demo": "demo"}

ASSETS = Path(__file__).parent / "assets"

CORN_SVG = f"""<svg viewBox="0 0 64 64" width="{{s}}" height="{{s}}" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
<path d="M32 58 C12 50 8 34 14 22 C20 30 26 40 32 58Z" fill="{FOREST}"/>
<path d="M32 58 C52 50 56 34 50 22 C44 30 38 40 32 58Z" fill="{FOREST}"/>
<ellipse cx="32" cy="29" rx="12" ry="22" fill="#E3B23C" stroke="{FOREST_DK}" stroke-width="2"/>
<g fill="{FOREST_DK}" opacity=".45"><circle cx="27" cy="14" r="1.6"/><circle cx="32" cy="12" r="1.6"/><circle cx="37" cy="14" r="1.6"/>
<circle cx="25" cy="21" r="1.6"/><circle cx="32" cy="20" r="1.6"/><circle cx="39" cy="21" r="1.6"/>
<circle cx="24" cy="28" r="1.6"/><circle cx="32" cy="27" r="1.6"/><circle cx="40" cy="28" r="1.6"/>
<circle cx="25" cy="35" r="1.6"/><circle cx="32" cy="34" r="1.6"/><circle cx="39" cy="35" r="1.6"/>
<circle cx="28" cy="42" r="1.6"/><circle cx="36" cy="42" r="1.6"/></g></svg>"""

SOY_SVG = f"""<svg viewBox="0 0 64 64" width="{{s}}" height="{{s}}" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
<path d="M10 44 C8 20 30 8 54 14 C56 38 36 56 10 44Z" fill="#7C9A5B" stroke="{FOREST_DK}" stroke-width="2"/>
<circle cx="22" cy="38" r="7" fill="{CREAM}" stroke="{FOREST_DK}" stroke-width="1.5"/>
<circle cx="33" cy="30" r="7" fill="{CREAM}" stroke="{FOREST_DK}" stroke-width="1.5"/>
<circle cx="44" cy="22" r="6" fill="{CREAM}" stroke="{FOREST_DK}" stroke-width="1.5"/>
<path d="M10 44 C6 50 4 54 4 58" stroke="{FOREST_DK}" stroke-width="3" fill="none" stroke-linecap="round"/></svg>"""
ICONS = {"CORN": CORN_SVG, "SOYBEANS": SOY_SVG}


def icon(crop, size=40):
    return ICONS[crop].replace("{s}", str(size))


@st.cache_data
def photo(name):
    path = ASSETS / name
    if not path.exists():
        return ""
    return "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode()


def html(s):
    """Render raw HTML. Collapsing newlines keeps markdown from treating indented lines as code."""
    st.markdown(" ".join(s.split("\n")), unsafe_allow_html=True)


def chapter(eyebrow, title=None, lead=None):
    """Section header. With one argument it is the title alone, with no eyebrow label."""
    if title is None:
        eyebrow, title = "", eyebrow
    lead_html = f"<p class='lead'>{lead}</p>" if lead else ""
    eyebrow_html = f"<div class='eyebrow'>{eyebrow}</div>" if eyebrow else ""
    html(f"<div class='sec'>{eyebrow_html}<h2>{title}</h2>{lead_html}</div>")


def pct(v, signed=False):
    return f"{v:+.0f}%" if signed else f"{v:.0f}%"


# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------
html(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Source+Sans+3:wght@400;600;700&display=swap');
html, body, .stApp, [class*="css"] {{ font-family: 'Source Sans 3', system-ui, sans-serif; color: {CHARCOAL}; }}
.stApp {{ background: {CREAM}; }}
header[data-testid="stHeader"] {{ background: transparent; }}
#MainMenu, footer {{ visibility: hidden; }}
.block-container {{ max-width: 1040px; padding: 1.2rem 1.2rem 4rem; }}
p, li, label, .stMarkdown, div[data-testid="stMarkdownContainer"] p {{ font-size: 1.1rem; line-height: 1.55; }}
h1, h2, h3 {{ font-family: 'Fraunces', Georgia, serif; color: {FOREST_DK}; letter-spacing: -0.01em; }}
h2 {{ font-size: 1.9rem; line-height: 1.2; margin: .15rem 0 .4rem; padding: 0; }}
h3 {{ font-size: 1.3rem; margin: 1.4rem 0 .3rem; }}
.eyebrow {{ font-size: .85rem; font-weight: 700; letter-spacing: .09em; text-transform: uppercase; color: {MUTED}; }}
.lead {{ color: {MUTED}; font-size: 1.15rem; max-width: 46rem; margin: 0 0 .6rem; }}
.sec {{ border-top: 1px solid {RULE}; padding-top: 1.4rem; margin-top: 2.4rem; }}
.small {{ font-size: .95rem; color: {MUTED}; }}

/* Controls: 48px touch targets, flat, 4px radius */
.stButton > button, .stFormSubmitButton > button {{ min-height: 48px; border-radius: 4px; border: 1px solid {FOREST};
  background: transparent; color: {FOREST}; font-weight: 700; font-size: 1.05rem; box-shadow: none; }}
.stButton > button:hover, .stFormSubmitButton > button:hover {{ background: {SAGE_LT}; border-color: {FOREST_DK}; color: {FOREST_DK}; }}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {{ background: {FOREST}; color: #fff; }}
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover {{ background: {FOREST_DK}; color: #fff; }}
.stButton > button:focus-visible {{ outline: 3px solid {CHARCOAL}; outline-offset: 2px; }}
div[data-baseweb="select"] > div, div[data-baseweb="input"] > div, div[data-baseweb="base-input"] {{
  background: {PAPER}; border-radius: 4px; min-height: 48px; border-color: {MUTED}; }}
div[data-testid="stNumberInput"] input, div[data-testid="stTextInput"] input {{ font-size: 1.1rem; }}
div[data-testid="stForm"] {{ border: 1px solid {RULE}; border-radius: 4px; background: {PAPER}; padding: 1.4rem; }}
div[data-testid="stAlert"] {{ border-radius: 4px; }}

/* Topbar */
.brand {{ display: flex; align-items: center; gap: .7rem; font-family: 'Fraunces', Georgia, serif; font-weight: 700;
  font-size: 1.35rem; color: {FOREST_DK}; padding: .35rem 0; }}

/* Hero */
.hero {{ display: grid; grid-template-columns: 1.1fr 1fr; background: {FOREST_DK}; border-radius: 4px; overflow: hidden; }}
.hero .copy {{ padding: 2.6rem 2.2rem; color: {CREAM}; display: flex; flex-direction: column; justify-content: center; }}
.hero .copy .eyebrow {{ color: {SAGE}; }}
.hero h1 {{ color: {CREAM}; font-size: 2.6rem; line-height: 1.1; margin: .5rem 0 1rem; padding: 0; }}
.hero p {{ color: {SAGE_LT}; font-size: 1.15rem; margin: 0; }}
.hero .pic {{ min-height: 340px; background-size: cover; background-position: center; }}
@media (max-width: 760px) {{ .hero {{ grid-template-columns: 1fr; }} .hero .pic {{ min-height: 200px; order: -1; }}
  .hero .copy {{ padding: 1.6rem 1.2rem; }} .hero h1 {{ font-size: 2rem; }} }}

/* Plain stat rows (no boxes) */
.stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 1.4rem; margin: 1rem 0; }}
.stat {{ border-left: 3px solid {FOREST}; padding-left: .9rem; }}
.stat .n {{ font-family: 'Fraunces', Georgia, serif; font-size: 2.3rem; font-weight: 700; line-height: 1.1; color: {FOREST_DK}; }}
.stat .t {{ color: {MUTED}; font-size: 1rem; line-height: 1.35; }}

/* Steps */
.steps {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1.4rem; }}
.step b {{ display: block; font-size: 1.15rem; color: {FOREST_DK}; margin-bottom: .15rem; }}
.step .k {{ font-family: 'Fraunces', Georgia, serif; font-size: 1.6rem; color: {FOREST}; }}

/* Drought level strip */
.legend {{ display: grid; grid-template-columns: repeat(6, 1fr); gap: 3px; margin: .6rem 0 .5rem; }}
.legend div {{ text-align: center; padding: .55rem .1rem; font-weight: 700; font-size: .95rem; color: #fff; border-radius: 2px;
  border: 3px solid transparent; opacity: .45; }}
.legend div.dark {{ color: {CHARCOAL}; }}
.legend div.on {{ opacity: 1; border-color: {CHARCOAL}; }}

/* Crop choice */
.crop {{ border: 1px solid {RULE}; border-radius: 4px; background: {PAPER}; overflow: hidden; margin-bottom: .5rem; }}
.crop.on {{ border: 2px solid {FOREST}; }}
.crop .img {{ height: 130px; background-size: cover; background-position: center; }}
.crop .row {{ display: flex; align-items: center; gap: .8rem; padding: .7rem .9rem; }}
.crop .row b {{ font-size: 1.15rem; display: block; line-height: 1.2; }}
.crop .row span {{ font-size: .95rem; color: {MUTED}; }}

/* Result */
.result {{ border: 1px solid {RULE}; border-left: 8px solid var(--c); border-radius: 4px; background: {PAPER}; padding: 1.2rem 1.4rem; margin: .6rem 0 1rem; }}
.result .head {{ display: flex; gap: 1rem; align-items: center; }}
.result .big {{ font-family: 'Fraunces', Georgia, serif; font-size: 2.8rem; font-weight: 700; line-height: 1.1; color: var(--c); }}
.result .sub {{ color: {CHARCOAL}; font-size: 1.1rem; }}
@media (max-width: 760px) {{ .result .big {{ font-size: 2.2rem; }} }}

.callout {{ border-left: 3px solid {SAGE}; padding: .2rem 0 .2rem 1rem; color: {CHARCOAL}; margin: .8rem 0; }}
.photo-band {{ height: 240px; border-radius: 4px; background-size: cover; background-position: center; margin: 1rem 0 .3rem; }}
.action {{ display: grid; grid-template-columns: 2.2rem 1fr; gap: .6rem; padding: .8rem 0; border-top: 1px solid {RULE}; }}
.action .num {{ font-family: 'Fraunces', Georgia, serif; font-weight: 700; font-size: 1.4rem; color: {FOREST}; }}
.action b {{ display: block; }}
div[data-testid="stMetric"] {{ border-left: 3px solid {FOREST}; padding-left: .9rem; }}
div[data-testid="stMetricValue"] {{ font-family: 'Fraunces', Georgia, serif; color: {FOREST_DK}; }}
.vt {{ width: 100%; border-collapse: collapse; margin: .4rem 0 1rem; font-size: 1.05rem; }}
.vt th {{ text-align: left; font-size: .85rem; letter-spacing: .06em; text-transform: uppercase; color: {MUTED}; border-bottom: 2px solid {RULE}; padding: .4rem .5rem; }}
.vt td {{ border-bottom: 1px solid {RULE}; padding: .6rem .5rem; vertical-align: top; }}
.ok {{ color: {FOREST}; font-weight: 700; }}
.miss {{ color: #B5402E; font-weight: 700; }}
.na {{ color: {MUTED}; font-weight: 700; }}
.quote {{ border: 1px solid {RULE}; border-left: 6px solid {FOREST}; border-radius: 4px; background: {PAPER}; padding: 1rem 1.2rem;
  font-family: 'Fraunces', Georgia, serif; font-size: 1.35rem; line-height: 1.4; color: {FOREST_DK}; margin: .8rem 0 1rem; }}
@media (max-width: 760px) {{ .vt {{ font-size: .95rem; overflow-x: auto; display: block; }} .quote {{ font-size: 1.15rem; }} }}
</style>
""")


def go_to(page):
    st.session_state.page = page
    st.rerun()


# ---------------------------------------------------------------------------
# Data: the team's analysis (wolverine/), the same tables the evidence app shows
# ---------------------------------------------------------------------------
OCHRE = "#C98B2B"
ORANGE = LEVEL_COLOR[3]
MASTER_TREND = "Master trend (all years)"
STRICT_TREND = "Strict trend (2000–2012 only)"
BAR_TEXT = dict(textposition="outside", cliponaxis=False)


@st.cache_data(show_spinner=False)
def get_panel():
    """Reported county yields with a drought reading, plus drought timing and Nebraska irrigation group."""
    panel = data_prep.add_strict_anomaly(data_prep.build_panel())
    panel = panel.merge(dt.drought_timing(), on=["fips", "crop", "year"], how="left")
    return panel.merge(dt.irrigation_groups(), on=["fips", "crop"], how="left")


@st.cache_data(show_spinner=False)
def analysis(crop, anom):
    """Every table the evidence app builds for one crop and one trend version."""
    view = get_panel()
    view = view[view.crop == crop]
    ne = view[view.state_alpha == "NE"]
    groups = ["mostly irrigated", "mostly dryland"]
    irr_table = rt.build_table(ne, TRAIN_YEARS, anom, extra_by=["irrig_group"])
    irr_check = rt.backtest(ne, anom, extra_by=["irrig_group"])
    timing = rt.build_table(view, (TRAIN_YEARS[0], TEST_YEARS[1]), anom, extra_by=["timing"])
    labelled = view.dropna(subset=["timing"])
    return {
        "table": rt.build_table(view, TRAIN_YEARS, anom),
        "check": rt.backtest(view, anom),
        "irr_table": irr_table[irr_table.irrig_group.isin(groups)],
        "irr_check": irr_check[irr_check.irrig_group.isin(groups)],
        "timing": timing[(timing.level == 4) & timing.timing.isin(["early", "peak"])],
        "d3_timing": view[view.max_drought_severity == 4]["timing"].value_counts(),
        "timing_years": (int(labelled.year.min()), int(labelled.year.max())),
        "timing_counties": labelled.fips.nunique(),
        "coverage": data_prep.coverage_report(view).reset_index(),
    }


def cell(frame, state, level, group=None):
    """One row of a backtest table (the 2000-2012 estimate and its 2013-2025 check), or None."""
    hit = frame[(frame.state_alpha == state) & (frame.level == level)]
    if group:
        hit = hit[hit.irrig_group == group]
    return hit.iloc[0] if len(hit) and hit.iloc[0].train_n > 0 else None


def lc_first(text):
    """Lower-case the first letter only, so 'Extreme drought (D3)' keeps its D-code."""
    return text[0].lower() + text[1:]


def below(v, digits=0):
    """'17% below normal' for a mean yield change in percent (negative = below)."""
    return f"{abs(v):.{digits}f}% {'below' if v < 0 else 'above'} normal"


def loss_text(v):
    """'17% loss' or '3% gain' for a mean yield change in percent."""
    return f"{abs(v):.0f}% {'loss' if v < 0 else 'gain'}"


def verdict(row):
    """(css class, sentence): did the 2000-2012 estimate hold up on 2013-2025?"""
    if row is None or not row.enough_rows:
        return "na", f"Too few past years to check (fewer than {MIN_CELL_N} in one period). Don't rely on this number."
    if row.within_tol:
        return "ok", f"Held up. 2013–2025 came in at {below(row.test_mean)}, within {TOLERANCE_PTS:g} points."
    return "miss", f"Missed. 2013–2025 came in at {below(row.test_mean)}, {row.abs_error:.0f} points away. Treat this estimate with care."


def typical_yield(panel, state, county, crop):
    """The county's recent trend yield in a normal year; recent reported yields if its trend is not available."""
    rows = panel[(panel.state_alpha == state) & (panel.county_name == county) & (panel.crop == crop)].sort_values("year")
    trend = (rows.yield_per_acre / (1 + rows.yield_anomaly_pct / 100)).dropna()
    return trend.tail(3).mean() if len(trend) else rows.yield_per_acre.tail(3).mean()


def peak_share(a):
    """Share of D3 seasons in which severe drought reached the county in July or August."""
    counts = a["d3_timing"]
    return counts.get("peak", 0) / counts.sum() if counts.sum() else None


def layout(fig, height=340):
    fig.update_layout(
        height=height, margin=dict(t=10, b=10, l=10, r=10), paper_bgcolor=CREAM, plot_bgcolor=CREAM,
        font=dict(family="Source Sans 3, sans-serif", size=15, color=CHARCOAL),
        legend=dict(orientation="h", y=-0.2, title_text=""),
    )
    fig.update_xaxes(showgrid=False, linecolor=MUTED)
    fig.update_yaxes(gridcolor=RULE, zeroline=True, zerolinecolor=MUTED)
    return fig


# ---------------------------------------------------------------------------
# Page 1: welcome
# ---------------------------------------------------------------------------
def show_welcome():
    html(f"""
    <div class="hero">
      <div class="copy">
        <div class="eyebrow">Iowa and Nebraska · Corn and soybeans</div>
        <h1>Same drought label. Same yield loss?</h1>
        <p>The Drought Monitor gives a county the same label in Iowa and in Nebraska. We checked 26 years of records to see what each level really cost farmers, and whether those numbers held up in later years.</p>
      </div>
      <div class="pic" style="background-image:url('{photo('hero.jpg')}')"></div>
    </div>
    """)
    st.write("")
    c1, c2 = st.columns([1, 2])
    if c1.button("Get started", type="primary", width="stretch"):
        go_to("login")
    c2.markdown("<span class='small'>Free to use. Based on public drought and crop records.</span>", unsafe_allow_html=True)

    try:
        with st.spinner("Loading drought and yield records..."):
            panel, corn = get_panel(), analysis("CORN", "yield_anomaly_pct")
    except Exception as exc:
        st.error("We could not load the data files. Ask the team to check the data folder, then refresh this page.")
        st.caption(f"Technical detail: {exc}")
        return
    ia, ne = cell(corn["check"], "IA", 4), cell(corn["check"], "NE", 4)
    dry, irr = cell(corn["irr_check"], "NE", 4, "mostly dryland"), cell(corn["irr_check"], "NE", 4, "mostly irrigated")
    share = peak_share(corn)

    chapter("The story in three parts")
    html(f"""
    <div class="steps">
      <div class="step"><div class="k">1</div><b>Drought comes in levels</b>The U.S. Drought Monitor rates every county each week, from no drought, through abnormally dry (D0), up to exceptional (D4).</div>
      <div class="step"><div class="k">2</div><b>Each level costs yield, and not the same in each state</b>In 2000 to 2012, extreme drought (D3) cut Iowa corn yields {abs(ia.train_mean):.1f}% below trend. Nebraska corn lost {abs(ne.train_mean):.1f}%.</div>
      <div class="step"><div class="k">3</div><b>Water and timing explain the gap</b>At D3, Nebraska dryland corn lost {abs(dry.train_mean):.0f}% and irrigated corn {abs(irr.train_mean):.0f}%. {share:.0%} of D3 seasons had severe drought in July or August.</div>
    </div>
    """)
    html(f"""
    <div class="stats">
      <div class="stat"><div class="n">{len(panel):,}</div><div class="t">county-crop-years of yield records</div></div>
      <div class="stat"><div class="n">{panel['fips'].nunique()}</div><div class="t">Iowa and Nebraska counties with yield records</div></div>
      <div class="stat"><div class="n">{int(panel['year'].min())} to {int(panel['year'].max())}</div><div class="t">years of drought and yield history</div></div>
    </div>
    <p class="small">Yield records: USDA NASS. Drought levels: U.S. Drought Monitor. Photos: USDA and NRCS, public domain.</p>
    """)


# ---------------------------------------------------------------------------
# Page 2: login
# ---------------------------------------------------------------------------
def show_login():
    left, right = st.columns([1, 1], gap="large")
    with left:
        html(f"<div class='brand'>{icon('CORN', 34)}{icon('SOYBEANS', 34)} Drought Category Reality Check</div>")
        html("<div class='sec' style='margin-top:1rem'><div class='eyebrow'>Sign in</div><h2>Welcome back</h2>"
             "<p class='lead'>Log in to see what each drought level costs your crop.</p></div>")
        with st.form("login"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log in", type="primary", width="stretch")
        if submitted:
            if DEMO_USERS.get(username.strip().lower()) == password and password:
                st.session_state.user = username.strip().lower()
                go_to("dashboard")
            else:
                st.error("That username or password does not match. Check them and try again.")
        st.markdown("<span class='small'>Team demo: username <b>demo</b>, password <b>demo</b>.</span>", unsafe_allow_html=True)
        if st.button("Back"):
            go_to("welcome")
    with right:
        html(f"<div class='photo-band' style='height:460px;margin-top:0;background-image:url(\"{photo('corn.jpg')}\")'></div>")


# ---------------------------------------------------------------------------
# Page 3: dashboard
# ---------------------------------------------------------------------------
def check_table(chk, state):
    """Plain-language table: the 2000-2012 estimate, what 2013-2025 did, and the verdict, per drought level."""
    rows = ""
    for lv, name, _, color, _ in DROUGHT_LEVELS:
        r = cell(chk, state, lv)
        if r is None:
            continue
        css, text = verdict(r)
        mark = {"ok": "✓", "miss": "✗", "na": "–"}[css]
        test = f"{below(r.test_mean)}<br><span class='small'>{r.test_n} county-years</span>" if r.test_n > 0 else "<span class='small'>No records</span>"
        rows += (f"<tr><td><b>{name}</b></td><td>{below(r.train_mean)}<br><span class='small'>{r.train_n} county-years</span></td>"
                 f"<td>{test}</td><td class='{css}'>{mark} {text}</td></tr>")
    return ("<table class='vt'><tr><th>Drought level</th><th>2000–2012 (our estimate)</th><th>2013–2025 (what happened)</th>"
            f"<th>Did it hold up?</th></tr>{rows}</table>")


def show_dashboard():
    try:
        with st.spinner("Loading drought and yield records..."):
            panel = get_panel()
    except Exception as exc:  # data files missing or an analysis module not merged yet
        st.error("We could not load the data files. Ask the team to check the data folder, then refresh this page.")
        st.caption(f"Technical detail: {exc}")
        return

    top = st.columns([5, 1])
    top[0].markdown(f"<div class='brand'>{icon('CORN', 34)}{icon('SOYBEANS', 34)} Drought Category Reality Check</div>", unsafe_allow_html=True)
    if top[1].button("Log out", width="stretch"):
        for k in ("user", "crop"):
            st.session_state.pop(k, None)
        go_to("welcome")

    # --- 1. Your farm ------------------------------------------------------
    chapter("Step 1", "Tell us about your farm", "Your answers stay on this screen. We use them to pick the numbers that match your state, crop and water.")
    c1, c2, c3 = st.columns([1, 1.3, 1])
    state = c1.selectbox("State", STATES, format_func=STATE_NAMES.get)

    crop = st.session_state.setdefault("crop", "CORN")
    counties = sorted(panel[(panel.state_alpha == state) & (panel.crop == crop)]["county_name"].unique())
    county = c2.selectbox("County", counties, format_func=lambda c: c.replace(" County", ""))
    acres = c3.number_input("Acres planted", min_value=1, max_value=100000, value=160, step=10)

    st.markdown("**Crop**")
    for col, key in zip(st.columns(2), CROPS):
        with col:
            html(f"""
            <div class="crop {'on' if crop == key else ''}">
              <div class="img" style="background-image:url('{photo('corn.jpg' if key == 'CORN' else 'soybeans.jpg')}')"></div>
              <div class="row">{icon(key, 40)}<div><b>{CROP_NAMES[key]}</b><span>{CROP_BLURB[key]}</span></div></div>
            </div>""")
            if st.button("Selected" if crop == key else f"Choose {CROP_NAMES[key].lower()}", key=f"pick_{key}",
                         type="primary" if crop == key else "secondary", width="stretch"):
                st.session_state.crop = key
                st.rerun()

    crop_name = CROP_NAMES[crop].lower()
    county_short = county.replace(" County", "")
    a = analysis(crop, "yield_anomaly_pct")     # the master trend: what the estimates below use
    dry, irr = cell(a["irr_check"], "NE", 4, "mostly dryland"), cell(a["irr_check"], "NE", 4, "mostly irrigated")

    irrig = None
    if state == "NE":
        irrig_help = (f"At extreme drought (D3) in 2000–2012, Nebraska {crop_name} lost {abs(dry.train_mean):.0f}% on dryland counties "
                      f"and {abs(irr.train_mean):.0f}% on irrigated counties.") if dry is not None and irr is not None else None
        irrig = IRRIG_CHOICES[st.radio("How is this field watered?", list(IRRIG_CHOICES), horizontal=True, help=irrig_help, key="irrig_choice")]

    # --- 2. The answer -----------------------------------------------------
    chapter("Step 2", "Does the same drought level cost the same in Iowa and Nebraska?",
            f"Each bar is the average {crop_name} yield change, compared with normal for that county, in 2000 to 2012. Below zero means yield lost.")
    table, check = a["table"], a["check"]
    d3 = rt.same_meaning(table, level=4, crop=crop)
    sc = rt.score(check)
    if d3["same"]:
        reco = (f"At extreme drought (D3), {crop_name} lost about the same in Iowa ({abs(d3['ia']):.0f}%) and Nebraska ({abs(d3['ne']):.0f}%), "
                "so one drought trigger can serve both states.")
    else:
        irr_note = " (much less on irrigated land)" if dry is not None and irr is not None and dry.train_mean - irr.train_mean <= -TOLERANCE_PTS else ""
        reco = (f"Don't read the drought map the same way in every state: at D3, plan for about a {abs(d3['ia']):.0f}% yield loss on Iowa {crop_name} "
                f"but about {abs(d3['ne']):.0f}% in Nebraska{irr_note}. These estimates held up on 2013–2025: {sc['share_within_tol']:.0%} of the "
                f"table's cells landed within {TOLERANCE_PTS:g} points.")
    html(f"<div class='quote'>{reco}</div>")
    m1, m2, m3 = st.columns(3)
    m1.metric("Iowa at D3", below(d3["ia"], 1))
    m2.metric("Nebraska at D3", below(d3["ne"], 1))
    m3.metric("Gap", f"{abs(d3['gap']):.1f} points", "about the same" if d3["same"] else "not the same", delta_color="off")

    fig = go.Figure()
    for abbr, color in (("IA", FOREST), ("NE", OCHRE)):
        g = table[table.state_alpha == abbr].sort_values("level")
        fig.add_trace(go.Bar(x=[LEVEL_SHORT[int(lv)] for lv in g.level], y=g.mean_loss, name=STATE_NAMES[abbr], marker_color=color,
                             text=[f"{v:.0f}%" for v in g.mean_loss], customdata=g.n,
                             hovertemplate="%{x}: %{y:.1f}% (%{customdata} county-years)<extra></extra>", **BAR_TEXT))
    fig.update_layout(barmode="group")
    layout(fig, 340).update_yaxes(title="Yield compared with normal (%)")
    st.plotly_chart(fig, width="stretch")

    # --- 3. Your estimate --------------------------------------------------
    chapter("Step 3", "What it means for your farm", "Move the slider to the drought level you want to plan for. Check the U.S. Drought Monitor for where your county stands today.")
    level = st.select_slider("Worst drought level this season", options=[lv for lv, *_ in DROUGHT_LEVELS], value=4, format_func=LEVEL_NAME.get)
    html("<div class='legend'>" + "".join(
        f"<div class='{'on ' if lv == level else ''}{'dark' if lv in (1, 2) else ''}' style='background:{c}'>{s}</div>"
        for lv, _, s, c, _ in DROUGHT_LEVELS) + "</div>")
    st.markdown(f"**{LEVEL_NAME[level]}.** {DROUGHT_LEVELS[level][4]}")

    row = cell(a["irr_check"], "NE", level, irrig) if irrig else cell(check, state, level)
    typical = typical_yield(panel, state, county, crop)
    lost = None
    if row is None or pd.isna(typical):
        st.info(f"We have no past {crop_name} years at this drought level for {STATE_NAMES[state]}"
                f"{' ' + IRRIG_LABEL[irrig] if irrig else ''}, or no yield record for {county_short} County. Try a nearby level or county.")
    else:
        change = row.train_mean
        expected = typical * (1 + change / 100)
        lost = max((typical - expected) * acres, 0)
        loss = -change
        if abs(loss) < 0.5:
            color, tone = LEVEL_COLOR[0], "Yield about normal at this level."
        elif loss >= 12:
            color, tone = LEVEL_COLOR[4], "Large expected loss. Worth planning for now."
        elif loss >= 4:
            color, tone = LEVEL_COLOR[3], "Some expected loss."
        elif loss > 0:
            color, tone = LEVEL_COLOR[2], "A small expected loss."
        else:
            color, tone = LEVEL_COLOR[0], "Past years at this level did not lose yield on average."
        html(f"""
        <div class="result" style="--c:{color}">
          <div class="head">{icon(crop, 64)}<div>
            <div class="big">{'About normal' if abs(loss) < 0.5 else f"{abs(loss):.0f}% {'lower' if loss > 0 else 'higher'} yield"}</div>
            <div class="sub">{CROP_NAMES[crop]} in {STATE_NAMES[state]}{' · ' + IRRIG_LABEL[irrig] if irrig else ''} at {lc_first(LEVEL_NAME[level])} · {tone}</div>
          </div></div>
        </div>""")
        m1, m2, m3 = st.columns(3)
        m1.metric("Typical yield", f"{typical:.0f} bu/ac", help=f"{county_short} County's recent trend yield, in a normal year.")
        m2.metric("Expected yield", f"{expected:.0f} bu/ac", f"{expected - typical:+.0f} bu/ac")
        m3.metric(f"Bushels at risk on {acres:,} acres", f"{lost:,.0f}")
        css, text = verdict(row)
        html(f"<div class='callout'><b>Can you trust it?</b> <span class='{css}'>{text}</span></div>")
        st.markdown(
            f"<span class='small'>Based on <b>{row.train_n}</b> county-years in {STATE_NAMES[state]}{' ' + IRRIG_LABEL[irrig] if irrig else ''} "
            f"from 2000 to 2012. This is an average of past years, not a forecast.</span>", unsafe_allow_html=True)

    # --- 4. Did it hold up? ------------------------------------------------
    chapter("Step 4", "Did it hold up on years we hadn't used?",
            "We built the numbers from 2000 to 2012, then checked them against 2013 to 2025. An estimate counts as holding up if later years landed within "
            f"{TOLERANCE_PTS:g} points of it.")
    strict = st.session_state.get("trend_version", MASTER_TREND) == STRICT_TREND
    ck = analysis(crop, STRICT_ANOM if strict else "yield_anomaly_pct")
    chk = ck["check"]
    s = rt.score(chk)
    m1, m2, m3 = st.columns(3)
    m1.metric(f"Estimates within {TOLERANCE_PTS:g} points", f"{s['share_within_tol']:.0%}")
    m2.metric("Average miss", f"{s['weighted_mae']:.1f} points")
    m3.metric("Estimates we could check", f"{s['cells_scored']} of {len(chk)}",
              help=f"A drought level is checked only when it has at least {MIN_CELL_N} county-years in both periods.")
    st.markdown(f"**{STATE_NAMES[state]} {crop_name}, drought level by level**")
    html(check_table(chk, state))
    g = chk[chk.state_alpha == state].sort_values("level")
    g = g[g.train_n > 0]
    fig = go.Figure()
    for col, label, color, n in (("train_mean", "2000–2012 (our estimate)", FOREST, "train_n"), ("test_mean", "2013–2025 (what happened)", OCHRE, "test_n")):
        fig.add_trace(go.Bar(x=[LEVEL_SHORT[int(lv)] for lv in g.level], y=g[col], name=label, marker_color=color, customdata=g[n],
                             text=[f"{v:.0f}%" if pd.notna(v) else "" for v in g[col]],
                             hovertemplate="%{x}: %{y:.1f}% (%{customdata} county-years)<extra></extra>", **BAR_TEXT))
    fig.update_layout(barmode="group")
    layout(fig, 320).update_yaxes(title="Yield compared with normal (%)")
    st.plotly_chart(fig, width="stretch")

    with st.expander("For the data-curious: every estimate, both states, and a stricter test"):
        if STRICT_ANOM in panel:
            st.radio("Trend version", [MASTER_TREND, STRICT_TREND], key="trend_version",
                     help="Each county's trend line is what 'normal' means. The master trend is fitted on all 26 years, so it sees the later years and flatters the check. "
                          "The strict trend is fitted on 2000–2012 only, so 2013–2025 is a true out-of-sample test.")
        shown = pd.DataFrame({
            "State": chk.state_alpha.map(STATE_NAMES), "Drought level": chk.level_label,
            "2000–2012 mean (%)": chk.train_mean.round(1), "2000–2012 county-years": chk.train_n,
            "2013–2025 mean (%)": chk.test_mean.round(1), "2013–2025 county-years": chk.test_n,
            "Miss (points)": chk.abs_error.round(1),
            "Did it hold up?": [verdict(r)[1].split(".")[0] for r in chk.itertuples()],
        })
        st.dataframe(shown, width="stretch", hide_index=True)
        pts = chk.dropna(subset=["train_mean", "test_mean"]).assign(State=lambda d: d.state_alpha.map(STATE_NAMES))
        sc_fig = px.scatter(pts, x="train_mean", y="test_mean", color="State", text="level_label",
                            color_discrete_map={"Iowa": FOREST, "Nebraska": OCHRE},
                            labels={"train_mean": "2000–2012 mean (%)", "test_mean": "2013–2025 mean (%)"})
        lo = float(min(pts.train_mean.min(), pts.test_mean.min())) - 2
        hi = float(max(pts.train_mean.max(), pts.test_mean.max())) + 2
        sc_fig.add_trace(go.Scatter(x=[lo, hi, hi, lo], y=[lo + TOLERANCE_PTS, hi + TOLERANCE_PTS, hi - TOLERANCE_PTS, lo - TOLERANCE_PTS],
                                    fill="toself", fillcolor="rgba(91,97,87,0.15)", line_width=0, name=f"±{TOLERANCE_PTS:g} points", hoverinfo="skip"))
        sc_fig.add_trace(go.Scatter(x=[lo, hi], y=[lo, hi], mode="lines", line=dict(dash="dash", color=MUTED), name="Same in both periods"))
        sc_fig.update_traces(textposition="top center", selector=dict(mode="markers+text"))
        st.plotly_chart(layout(sc_fig, 380), width="stretch")
        st.caption("Dots inside the shaded band held up. Dots on the dashed line landed exactly where 2000–2012 said they would.")

    # --- 5. Why the states differ -----------------------------------------
    chapter("Step 5", "Why the same label costs different amounts", "Two things explain most of the gap: when the dry spell arrives, and whether the field can be watered.")
    st.markdown("### Peak-season drought versus early drought")
    tm = a["timing"]
    if len(tm):
        fig = go.Figure()
        for when, label, color in (("peak", "Peak (July to August)", LEVEL_COLOR[4]), ("early", "Early (May to June)", LEVEL_COLOR[2])):
            g = tm[tm.timing == when]
            fig.add_trace(go.Bar(x=[STATE_NAMES[x] for x in g.state_alpha], y=g.mean_loss, name=label, marker_color=color, customdata=g.n,
                                 text=[f"{v:.0f}%" for v in g.mean_loss],
                                 hovertemplate="%{x}: %{y:.1f}% (%{customdata} county-years)<extra></extra>", **BAR_TEXT))
        fig.update_layout(barmode="group")
        layout(fig, 320).update_yaxes(title="Yield compared with normal at D3 (%)")
        st.plotly_chart(fig, width="stretch")
        share = peak_share(a)
        thin = tm[(tm.timing == "early") & (tm.n < MIN_CELL_N)]
        thin_note = (" Early-only D3 seasons are too rare to quote for " + " and ".join(STATE_NAMES[x] for x in thin.state_alpha) +
                     f" (fewer than {MIN_CELL_N} county-years).") if len(thin) else ""
        yrs = a["timing_years"]
        st.markdown(f"**{share:.0%}** of D3 seasons had severe drought (D2 or worse) reach the county in July or August.{thin_note}")
        st.caption(f"Years {yrs[0]}–{yrs[1]}, {a['timing_counties']} counties with a timing label. "
                   "Peak means severe drought reached the county in July or August; early means only before July.")

    st.markdown("### Nebraska: irrigated versus dryland counties")
    it = a["irr_table"]
    if len(it):
        fig = go.Figure()
        for grp, label, color in (("mostly irrigated", "Mostly irrigated counties", FOREST), ("mostly dryland", "Mostly dryland counties", ORANGE)):
            g = it[it.irrig_group == grp].sort_values("level")
            fig.add_trace(go.Bar(x=[LEVEL_SHORT[int(lv)] for lv in g.level], y=g.mean_loss, name=label, marker_color=color, customdata=g.n,
                                 text=[f"{v:.0f}%" for v in g.mean_loss],
                                 hovertemplate="%{x}: %{y:.1f}% (%{customdata} county-years)<extra></extra>", **BAR_TEXT))
        fig.update_layout(barmode="group")
        layout(fig, 320).update_yaxes(title="Yield compared with normal (%)")
        st.plotly_chart(fig, width="stretch")
        st.caption("Irrigation data runs 2000–2018. Each Nebraska county gets one average irrigated share and is grouped at 50%. Iowa is rain-fed and is not split.")

    # --- 6. Get ready ------------------------------------------------------
    chapter("Step 6", "Getting ready", "General steps farmers take when drought looks likely. Your county extension office and crop insurance agent can tailor them to your fields.")
    html(f"<div class='photo-band' style='background-image:url(\"{photo('drought.jpg')}\")'></div>"
         "<div class='small'>Drought-damaged corn. USDA photo, public domain.</div>")
    d1, d2 = cell(check, state, 2), cell(check, state, 3)
    ia_row = cell(check, "IA", 4)
    share = peak_share(a)
    insurance = ("Compare your coverage with the loss estimate above and ask when a loss has to be reported." if lost is None else
                 f"At {lc_first(LEVEL_NAME[level])} your estimate is about {lost:,.0f} bushels short on {acres:,} acres. "
                 "Compare that with your coverage and ask when a loss has to be reported.")
    storage = ("A yield shortfall changes how much grain you store or sell. Revisit contracts early." if lost is None else
               f"A shortfall of about {lost:,.0f} bushels changes how much grain you store or sell. Revisit contracts early.")
    if state == "NE" and dry is not None and irr is not None:
        water = (f"At extreme drought (D3) in 2000–2012, Nebraska {crop_name} lost {abs(dry.train_mean):.0f}% on dryland and "
                 f"{abs(irr.train_mean):.0f}% on irrigated ground. If you irrigate, check pumps and schedules early.")
    elif state == "IA" and ia_row is not None:
        water = f"Iowa {crop_name} has no irrigation cushion: at extreme drought (D3) it lost {abs(ia_row.train_mean):.0f}%. Decide early which fields matter most."
    else:
        water = "Decide early which fields matter most if water runs short."
    drought_map = "Watch your county's weekly level on the U.S. Drought Monitor map."
    if d1 is not None and d2 is not None:
        drought_map = (f"In {STATE_NAMES[state]}, {crop_name} {'lost' if d1.train_mean < 0 else 'gained'} {abs(d1.train_mean):.0f}% at moderate drought (D1) "
                       f"and {'lost' if d2.train_mean < 0 else 'gained'} {abs(d2.train_mean):.0f}% at severe drought (D2). " + drought_map)
    when = (f"{share:.0%} of extreme-drought seasons had severe drought reach the county in July or August. Watch those weeks closely."
            if share is not None else "Know which weeks of the season carry the most risk.")
    actions = [
        ("Talk to your crop insurance agent", insurance),
        ("Plan your water", water),
        ("Watch the weekly drought map", drought_map),
        ("Know your risky weeks", when),
        ("Line up storage and marketing", storage),
        ("Call your county extension office", "They know local conditions and can point you to drought assistance programs."),
    ]
    html("".join(f"<div class='action'><div class='num'>{i}</div><div><b>{t}</b>{d}</div></div>" for i, (t, d) in enumerate(actions, 1)))

    # --- About the data ----------------------------------------------------
    chapter("About the numbers")
    st.markdown(f"**How many county-years sit behind each number ({CROP_NAMES[crop]})**")
    cov = a["coverage"]
    cov = pd.DataFrame({"State": cov.state_alpha.map(STATE_NAMES), "Drought level": cov.max_drought_severity.map(lambda v: LEVEL_NAME[int(v)]),
                        "2000–2012": cov.train, "2013–2025": cov.test})
    st.dataframe(cov, width="stretch", hide_index=True)
    thin_cells = check[check.train_n < MIN_CELL_N]
    thin_text = ("".join(f"- {STATE_NAMES[r.state_alpha]} {r.level_label} has only {r.train_n} county-years from 2000–2012. Don't quote it.\n"
                         for r in thin_cells.itertuples()))
    st.markdown("**Limitations**")
    st.markdown(
        "- Drought level is the season's worst U.S. Drought Monitor category, so a single bad week counts the same as a whole bad season.\n"
        "- County yields come from USDA NASS surveys. Small counties drop out in some years.\n"
        "- The strict trend is fitted on 2000–2012 only, so 2013–2025 is a real out-of-sample check. "
        "The master trend uses all years and flatters the check.\n"
        "- Irrigation shares run 2000–2018 and are averaged to one value per county.\n"
        "- Estimates are averages of past years, not forecasts.\n" + thin_text)
    st.markdown("**Credits**")
    st.markdown(
        "- **U.S. Drought Monitor:** The U.S. Drought Monitor is jointly produced by the National Drought "
        "Mitigation Center at the University of Nebraska-Lincoln, the United States Department of Agriculture, "
        "and the National Oceanic and Atmospheric Administration.\n"
        "- **USDA NASS:** This product uses the NASS API but is not endorsed or certified by NASS.\n"
        "- **NOAA ACIS:** Weather data from the Applied Climate Information System (ACIS), NOAA Regional Climate Centers.\n"
        "- **Soil:** Soil Survey Staff, Natural Resources Conservation Service, United States Department of "
        "Agriculture. Soil Survey Geographic (SSURGO) Database, via Soil Data Access.\n"
        "- **Photos:** USDA and NRCS, public domain, via Wikimedia Commons.")
    html("<p class='small'>Built by Team Wolverine for the Data to Harvest Hackathon, Delaware State University.</p>")


page = st.session_state.get("page", "welcome")
if page == "dashboard" and "user" not in st.session_state:
    page = "login"
{"welcome": show_welcome, "login": show_login, "dashboard": show_dashboard}[page]()
