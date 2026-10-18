import plotly.graph_objects as go
import streamlit as st

from src.data_loader import load_master
from wolverine.contracts import CROPS, STATES, LEVEL_LABELS

st.set_page_config(page_title="Drought Yield Estimator", page_icon=":ear_of_corn:", layout="centered")

# Login
# Demo accounts only: replace with a real user store before sharing the app outside the team.
DEMO_USERS = {"farmer": "wolverine", "demo": "demo"}

STATE_NAMES = {"IA": "Iowa", "NE": "Nebraska"}
CROP_NAMES = {"CORN": "Corn", "SOYBEANS": "Soybeans"}
UNIT = "bushels per acre"

# Plain-language drought levels (U.S. Drought Monitor D0-D4), keyed by the dataset's 0..5 scale.
DROUGHT_CHOICES = {
    "No drought": 0,
    "Abnormally dry (D0)": 1,
    "Moderate drought (D1)": 2,
    "Severe drought (D2)": 3,
    "Extreme drought (D3)": 4,
    "Exceptional drought (D4)": 5,
}

MIN_COUNTY_N = 5   # fewer matching county-years than this and we use the whole state instead

st.markdown(
    """
    <style>
    html, body, [class*="css"] { font-size: 19px; }
    .big-number { font-size: 3.4rem; font-weight: 700; line-height: 1.1; }
    .card { border-radius: 12px; padding: 1.2rem 1.4rem; margin: 0.6rem 0; }
    .card-low  { background: #e8f5e9; color: #1b5e20; }
    .card-mid  { background: #fff8e1; color: #7a5200; }
    .card-high { background: #ffebee; color: #8e1b1b; }
    </style>
    """,
    unsafe_allow_html=True,
)


def show_login():
    st.title(":ear_of_corn: Drought Yield Estimator")
    st.write("See how drought could affect your corn and soybean yields, in plain numbers.")
    with st.form("login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in", width="stretch", type="primary")
    if submitted:
        if DEMO_USERS.get(username.strip().lower()) == password:
            st.session_state.user = username.strip().lower()
            st.rerun()
        else:
            st.error("That username or password isn't right. Please try again.")
    st.caption("Team Wolverine demo: log in with username **demo** and password **demo**.")


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


def show_dashboard():
    df = get_data()

    top = st.columns([4, 1])
    top[0].title(":ear_of_corn: Drought Yield Estimator")
    if top[1].button("Log out"):
        del st.session_state["user"]
        st.rerun()

    st.subheader("1. Tell us about your farm")
    c1, c2 = st.columns(2)
    state = c1.selectbox("State", STATES, format_func=STATE_NAMES.get)
    counties = sorted(df[df["state_alpha"] == state]["county_name"].unique())
    county = c2.selectbox("County", counties, format_func=lambda c: c.replace(" County", ""))
    c3, c4 = st.columns(2)
    crop = c3.selectbox("Crop", CROPS, format_func=CROP_NAMES.get)
    acres = c4.number_input("Acres planted", min_value=1, value=160, step=10)

    st.subheader("2. How dry could it get?")
    choice = st.select_slider("Worst drought level this season", options=list(DROUGHT_CHOICES), value="Severe drought (D2)")
    level = DROUGHT_CHOICES[choice]

    # Results
    st.subheader("3. What to expect")
    anomaly, n, basis = estimate(df, state, county, crop, level)
    if anomaly is None:
        st.info("We don't have enough past years at this drought level to give an estimate.")
        return

    history = df[(df["state_alpha"] == state) & (df["county_name"] == county) & (df["crop"] == crop)].sort_values("year")
    typical = history[history["year"] >= history["year"].max() - 9]["yield_per_acre"].mean()
    expected = typical * (1 + anomaly / 100)
    lost_per_acre = typical - expected
    total_lost = lost_per_acre * acres

    loss_pct = -anomaly
    if loss_pct >= 15:
        style, verdict = "card-high", "Large expected loss. Worth planning for."
    elif loss_pct >= 5:
        style, verdict = "card-mid", "Some expected loss."
    else:
        style, verdict = "card-low", "Little to no loss expected historically."

    if loss_pct > 0:
        headline = f"<div class='big-number'>{loss_pct:.0f}% lower yield</div>"
    else:
        headline = f"<div class='big-number'>{abs(loss_pct):.0f}% higher yield</div>"
    st.markdown(
        f"<div class='card {style}'>{headline}<div>{verdict}</div></div>",
        unsafe_allow_html=True,
    )

    m1, m2, m3 = st.columns(3)
    m1.metric("Typical yield", f"{typical:.0f}", help=f"Your county's average over its last 10 reported years, in {UNIT}.")
    m2.metric("Expected yield", f"{expected:.0f}", f"{expected - typical:+.0f}")
    m3.metric(f"Bushels at risk ({acres} ac)", f"{max(total_lost, 0):,.0f}")

    st.caption(
        f"Based on {n} past county-years in {basis} that reached '{choice}' during the season. "
        "Yields are in bushels per acre. This is a historical average, not a guarantee."
    )

    # Charts
    st.subheader("How loss grows as drought gets worse")
    levels, losses = [], []
    for name, lv in DROUGHT_CHOICES.items():
        a, _, _ = estimate(df, state, county, crop, lv)
        if a is not None:
            levels.append(name.split(" (")[0])
            losses.append(-a)
    fig = go.Figure(go.Bar(
        x=levels, y=losses,
        marker_color=["#c62828" if name.startswith(choice.split(" (")[0]) else "#bdbdbd" for name in levels],
        text=[f"{v:.0f}%" for v in losses], textposition="outside",
    ))
    fig.update_layout(yaxis_title="Average yield loss (%)", xaxis_title=None, height=360, margin=dict(t=20))
    st.plotly_chart(fig, width="stretch")

    st.subheader(f"{CROP_NAMES[crop]} yield in {county.replace(' County', '')} County over the years")
    line = go.Figure(go.Scatter(x=history["year"], y=history["yield_per_acre"], mode="lines+markers", line_color="#2e7d32"))
    line.update_layout(yaxis_title=UNIT.capitalize(), xaxis_title=None, height=320, margin=dict(t=20))
    st.plotly_chart(line, width="stretch")


if "user" not in st.session_state:
    show_login()
else:
    show_dashboard()
