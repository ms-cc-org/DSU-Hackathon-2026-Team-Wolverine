import base64
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.data_loader import load_master
from wolverine import drought_timing as dt
from wolverine.contracts import CROPS, STATES

st.set_page_config(page_title="Drought Yield Estimator", page_icon=":ear_of_corn:", layout="wide")

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
LEVELS = [
    # level, label, short, colour, what it means on the farm
    (0, "No drought", "None", "#4F7D4F", "Normal moisture."),
    (1, "Abnormally dry (D0)", "D0", "#C2BE5A", "Going into drought. Crops may begin to stress."),
    (2, "Moderate drought (D1)", "D1", "#DDAE3A", "Some crop damage is likely. Fields and pastures are dry."),
    (3, "Severe drought (D2)", "D2", "#D9772B", "Crop losses are likely. Water shortages are common."),
    (4, "Extreme drought (D3)", "D3", "#B5402E", "Major crop losses. Widespread water shortages."),
    (5, "Exceptional drought (D4)", "D4", "#7A2417", "Exceptional and widespread losses."),
]
LEVEL_NAME = {lv: name for lv, name, *_ in LEVELS}
LEVEL_COLOR = {lv: c for lv, _, _, c, _ in LEVELS}
LEVEL_SHORT = {lv: s for lv, _, s, *_ in LEVELS}

STATE_NAMES = {"IA": "Iowa", "NE": "Nebraska"}
CROP_NAMES = {"CORN": "Corn", "SOYBEANS": "Soybeans"}
CROP_BLURB = {"CORN": "Grain corn, bushels per acre", "SOYBEANS": "Soybeans, bushels per acre"}
TIMING_CHOICES = {
    "Not sure": None,
    "Early (May to June)": "early",
    "Peak season (July to August)": "peak",
    "Late (September on)": "late",
}
TIMING_LABEL = {"none": "No severe drought", "early": "Early (May to June)",
                "peak": "Peak (July to August)", "late": "Late (September on)"}
IRRIG_CHOICES = {"Irrigated": "mostly irrigated", "Rain only (dryland)": "mostly dryland"}

MIN_COUNTY_N = 5    # fewer matching county-years than this and we widen to the state
MIN_STATE_N = 10

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
</style>
""")


def go_to(page):
    st.session_state.page = page
    st.rerun()


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def get_data():
    """County x crop x year records, with drought timing and (Nebraska) irrigation group joined on."""
    df = load_master()
    df = df[df["state_alpha"].isin(STATES) & df["crop"].isin(CROPS)]
    df = df.dropna(subset=["yield_per_acre", "yield_anomaly_pct", "max_drought_severity"]).copy()
    df["level"] = df["max_drought_severity"].astype(int)
    df["trend_yield"] = df["yield_per_acre"] / (1 + df["yield_anomaly_pct"] / 100)
    df = df.merge(dt.drought_timing(), on=["fips", "crop", "year"], how="left")
    df = df.merge(dt.irrigation_groups(), on=["fips", "crop"], how="left")
    return df


def level_loss(df, state, crop, level, irrig=None):
    """Average yield loss (%) at one drought level for a state and crop. state=None uses both states."""
    rows = df[(df["crop"] == crop) & (df["level"] == level)]
    if state:
        rows = rows[rows["state_alpha"] == state]
    if irrig:
        rows = rows[rows["irrig_group"] == irrig]
    return -rows["yield_anomaly_pct"].mean() if len(rows) >= MIN_STATE_N else None


def timing_means(df, crop, state=None):
    """Average yield change vs trend by drought timing (none / early / peak / late)."""
    rows = df[df["crop"] == crop]
    if state:
        rows = rows[rows["state_alpha"] == state]
    return rows.groupby("timing")["yield_anomaly_pct"].mean()


def loss_text(v):
    """'5% loss' or '3% gain' for a loss value in percent."""
    return f"{abs(v):.0f}% {'loss' if v > 0 else 'gain'}"


def estimate(df, state, county, crop, level, timing=None, irrig=None):
    """Average yield change vs trend in past years at this drought level.

    Starts with the farmer's own county and widens step by step (state, then drop the timing
    filter, then drop the irrigation filter) until enough past years match. Returns None if nothing does.
    """
    base = df[(df["state_alpha"] == state) & (df["crop"] == crop) & (df["level"] == level)]

    def attempt(use_timing, use_irrig, county_only):
        rows = base
        if use_irrig and irrig:
            rows = rows[rows["irrig_group"] == irrig]
        if use_timing and timing:
            rows = rows[rows["timing"] == timing]
        if county_only:
            rows = rows[rows["county_name"] == county]
        return rows

    steps = [
        (True, True, True, MIN_COUNTY_N, "your county"),
        (True, True, False, MIN_STATE_N, f"{STATE_NAMES[state]} counties"),
        (False, True, False, MIN_STATE_N, f"{STATE_NAMES[state]} counties (any timing)"),
        (False, False, False, MIN_STATE_N, f"{STATE_NAMES[state]} counties (any timing or water setup)"),
    ]
    for use_timing, use_irrig, county_only, need, basis in steps:
        rows = attempt(use_timing, use_irrig, county_only)
        if len(rows) >= need:
            a = rows["yield_anomaly_pct"]
            return {"mean": a.mean(), "lo": a.quantile(0.25), "hi": a.quantile(0.75), "n": len(rows), "basis": basis}
    return None


# ---------------------------------------------------------------------------
# Page 1: welcome
# ---------------------------------------------------------------------------
def show_welcome():
    html(f"""
    <div class="hero">
      <div class="copy">
        <div class="eyebrow">Iowa and Nebraska · Corn and soybeans</div>
        <h1>When the rain stops, what does it cost the harvest?</h1>
        <p>Pick your county, your crop and a drought level. We show what past droughts did to yields on farms like yours, so you can plan before the season turns.</p>
      </div>
      <div class="pic" style="background-image:url('{photo('hero.jpg')}')"></div>
    </div>
    """)
    st.write("")
    c1, c2 = st.columns([1, 2])
    if c1.button("Get started", type="primary", width="stretch"):
        go_to("login")
    c2.markdown("<span class='small'>Free to use. Based on public drought and crop records.</span>", unsafe_allow_html=True)

    df = get_data()
    sev = df[df["level"] >= 4]
    ia = -sev[(sev.state_alpha == "IA") & (sev.crop == "CORN")]["yield_anomaly_pct"].mean()
    ne = -sev[(sev.state_alpha == "NE") & (sev.crop == "CORN")]["yield_anomaly_pct"].mean()

    tm = timing_means(df, "CORN")
    dry, wet = level_loss(df, "NE", "CORN", 4, "mostly dryland"), level_loss(df, "NE", "CORN", 4, "mostly irrigated")
    step3 = (f"Corn hit by drought in July and August has run {tm['peak']:+.0f}% against trend, versus {tm['early']:+.0f}% when drought comes in May and June. "
             f"At extreme drought (D3), Nebraska dryland corn had a {loss_text(dry)} and irrigated corn a {loss_text(wet)}.")
    chapter("The story in three parts")
    html(f"""
    <div class="steps">
      <div class="step"><div class="k">1</div><b>Drought comes in levels</b>The U.S. Drought Monitor rates every county each week, from abnormally dry (D0) to exceptional (D4).</div>
      <div class="step"><div class="k">2</div><b>Each level costs yield</b>In Iowa, extreme drought (D3 or worse) has cut corn yields about {ia:.0f}% below trend. In Nebraska, about {ne:.0f}%.</div>
      <div class="step"><div class="k">3</div><b>Timing and water change the answer</b>{step3}</div>
    </div>
    """)
    html(f"""
    <div class="stats">
      <div class="stat"><div class="n">{len(df):,}</div><div class="t">county-crop-years of yield records</div></div>
      <div class="stat"><div class="n">{df['fips'].nunique()}</div><div class="t">Iowa and Nebraska counties with yield records</div></div>
      <div class="stat"><div class="n">{int(df['year'].min())} to {int(df['year'].max())}</div><div class="t">years of drought and yield history</div></div>
    </div>
    <p class="small">Yield records: USDA NASS. Drought levels: U.S. Drought Monitor. Photos: USDA and NRCS, public domain.</p>
    """)


# ---------------------------------------------------------------------------
# Page 2: login
# ---------------------------------------------------------------------------
def show_login():
    left, right = st.columns([1, 1], gap="large")
    with left:
        html(f"<div class='brand'>{icon('CORN', 34)}{icon('SOYBEANS', 34)} Drought Yield Estimator</div>")
        html("<div class='sec' style='margin-top:1rem'><div class='eyebrow'>Sign in</div><h2>Welcome back</h2>"
             "<p class='lead'>Log in to see your county's drought and yield story.</p></div>")
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
def layout(fig, height=340):
    fig.update_layout(
        height=height, margin=dict(t=10, b=10, l=10, r=10), paper_bgcolor=CREAM, plot_bgcolor=CREAM,
        font=dict(family="Source Sans 3, sans-serif", size=15, color=CHARCOAL),
        legend=dict(orientation="h", y=-0.2),
    )
    fig.update_xaxes(showgrid=False, linecolor=MUTED)
    fig.update_yaxes(gridcolor=RULE, zeroline=True, zerolinecolor=MUTED)
    return fig


def show_dashboard():
    with st.spinner("Loading drought and yield records..."):
        try:
            df = get_data()
        except Exception as exc:  # data files missing or a module not merged yet
            st.error("We could not load the data files. Ask the team to check the data folder, then refresh this page.")
            st.caption(f"Technical detail: {exc}")
            return

    top = st.columns([5, 1])
    top[0].markdown(f"<div class='brand'>{icon('CORN', 34)}{icon('SOYBEANS', 34)} Drought Yield Estimator</div>", unsafe_allow_html=True)
    if top[1].button("Log out", width="stretch"):
        for k in ("user", "crop"):
            st.session_state.pop(k, None)
        go_to("welcome")

    # --- 1. Your farm ------------------------------------------------------
    chapter("Step 1", "Tell us about your farm", "Your answers stay on this screen. We use them to find the past years that look most like yours.")
    c1, c2, c3 = st.columns([1, 1.3, 1])
    state = c1.selectbox("State", STATES, format_func=STATE_NAMES.get)
    counties = sorted(df[df["state_alpha"] == state]["county_name"].unique())
    county = c2.selectbox("County", counties, format_func=lambda c: c.replace(" County", ""))
    acres = c3.number_input("Acres planted", min_value=1, max_value=100000, value=160, step=10)

    crop = st.session_state.setdefault("crop", "CORN")
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

    irrig = None
    if state == "NE":
        d_loss, i_loss = (level_loss(df, "NE", crop, 4, g) for g in ("mostly dryland", "mostly irrigated"))
        irrig_help = (f"At extreme drought (D3), Nebraska {CROP_NAMES[crop].lower()} had a {loss_text(d_loss)} in dryland counties "
                      f"and a {loss_text(i_loss)} in irrigated counties.") if d_loss is not None and i_loss is not None else None
        choice = st.radio("How is this field watered?", list(IRRIG_CHOICES), horizontal=True, help=irrig_help)
        irrig = IRRIG_CHOICES[choice]

    county_short = county.replace(" County", "")
    crop_name = CROP_NAMES[crop].lower()
    hist = df[(df["state_alpha"] == state) & (df["county_name"] == county) & (df["crop"] == crop)].sort_values("year")

    # --- 2. County story ---------------------------------------------------
    chapter("Step 2", f"What drought has done in {county_short} County",
            f"Each dot is one year of {crop_name} yield. Dot colour shows the worst drought level that year. The dashed line is the yield trend without drought.")
    if hist.empty:
        st.info(f"We have no {crop_name} yield records for {county_short} County. Try a nearby county or the other crop.")
    else:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=hist["year"], y=hist["trend_yield"], mode="lines", name="Trend",
                                 line=dict(color=MUTED, dash="dash", width=2)))
        for lv, name, short, color, _ in LEVELS:
            sub = hist[hist["level"] == lv]
            if len(sub):
                fig.add_trace(go.Scatter(x=sub["year"], y=sub["yield_per_acre"], mode="markers", name=f"{short} {name.split(' (')[0].replace(' drought','')}",
                                         marker=dict(color=color, size=12, line=dict(color=CHARCOAL, width=1)),
                                         hovertemplate="%{x}: %{y:.0f} bu/acre<extra></extra>"))
        layout(fig, 360).update_yaxes(title="Bushels per acre")
        st.plotly_chart(fig, width="stretch")

        sev = hist[hist["level"] >= 3]
        calm = hist[hist["level"] <= 1]
        worst = hist.loc[hist["yield_anomaly_pct"].idxmin()]
        if len(sev):
            msg = (f"In <b>{len(sev)} of {len(hist)}</b> years, drought here reached severe (D2) or worse, and {crop_name} yields averaged "
                   f"<b>{pct(sev['yield_anomaly_pct'].mean(), True)}</b> against trend")
            if len(calm):
                msg += f", compared with <b>{pct(calm['yield_anomaly_pct'].mean(), True)}</b> in years with little or no drought"
            msg += ". "
            if sev["precip_anomaly_pct"].notna().any():
                msg += (f"In those dry years, rainfall ran about <b>{abs(sev['precip_anomaly_pct'].mean()):.0f}% "
                        f"{'below' if sev['precip_anomaly_pct'].mean() < 0 else 'above'}</b> normal and the county saw "
                        f"<b>{sev['extreme_heat_days'].mean():.0f}</b> extreme-heat days on average, versus "
                        f"<b>{hist['extreme_heat_days'].mean():.0f}</b> across all years. ")
        else:
            msg = f"In none of {len(hist)} years did drought here reach severe (D2). "
        msg += (f"The hardest year was <b>{int(worst['year'])}</b>: <b>{worst['yield_per_acre']:.0f}</b> bushels per acre, "
                f"{abs(worst['yield_anomaly_pct']):.0f}% below trend, with drought at {LEVEL_NAME[int(worst['level'])].lower()}.")
        html(f"<div class='callout'>{msg}</div>")

    # --- 3. What if --------------------------------------------------------
    chapter("Step 3", "What if drought hits this season?", "Move the slider to the drought level you want to plan for. Check the U.S. Drought Monitor for where your county stands today.")
    level = st.select_slider("Worst drought level this season", options=[lv for lv, *_ in LEVELS], value=3, format_func=LEVEL_NAME.get)
    html("<div class='legend'>" + "".join(
        f"<div class='{'on ' if lv == level else ''}{'dark' if lv in (1, 2) else ''}' style='background:{c}'>{s}</div>"
        for lv, _, s, c, _ in LEVELS) + "</div>")
    st.markdown(f"**{LEVEL_NAME[level]}.** {LEVELS[level][4]}")

    timing = None
    if level >= 3:
        tmeans = timing_means(df, crop, state)
        have = "has" if crop == "CORN" else "have"
        timing_help = (f"{CROP_NAMES[crop]} in {STATE_NAMES[state]} {have} averaged {tmeans['peak']:+.0f}% against trend when severe drought hit in "
                       f"July and August, {tmeans['early']:+.0f}% when it hit in May and June, and {tmeans['late']:+.0f}% when it came in September or later."
                       ) if {"peak", "early", "late"} <= set(tmeans.index) else None
        t_choice = st.radio("When would the dry spell hit?", list(TIMING_CHOICES), horizontal=True, help=timing_help)
        timing = TIMING_CHOICES[t_choice]

    est = estimate(df, state, county, crop, level, timing, irrig)
    lost = None
    if est is None or hist.empty:
        st.info("We do not have enough past years at this drought level to give a fair estimate. Try a nearby level.")
    else:
        typical = hist.sort_values("year").tail(3)["trend_yield"].mean()
        change = est["mean"]
        expected = typical * (1 + change / 100)
        lost = max((typical - expected) * acres, 0)
        loss = -change
        if loss >= 12:
            color, verdict = LEVEL_COLOR[4], "Large expected loss. Worth planning for now."
        elif loss >= 4:
            color, verdict = LEVEL_COLOR[3], "Some expected loss."
        elif loss > 0:
            color, verdict = LEVEL_COLOR[2], "A small expected loss."
        else:
            color, verdict = LEVEL_COLOR[0], "Past years at this level did not lose yield on average."
        word = "lower" if loss > 0 else "higher"
        lo, hi = est["lo"], est["hi"]
        html(f"""
        <div class="result" style="--c:{color}">
          <div class="head">{icon(crop, 64)}<div>
            <div class="big">{abs(loss):.0f}% {word} yield</div>
            <div class="sub">{CROP_NAMES[crop]} in {county_short} County at {LEVEL_NAME[level].lower()} · {verdict}</div>
          </div></div>
        </div>""")
        m1, m2, m3 = st.columns(3)
        m1.metric("Typical yield", f"{typical:.0f} bu/ac", help="Your county's recent trend yield, in a normal year.")
        m2.metric("Expected yield", f"{expected:.0f} bu/ac", f"{expected - typical:+.0f} bu/ac")
        m3.metric(f"Bushels at risk on {acres:,} acres", f"{lost:,.0f}")
        st.markdown(
            f"<span class='small'>Based on <b>{est['n']}</b> past years in {est['basis']}. In half of those years the change was between "
            f"<b>{pct(lo, True)}</b> and <b>{pct(hi, True)}</b>. This is a historical average, not a forecast.</span>",
            unsafe_allow_html=True)

    # --- 4. What changes the answer ---------------------------------------
    chapter("Step 4", "What makes it better or worse", "Two things change what drought costs: the loss at each level, and when the dry spell arrives.")
    st.markdown(f"### Loss grows with each drought level")
    xs, ys, cs = [], [], []
    for lv, _, short, c, _ in LEVELS:
        e = estimate(df, state, county, crop, lv, None, irrig)
        if e:
            xs.append(f"{short}" if lv else "None")
            ys.append(-e["mean"])
            cs.append(c if lv == level else SAGE)
    if xs:
        fig = go.Figure(go.Bar(x=xs, y=ys, marker_color=cs, text=[f"{v:.0f}%" for v in ys], textposition="outside", cliponaxis=False))
        layout(fig, 320).update_yaxes(title="Average yield loss (%)")
        st.plotly_chart(fig, width="stretch")

    st.markdown(f"### When the dry spell hits matters")
    pool = df[(df["state_alpha"] == state) & (df["crop"] == crop)]
    if irrig:
        pool = pool[pool["irrig_group"] == irrig]
    tm = pool.groupby("timing")["yield_anomaly_pct"].agg(["mean", "count"]).reindex(["none", "early", "peak", "late"]).dropna()
    if len(tm):
        fig = go.Figure(go.Bar(
            x=[TIMING_LABEL[t] for t in tm.index], y=tm["mean"],
            marker_color=[FOREST if v >= 0 else LEVEL_COLOR[4] for v in tm["mean"]],
            text=[f"{v:+.0f}%" for v in tm["mean"]], textposition="outside", cliponaxis=False))
        layout(fig, 320).update_yaxes(title="Yield vs trend (%)")
        st.plotly_chart(fig, width="stretch")
        worst_t = tm["mean"].idxmin()
        st.markdown(f"For {crop_name} in {STATE_NAMES[state]}, drought that arrives in the **{TIMING_LABEL[worst_t].lower()}** window has cost the most. "
                    "Severe drought (D2 or worse) is counted by the month it first appears.")

    st.markdown("### Irrigation changes the answer" if state == "NE" else "### Water setup")
    if state == "NE":
        ne = df[(df["state_alpha"] == "NE") & (df["crop"] == crop) & df["irrig_group"].notna()]
        fig = go.Figure()
        for grp, label, color in [("mostly irrigated", "Irrigated counties", FOREST), ("mostly dryland", "Dryland counties", LEVEL_COLOR[3])]:
            g = ne[ne["irrig_group"] == grp].groupby("level")["yield_anomaly_pct"].agg(["mean", "count"])
            g = g[g["count"] >= MIN_STATE_N]
            fig.add_trace(go.Bar(x=[LEVEL_SHORT[i] if i else "None" for i in g.index], y=-g["mean"], name=label, marker_color=color))
        fig.update_layout(barmode="group")
        layout(fig, 320).update_yaxes(title="Average yield loss (%)")
        st.plotly_chart(fig, width="stretch")
        st.markdown("Nebraska counties are grouped by whether most of their cropland is irrigated. If you can irrigate, past droughts cost far less.")
    else:
        ia, ne_i, ne_d = (level_loss(df, s_, crop, 4, g) for s_, g in (("IA", None), ("NE", "mostly irrigated"), ("NE", "mostly dryland")))
        line = (f"Iowa is rain-fed, so drought reaches the crop directly. At extreme drought (D3), Iowa {crop_name} had a {loss_text(ia)}, "
                f"compared with a {loss_text(ne_i)} in irrigated Nebraska counties and a {loss_text(ne_d)} in dryland Nebraska counties.")
        st.markdown(line if None not in (ia, ne_i, ne_d) else "Iowa is rain-fed, so drought reaches the crop directly.")

    # --- 5. Get ready ------------------------------------------------------
    chapter("Step 5", "Getting ready", "General steps farmers take when drought looks likely. Your county extension office and crop insurance agent can tailor them to your fields.")
    html(f"<div class='photo-band' style='background-image:url(\"{photo('drought.jpg')}\")'></div>"
         "<div class='small'>Drought-damaged corn. USDA photo, public domain.</div>")
    d1, d2 = level_loss(df, state, crop, 2), level_loss(df, state, crop, 3)
    tmeans = timing_means(df, crop, state)
    ne_dry, ne_irr = level_loss(df, "NE", crop, 4, "mostly dryland"), level_loss(df, "NE", crop, 4, "mostly irrigated")
    ia_loss = level_loss(df, "IA", crop, 4)
    if lost is not None:
        insurance = (f"At {LEVEL_NAME[level][0].lower() + LEVEL_NAME[level][1:]} your estimate is about {lost:,.0f} bushels short on {acres:,} acres. "
                     "Compare that with your coverage and ask when a loss has to be reported.")
        storage = f"A shortfall of about {lost:,.0f} bushels changes how much grain you store or sell. Revisit contracts early."
    else:
        insurance = "Compare your coverage with the loss estimate above and ask when a loss has to be reported."
        storage = "A yield shortfall changes how much grain you store or sell. Revisit contracts early."
    if state == "NE" and None not in (ne_dry, ne_irr):
        water = (f"At extreme drought (D3), Nebraska {crop_name} had a {loss_text(ne_dry)} on dryland "
                 f"and a {loss_text(ne_irr)} on irrigated ground. If you irrigate, check pumps and schedules early.")
    elif state == "IA" and ia_loss is not None:
        water = f"Iowa {crop_name} has no irrigation cushion: at extreme drought (D3) it had a {loss_text(ia_loss)}. Decide early which fields matter most."
    else:
        water = "Decide early which fields matter most if water runs short."
    drought_map = "Watch your county's weekly level on the U.S. Drought Monitor map."
    if d1 is not None and d2 is not None:
        drought_map = (f"In {STATE_NAMES[state]}, {crop_name} had a {loss_text(d1)} at moderate drought (D1) and a {loss_text(d2)} at severe drought (D2). "
                       + drought_map)
    when = "Know which weeks of the season carry the most risk."
    if {"peak", "early"} <= set(tmeans.index):
        when = (f"{CROP_NAMES[crop]} in {STATE_NAMES[state]} {'has' if crop == 'CORN' else 'have'} averaged {tmeans['peak']:+.0f}% against trend when severe drought hit in July and August, "
                f"versus {tmeans['early']:+.0f}% in May and June. " + when)
    actions = [
        ("Talk to your crop insurance agent", insurance),
        ("Plan your water", water),
        ("Watch the weekly drought map", drought_map),
        ("Know your risky weeks", when),
        ("Line up storage and marketing", storage),
        ("Call your county extension office", "They know local conditions and can point you to drought assistance programs."),
    ]
    html("".join(f"<div class='action'><div class='num'>{i}</div><div><b>{t}</b>{d}</div></div>" for i, (t, d) in enumerate(actions, 1)))

    # --- 6. About the data -------------------------------------------------
    chapter("About the numbers")
    html(f"""
    <p class="small">Yield change is measured against each county's own trend, so a normal year is 0%. Estimates average past years with the same drought level,
    starting with your county and widening to your state when your county has fewer than {MIN_COUNTY_N} matching years.
    Drought level is the worst weekly U.S. Drought Monitor rating each season. Drought timing and irrigation groups come from the team's analysis modules.
    Yields: USDA NASS, 2000 to 2025. Photos: USDA and NRCS, public domain, via Wikimedia Commons. Built by Team Wolverine for the Data to Harvest Hackathon.</p>
    """)


page = st.session_state.get("page", "welcome")
if page == "dashboard" and "user" not in st.session_state:
    page = "login"
{"welcome": show_welcome, "login": show_login, "dashboard": show_dashboard}[page]()
