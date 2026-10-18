"""Overview: the landing page, and the corn and soybean intelligence sections."""
import streamlit as st

from droughtlens import data
from droughtlens.reality import analysis, below, cell, crop_adj, get_panel, heat_thresholds, loss_phrase, peak_share
from droughtlens.theme import DROUGHT_LEVELS, callout, chapter, crop_icon, html, photo
from droughtlens.views.common import goto, signed_in

SEASON_TEXT = {"CORN": "May 1 to September 30", "SOYBEANS": "May 1 to October 31"}


def _hardest_years(crop):
    """The year each state's reported yields fell furthest below trend, and by how much."""
    p = get_panel()
    p = p[p.crop == crop].dropna(subset=["yield_anomaly_pct"])
    out = {}
    for state in data.STATE_NAMES:
        by_year = p[p.state_alpha == state].groupby("year").yield_anomaly_pct.mean()
        out[state] = (int(by_year.idxmin()), float(by_year.min()))
    return out


def _share_in_d2(crop):
    p = get_panel()
    p = p[p.crop == crop]
    return {s: float((p[p.state_alpha == s].max_drought_severity >= data.SEVERE).mean()) for s in data.STATE_NAMES}


def crop_section(crop, photo_name, photo_first):
    a = analysis(crop)
    name = data.CROP_NAMES[crop]
    ia, ne = cell(a["check"], "IA", 4), cell(a["check"], "NE", 4)
    share, (neg, sharp) = peak_share(a), heat_thresholds(crop)
    dry, irr = cell(a["irr_check"], "NE", 4, "mostly dryland"), cell(a["irr_check"], "NE", 4, "mostly irrigated")
    hardest, in_d2 = _hardest_years(crop), _share_in_d2(crop)

    pic, txt = st.columns([1, 1.5], gap="large")
    cols = (pic, txt) if photo_first else (txt, pic)
    with cols[0 if photo_first else 1]:
        html(f"<div class='photo-band' style='height:340px;margin-top:.2rem;background-image:url(\"{photo(photo_name)}\")'></div>")
    with cols[1 if photo_first else 0]:
        html(f"<div class='h2row'>{crop_icon(crop, 44)}<h3 style='margin:.2rem 0'>{name} intelligence</h3></div>")
        callout(f"<span class='tagline'>Growing season in our data</span>{SEASON_TEXT[crop]}. Weather and drought figures for {crop_adj(crop)} are measured over this window.", "finding")
        callout("<span class='tagline'>Drought sensitivity</span>"
                f"At extreme drought (D3), {crop_adj(crop)} yields in 2000 to 2012 fell {abs(ia.train_mean):.0f}% below trend in Iowa and {abs(ne.train_mean):.0f}% in Nebraska. "
                f"{share:.0%} of D3 seasons had severe drought reach the county in July or August. Yields turn negative at {neg} days of 35 °C (95 °F) or hotter and fall sharply at {sharp}.", "finding")
        callout("<span class='tagline'>Historical drought context</span>"
                f"Since 2000, {in_d2['IA']:.0%} of Iowa and {in_d2['NE']:.0%} of Nebraska county-seasons reached D2 or worse. "
                f"The hardest year for {crop_adj(crop)} was {hardest['IA'][0]} in Iowa ({below(hardest['IA'][1], 1)}) and {hardest['NE'][0]} in Nebraska ({below(hardest['NE'][1], 1)}).", "finding")
        callout("<span class='tagline'>What the data supports considering</span>"
                f"In Nebraska, mostly dryland counties had {loss_phrase(dry.train_mean)} at D3 and mostly irrigated counties {loss_phrase(irr.train_mean)}. "
                "Iowa is rain-fed. <b>General guidance:</b> scout often in July and August, and talk with your county extension office.", "guidance")


def water_section():
    """Nebraska irrigated versus dryland: the biggest single reason the same drought label costs different amounts."""
    rows = {}
    for crop in data.CROPS:
        a = analysis(crop)
        rows[crop] = (cell(a["irr_check"], "NE", 4, "mostly dryland"), cell(a["irr_check"], "NE", 4, "mostly irrigated"))
    pic, txt = st.columns([1, 1.5], gap="large")
    with pic:
        html(f"<div class='photo-band' style='height:380px;margin-top:.2rem;background-image:url(\"{photo('irrigation.jpg')}\")'></div>"
             "<div class='small'>Monitoring a center-pivot irrigation system. USDA photo, public domain.</div>")
    with txt:
        html("<h3 style='margin:.2rem 0'>Water changes the answer</h3>")
        lines = " ".join(f"{data.CROP_NAMES[c]}: {loss_phrase(d.train_mean)} on dryland counties, {loss_phrase(i.train_mean)} on irrigated counties." for c, (d, i) in rows.items())
        callout(f"<span class='tagline'>Nebraska at extreme drought (D3), 2000 to 2012</span>{lines}", "finding")
        callout("<span class='tagline'>How to read this</span>Nebraska counties are grouped by whether most of their cropland is irrigated, using NASS irrigation records from 2000 to 2018. "
                "Iowa is rain-fed, so it has no such split.", "finding")
        callout("<span class='tagline'>General guidance</span>If you irrigate, check your system early in the season. DroughtLens does not advise irrigation volumes or schedules, because the data cannot support them.", "guidance")


def show():
    ia_ne = len(data.counties())
    html(f"""
    <div class="hero">
      <div class="copy">
        <div class="eyebrow">Drought intelligence for the Midwest</div>
        <h1>See Drought Coming. Plan Ahead.</h1>
        <p>DroughtLens helps corn and soybean farmers in Nebraska and Iowa understand drought risk, explore historical weather patterns, and prepare smarter plans for their fields.</p>
        <p style="font-size:.98rem">We cover Nebraska and Iowa only, {ia_ne} counties, because that is where our records on corn and soybean yield and weekly drought are deepest.</p>
      </div>
      <div class="pic" style="background-image:url('{photo('aerial.jpg')}')">
        <div class="caption"><b>Historical records, 2000 to 2025.</b> Latest drought reading in our data: {data.latest_observation():%B %d, %Y}.
        Iowa farmland, USDA NRCS photo.</div>
      </div>
    </div>
    """)
    st.write("")
    c1, c2, _ = st.columns([1.3, 1.3, 2])
    c1.button("Explore My Drought Outlook", key="hero_outlook", type="primary", on_click=goto, args=("outlook" if signed_in() else "login",),
              kwargs={"next_page": "outlook"}, width="stretch")
    c2.button("Ask the Agricultural Advisor", key="hero_advisor", on_click=goto, args=("advisor" if signed_in() else "login",),
              kwargs={"next_page": "advisor"}, width="stretch")

    chapter("What DroughtLens is, and is not", lead="DroughtLens looks back so you can look ahead. It does not forecast.")
    html(f"""
    <div class="steps">
      <div class="step"><div class="k">1</div><b>What past droughts cost</b>For each Drought Monitor level, we measured how far corn and soybean yields fell below each county's own trend, and checked whether that held up in later years.</div>
      <div class="step"><div class="k">2</div><b>Your county's own record</b>How often drought reached your county, when in the season, and what it did to yield there, from {data.FIRST_YEAR} to {data.LAST_YEAR}.</div>
      <div class="step"><div class="k">3</div><b>A plan you can edit</b>A preparedness plan that keeps what the data says apart from general guidance, with no costly steps recommended.</div>
    </div>
    """)

    chapter("Every Crop Has Different Needs.", lead="The same drought label does not cost every crop, or every state, the same. These figures are read straight from our records.")
    with st.spinner("Loading the crop records..."):
        crop_section("CORN", "corn.jpg", photo_first=True)
        st.write("")
        crop_section("SOYBEANS", "soybeans.jpg", photo_first=False)
        st.write("")
        water_section()

    chapter("Reading a drought level", lead="The U.S. Drought Monitor rates every county each week. DroughtLens uses the worst weekly level reached during the crop season.",
            hint="The levels run from none through D0 (abnormally dry) to D4 (exceptional drought). A level counts when at least 1% of the county reached it that week.")
    html("<div class='legend'>" + "".join(f"<div style='background:{c};color:{ink}'>{short}</div>" for _, _, short, c, ink, _ in DROUGHT_LEVELS) + "</div>")
    html("<table class='vt'>" + "".join(f"<tr><td><b>{name}</b></td><td>{meaning}</td></tr>" for _, name, _, _, _, meaning in DROUGHT_LEVELS) + "</table>")
