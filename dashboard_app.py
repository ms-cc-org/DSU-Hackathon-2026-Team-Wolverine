import plotly.graph_objects as go
import streamlit as st

from src.data_loader import load_master
from wolverine.contracts import CROPS, STATES

st.set_page_config(page_title="Drought Yield Estimator", page_icon=":ear_of_corn:", layout="centered")

# Palette (team color scheme)
CREAM = "#F3F0DE"
OLIVE = "#9DA51C"
SAGE = "#DCDBC8"
GOLD = "#F2C14E"
DARK = "#676644"
RED = "#CB3E30"
INK = "#3B3A26"   # darker shade of DARK, for body text

# Login
# Demo accounts only: replace with a real user store before sharing the app outside the team.
DEMO_USERS = {"farmer": "wolverine", "demo": "demo"}

STATE_NAMES = {"IA": "Iowa", "NE": "Nebraska"}
CROP_NAMES = {"CORN": "Corn", "SOYBEANS": "Soybeans"}
UNIT = "bushels per acre"
MIN_COUNTY_N = 5   # fewer matching county-years than this and we use the whole state instead

# U.S. Drought Monitor levels, keyed by the dataset's 0..5 scale (max_drought_severity).
DROUGHT = [
    # level, short name, colour, what it means for a farm
    (0, "No drought",   OLIVE,     "Normal moisture."),
    (1, "Abnormally dry (D0)", "#C8C645", "Going into drought. Crops may start to stress."),
    (2, "Moderate (D1)",  GOLD,      "Some crop damage likely. Pastures and fields are dry."),
    (3, "Severe (D2)",    "#E39B3F", "Crop losses likely. Water shortages are common."),
    (4, "Extreme (D3)",   RED,       "Major crop losses. Widespread water shortages."),
    (5, "Exceptional (D4)", "#8E2A20", "Exceptional and widespread losses."),
]
LEVEL_NAME = {lv: name for lv, name, _, _ in DROUGHT}

CORN_SVG = f"""
<svg viewBox="0 0 64 64" width="{{s}}" height="{{s}}" xmlns="http://www.w3.org/2000/svg">
  <path d="M32 58 C12 50 8 34 14 22 C20 30 26 40 32 58Z" fill="{OLIVE}"/>
  <path d="M32 58 C52 50 56 34 50 22 C44 30 38 40 32 58Z" fill="{OLIVE}"/>
  <ellipse cx="32" cy="29" rx="12" ry="22" fill="{GOLD}" stroke="{DARK}" stroke-width="2"/>
  <g fill="{DARK}" opacity=".55">
    <circle cx="27" cy="14" r="1.6"/><circle cx="32" cy="12" r="1.6"/><circle cx="37" cy="14" r="1.6"/>
    <circle cx="25" cy="21" r="1.6"/><circle cx="32" cy="20" r="1.6"/><circle cx="39" cy="21" r="1.6"/>
    <circle cx="24" cy="28" r="1.6"/><circle cx="32" cy="27" r="1.6"/><circle cx="40" cy="28" r="1.6"/>
    <circle cx="25" cy="35" r="1.6"/><circle cx="32" cy="34" r="1.6"/><circle cx="39" cy="35" r="1.6"/>
    <circle cx="28" cy="42" r="1.6"/><circle cx="36" cy="42" r="1.6"/>
  </g>
</svg>"""

SOY_SVG = f"""
<svg viewBox="0 0 64 64" width="{{s}}" height="{{s}}" xmlns="http://www.w3.org/2000/svg">
  <path d="M10 44 C8 20 30 8 54 14 C56 38 36 56 10 44Z" fill="{OLIVE}" stroke="{DARK}" stroke-width="2"/>
  <circle cx="22" cy="38" r="7" fill="{CREAM}" stroke="{DARK}" stroke-width="1.5"/>
  <circle cx="33" cy="30" r="7" fill="{CREAM}" stroke="{DARK}" stroke-width="1.5"/>
  <circle cx="44" cy="22" r="6" fill="{CREAM}" stroke="{DARK}" stroke-width="1.5"/>
  <path d="M10 44 C6 50 4 54 4 58" stroke="{DARK}" stroke-width="3" fill="none" stroke-linecap="round"/>
</svg>"""

ICONS = {"CORN": CORN_SVG, "SOYBEANS": SOY_SVG}


def icon(crop, size=56):
    return ICONS[crop].replace("{s}", str(size))


st.markdown(
    f"""
    <style>
    html, body, [class*="css"], .stApp {{ font-size: 19px; color: {INK}; }}
    .stApp {{ background: {CREAM}; }}
    h1, h2, h3, h4, label, p, span, div[data-testid="stMarkdownContainer"] {{ color: {INK}; }}
    header[data-testid="stHeader"] {{ background: transparent; }}
    .stButton > button {{ border-radius: 10px; border: 2px solid {DARK}; background: {SAGE}; color: {INK};
        font-weight: 600; padding: .55rem 1rem; }}
    .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {{
        background: {OLIVE}; border-color: {OLIVE}; color: #fff; }}
    .stButton > button:hover {{ border-color: {RED}; color: {RED}; }}
    .stButton > button[kind="primary"]:hover {{ background: {DARK}; border-color: {DARK}; color: #fff; }}
    div[data-baseweb="select"] > div, input {{ background: #fff !important; color: {INK} !important; }}
    div[data-testid="stMetric"] {{ background: {SAGE}; border-radius: 12px; padding: .8rem 1rem; }}
    .hero {{ background: {DARK}; color: {CREAM}; border-radius: 18px; padding: 2.2rem 1.8rem; text-align: center; }}
    .hero h1, .hero p, .hero div {{ color: {CREAM}; }}
    .hero h1 {{ font-size: 2.6rem; margin: .3rem 0; }}
    .step {{ background: {SAGE}; border-radius: 14px; padding: 1rem 1.2rem; height: 100%; }}
    .step b {{ color: {DARK}; }}
    .crop-card {{ border-radius: 14px; padding: .8rem; text-align: center; border: 3px solid {SAGE}; background: #fff; }}
    .crop-card.on {{ border-color: {OLIVE}; background: {CREAM}; }}
    .legend {{ display: flex; gap: 6px; margin: .4rem 0 1rem; }}
    .legend div {{ flex: 1; text-align: center; border-radius: 8px; padding: .5rem .1rem; font-size: .8rem;
        font-weight: 700; color: {INK}; opacity: .55; border: 3px solid transparent; }}
    .legend div.on {{ opacity: 1; border-color: {INK}; }}
    .big-number {{ font-size: 3.4rem; font-weight: 800; line-height: 1.1; }}
    .result {{ border-radius: 16px; padding: 1.2rem 1.4rem; margin: .6rem 0; display: flex; gap: 1rem; align-items: center; }}
    </style>
    """,
    unsafe_allow_html=True,
)


def go_to(page):
    st.session_state.page = page
    st.rerun()


# Page 1: welcome

def show_welcome():
    st.markdown(
        f"""
        <div class="hero">
          <div>{icon("CORN", 72)} {icon("SOYBEANS", 72)}</div>
          <h1>Drought Yield Estimator</h1>
          <p style="font-size:1.25rem">How could drought affect your corn and soybean yields this year?
          Get a clear estimate for your county in Iowa or Nebraska, based on 26 years of real drought and yield records.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")
    a, b, c = st.columns(3)
    a.markdown("<div class='step'><b>1. Pick your farm</b><br>State, county, crop and acres.</div>", unsafe_allow_html=True)
    b.markdown("<div class='step'><b>2. Pick a drought level</b><br>From no drought to exceptional.</div>", unsafe_allow_html=True)
    c.markdown("<div class='step'><b>3. See your estimate</b><br>Expected yield loss in bushels.</div>", unsafe_allow_html=True)
    st.write("")
    if st.button("Get started", type="primary", width="stretch"):
        go_to("login")
    st.caption("Team Wolverine · Data to Harvest Hackathon, Delaware State University, 2026")


# Page 2: login

def show_login():
    st.markdown(f"<div style='text-align:center'>{icon('CORN', 56)} {icon('SOYBEANS', 56)}</div>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align:center'>Welcome back</h2>", unsafe_allow_html=True)
    with st.form("login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in", width="stretch", type="primary")
    if submitted:
        if DEMO_USERS.get(username.strip().lower()) == password:
            st.session_state.user = username.strip().lower()
            go_to("dashboard")
        else:
            st.error("That username or password isn't right. Please try again.")
    st.caption("Team Wolverine demo: log in with username **demo** and password **demo**.")
    if st.button("Back"):
        go_to("welcome")


# Data

@st.cache_data
def get_data():
    df = load_master()
    df = df[df["state_alpha"].isin(STATES) & df["crop"].isin(CROPS)]
    return df.dropna(subset=["yield_per_acre", "yield_anomaly_pct", "max_drought_severity"])


def estimate(df, state, county, crop, level):
    """Average historical yield change for this drought level, county first, state as fallback."""
    crop_rows = df[(df["state_alpha"] == state) & (df["crop"] == crop)]
    match = crop_rows[crop_rows["max_drought_severity"] == level]
    local = match[match["county_name"] == county]
    if len(local) >= MIN_COUNTY_N:
        return local["yield_anomaly_pct"].mean(), len(local), "your county"
    if len(match) > 0:
        return match["yield_anomaly_pct"].mean(), len(match), f"{STATE_NAMES[state]} counties"
    return None, 0, ""


# Page 3: dashboard

def show_dashboard():
    df = get_data()

    top = st.columns([4, 1])
    top[0].markdown(f"<h2>{icon('CORN', 40)}{icon('SOYBEANS', 40)} Drought Yield Estimator</h2>", unsafe_allow_html=True)
    if top[1].button("Log out"):
        for k in ("user", "crop"):
            st.session_state.pop(k, None)
        go_to("welcome")

    st.subheader("1. Tell us about your farm")
    c1, c2 = st.columns(2)
    state = c1.selectbox("State", STATES, format_func=STATE_NAMES.get)
    counties = sorted(df[df["state_alpha"] == state]["county_name"].unique())
    county = c2.selectbox("County", counties, format_func=lambda c: c.replace(" County", ""))
    acres = st.number_input("Acres planted", min_value=1, value=160, step=10)

    st.write("Which crop?")
    crop = st.session_state.setdefault("crop", "CORN")
    cols = st.columns(2)
    for col, key in zip(cols, CROPS):
        col.markdown(
            f"<div class='crop-card {'on' if crop == key else ''}'>{icon(key, 64)}<br><b>{CROP_NAMES[key]}</b></div>",
            unsafe_allow_html=True,
        )
        if col.button("Selected" if crop == key else f"Choose {CROP_NAMES[key].lower()}", key=f"pick_{key}",
                      type="primary" if crop == key else "secondary", width="stretch"):
            st.session_state.crop = key
            st.rerun()

    st.subheader("2. How dry could it get?")
    choice = st.select_slider(
        "Worst drought level this season",
        options=[lv for lv, *_ in DROUGHT],
        value=3,
        format_func=LEVEL_NAME.get,
    )
    level = choice
    _, _, color, meaning = DROUGHT[level]
    st.markdown(
        "<div class='legend'>"
        + "".join(
            f"<div class='{'on' if lv == level else ''}' style='background:{c}'>{n.split(' (')[0]}</div>"
            for lv, n, c, _ in DROUGHT
        )
        + "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(f"**{LEVEL_NAME[level]}:** {meaning}")

    # Results
    st.subheader("3. What to expect")
    anomaly, n, basis = estimate(df, state, county, crop, level)
    if anomaly is None:
        st.info("We don't have enough past years at this drought level to give an estimate.")
        return

    history = df[(df["state_alpha"] == state) & (df["county_name"] == county) & (df["crop"] == crop)].sort_values("year")
    typical = history[history["year"] >= history["year"].max() - 9]["yield_per_acre"].mean()
    expected = typical * (1 + anomaly / 100)
    total_lost = (typical - expected) * acres

    loss_pct = -anomaly
    if loss_pct >= 15:
        bg, fg, verdict = RED, "#fff", "Large expected loss. Worth planning for."
    elif loss_pct >= 5:
        bg, fg, verdict = GOLD, INK, "Some expected loss."
    else:
        bg, fg, verdict = OLIVE, "#fff", "Little to no loss expected historically."
    word = "lower" if loss_pct > 0 else "higher"
    st.markdown(
        f"<div class='result' style='background:{bg};color:{fg}'>{icon(crop, 84)}"
        f"<div><div class='big-number' style='color:{fg}'>{abs(loss_pct):.0f}% {word} yield</div>"
        f"<div style='color:{fg}'>{CROP_NAMES[crop]} in {LEVEL_NAME[level]} · {verdict}</div></div></div>",
        unsafe_allow_html=True,
    )

    m1, m2, m3 = st.columns(3)
    m1.metric("Typical yield", f"{typical:.0f}", help=f"Your county's average over its last 10 reported years, in {UNIT}.")
    m2.metric("Expected yield", f"{expected:.0f}", f"{expected - typical:+.0f}")
    m3.metric(f"Bushels at risk ({acres} ac)", f"{max(total_lost, 0):,.0f}")
    st.caption(
        f"Based on {n} past county-years in {basis} that reached '{LEVEL_NAME[level]}' during the season. "
        "Yields are in bushels per acre. This is a historical average, not a guarantee."
    )

    # Charts
    st.subheader("How loss grows as drought gets worse")
    xs, ys, cs = [], [], []
    for lv, name, c, _ in DROUGHT:
        a, _, _ = estimate(df, state, county, crop, lv)
        if a is not None:
            xs.append(name.split(" (")[0])
            ys.append(-a)
            cs.append(c if lv == level else SAGE)
    fig = go.Figure(go.Bar(x=xs, y=ys, marker_color=cs, text=[f"{v:.0f}%" for v in ys], textposition="outside",
                           textfont_color=INK))
    fig.update_layout(yaxis_title="Average yield loss (%)", height=360, margin=dict(t=20),
                      paper_bgcolor=CREAM, plot_bgcolor=CREAM, font_color=INK)
    st.plotly_chart(fig, width="stretch")

    st.subheader(f"{CROP_NAMES[crop]} yield in {county.replace(' County', '')} County over the years")
    line = go.Figure(go.Scatter(x=history["year"], y=history["yield_per_acre"], mode="lines+markers",
                                line_color=OLIVE, marker_color=DARK))
    line.update_layout(yaxis_title=UNIT.capitalize(), height=320, margin=dict(t=20),
                       paper_bgcolor=CREAM, plot_bgcolor=CREAM, font_color=INK)
    st.plotly_chart(line, width="stretch")


page = st.session_state.get("page", "welcome")
if page == "dashboard" and "user" not in st.session_state:
    page = "login"
{"welcome": show_welcome, "login": show_login, "dashboard": show_dashboard}[page]()
