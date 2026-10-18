"""Drought Outlook: location, crop and period selectors, the county map, the county's drought record, contributing factors
and the Drought Category Reality Check estimate with its uncertainty. The History tab holds the deeper analysis."""
from html import escape

import plotly.graph_objects as go
import streamlit as st

from droughtlens import data
from droughtlens.charts import BAR_TEXT, style
from droughtlens.data import CROP_NAMES, PERIODS, SEVERE, STATE_NAMES
from droughtlens.insights import county_profile, factors, has_yield_record
from droughtlens.reality import (below, crop_adj, get_panel, lc_first, per_acre, state_estimate, total_amount, typical_yield, YIELD_UNITS)
from droughtlens.theme import (AMBER, DROUGHT_LEVELS, FOREST, IVORY, LEVEL_COLOR, LEVEL_INK, LEVEL_MEANING, LEVEL_NAME, LEVEL_SHORT, MUTED,
                               OLIVE, RED, SILK, TINT, callout, chapter, crop_icon, html, tip)
from droughtlens.views import history
from droughtlens.views.common import context, county_select, crop_select, period_select, push, sticky, user_record


@st.cache_data(show_spinner=False)
def cost_by_county(crop):
    """Per county: the average yield change in seasons that reached D2 or worse (2000 to 2025). Counties need 3 such years."""
    p = get_panel()
    p = p[(p.crop == crop) & (p.max_drought_severity >= SEVERE)].dropna(subset=["yield_anomaly_pct"])
    g = p.groupby("fips").agg(change=("yield_anomaly_pct", "mean"), years=("yield_anomaly_pct", "size"), name=("county_name", "first"))
    return g[g.years >= 3].reset_index()


def drought_map(crop, selected):
    gj, cs, g = data.county_geojson(), data.counties(), cost_by_county(crop)
    fig = go.Figure()
    common = dict(geojson=gj, featureidkey="id", marker_line_color=IVORY, marker_line_width=0.6)
    fig.add_trace(go.Choropleth(locations=cs.fips, z=[0] * len(cs), colorscale=[[0, TINT], [1, TINT]], showscale=False, hoverinfo="skip", **common))
    fig.add_trace(go.Choropleth(
        locations=g.fips, z=g.change, zmin=-15, zmax=0, colorscale=[[0, RED], [0.5, "#D9B25F"], [1, SILK]],
        text=g.name, customdata=g.years, hovertemplate="%{text}<br>%{z:.1f}% vs normal in D2+ seasons<br>%{customdata} seasons<extra></extra>",
        colorbar=dict(title=dict(text="Yield vs normal<br>in D2+ seasons (%)", font=dict(size=12)), thickness=12, len=0.7), **common))
    fig.add_trace(go.Choropleth(locations=[selected], z=[1], zmin=0, zmax=1, colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]], showscale=False,
                                geojson=gj, featureidkey="id", marker_line_color=FOREST, marker_line_width=3.5, hoverinfo="skip"))
    fig.update_geos(fitbounds="locations", visible=False, bgcolor=IVORY)
    fig.update_layout(height=430, margin=dict(t=0, b=0, l=0, r=0), paper_bgcolor=IVORY, font=dict(family="DM Sans, sans-serif"))
    return fig


def status_table():
    """Be plain about which kind of information is which."""
    obs = data.latest_observation()
    rows = [
        ("Historical observations", "ok", f"Available. Yield, weather and weekly drought for each county, {data.FIRST_YEAR} to {data.LAST_YEAR}."),
        ("Current conditions", "na", f"Not available. The latest Drought Monitor reading in our data is {obs:%B %d, %Y}. Check droughtmonitor.unl.edu for today."),
        ("Forecast", "na", "Not available. DroughtLens has no weather or drought forecast."),
        ("Model prediction", "na", "Not available. DroughtLens does not predict future drought. It shows what past droughts cost, and whether that held up."),
    ]
    body = "".join(f"<tr><td>{n}</td><td class='{c}'>{'✓' if c == 'ok' else '–'} {t}</td></tr>" for n, c, t in rows)
    html(f"<table class='vt status'><tr><th>Kind of information</th><th>Status in DroughtLens</th></tr>{body}</table>")


def record_chart(p):
    rec = p["record"]
    fig = go.Figure()
    for lv in sorted(rec.level.unique()):
        sub = rec[rec.level == lv]
        fig.add_trace(go.Bar(x=sub.year, y=sub.weeks_d2, name=LEVEL_SHORT[int(lv)] if lv else "None", marker_color=LEVEL_COLOR[int(lv)],
                             customdata=[LEVEL_NAME[int(lv)]] * len(sub),
                             hovertemplate="%{x}: %{y} weeks in D2 or worse<br>worst level: %{customdata}<extra></extra>"))
    fig.update_layout(barmode="stack")
    style(fig, 280).update_yaxes(title="Weeks in D2 or worse").update_xaxes(dtick=2)
    return fig


def factors_table(p):
    rows = "".join(f"<tr><td><b>{escape(n)}</b></td><td>{escape(v)}</td><td>{escape(m)}</td><td class='small'>{escape(s)}</td></tr>" for n, v, m, s in factors(p))
    return f"<table class='vt'><tr><th>Factor</th><th>What we found</th><th>What it means</th><th>Source</th></tr>{rows}</table>"


def estimate_block(ctx, p, record):
    crop, state, county = ctx["crop"], ctx["state"], ctx["county"]
    chapter("Estimate", "What a drought level has cost, and how far to trust it",
            "Move the slider to the drought level you want to plan for. This is what past droughts of that level did in your state, not a forecast.",
            hint=("We take every Nebraska or Iowa county-year of your crop in 2000 to 2012 whose worst weekly drought level was the one you pick, and average how far yield sat from each county's own trend. "
                  "We then check that average against 2013 to 2025, years we never used to build it, and show you whether it held up. Nebraska fields can use the irrigated or dryland group. "
                  "The county only sets your typical yield, to turn percentages into tons or bushels."))
    c1, c2 = st.columns(2)
    with c1:
        acres = sticky(st.number_input, "acres", "Acres planted", min_value=1, max_value=100000, default=int(ctx["acres"] or 160), step=10)
    irrig = None
    if state == "NE":
        with c2:
            irrig_choice = sticky(st.radio, "irrig_pick", "How is this field watered?", ["Irrigated", "Rain only (dryland)"], horizontal=True,
                                  help="About the same drought level cost Nebraska dryland counties far more than irrigated counties.")
        irrig = {"Irrigated": "mostly irrigated", "Rain only (dryland)": "mostly dryland"}[irrig_choice]
        if ctx["field"] and ctx["field"].get("irrigation"):
            irrig = ctx["field"]["irrigation"]
            st.caption(f"Using the water setting saved for {ctx['field']['name']}.")
    level = sticky(st.select_slider, "level", "Worst drought level this season", options=[lv for lv, *_ in DROUGHT_LEVELS], default=4, format_func=LEVEL_NAME.get)
    html("<div class='legend'>" + "".join(
        f"<div class='{'on' if lv == level else ''}' style='background:{c};color:{ink}'>{s}</div>"
        for lv, _, s, c, ink, _ in DROUGHT_LEVELS) + "</div>")
    st.markdown(f"**{LEVEL_NAME[level]}.** {LEVEL_MEANING[level]}")

    row, css, text = state_estimate(crop, state, level, irrig)
    typical = typical_yield(get_panel(), state, county, crop) if has_yield_record(p) else float("nan")
    if row is None:
        st.info(f"We have no past {CROP_NAMES[crop].lower()} years at this drought level for {STATE_NAMES[state]}. Try a nearby level.")
        return
    change = row.train_mean
    loss = -change
    if abs(loss) < 0.5:
        color, tone = OLIVE, "Yield about normal at this level."
    elif loss >= 12:
        color, tone = RED, "Large expected loss. Worth planning for now."
    elif loss >= 4:
        color, tone = AMBER, "Some expected loss."
    elif loss > 0:
        color, tone = "#D9B25F", "A small expected loss."
    else:
        color, tone = OLIVE, "Past years at this level did not lose yield on average."
    big = "About normal" if abs(loss) < 0.5 else f"{abs(loss):.0f}% {'lower' if loss > 0 else 'higher'} yield"
    water = {"mostly irrigated": " · irrigated counties", "mostly dryland": " · dryland counties"}.get(irrig, "")
    html(f"""<div class="result" style="--c:{color}"><div class="head">{crop_icon(crop, 64)}<div>
        <div class="big">{big}</div><div class="sub">{CROP_NAMES[crop]} in {STATE_NAMES[state]}{water} at {lc_first(LEVEL_NAME[level])} · {tone}</div></div></div></div>""")
    if typical == typical:
        u = YIELD_UNITS[crop]
        expected = typical * (1 + change / 100)
        m1, m2, m3 = st.columns(3)
        m1.metric("Typical yield", per_acre(crop, typical),
                  help=f"{county}'s recent trend yield in a normal year, in {u['per_acre']}." + (" Corn is shown in tons: one bushel weighs 56 pounds and one ton is 2,000 pounds." if crop == "CORN" else ""))
        m2.metric("Expected yield", per_acre(crop, expected), per_acre(crop, expected - typical, signed=True))
        m3.metric(f"{u['total'].capitalize()} at risk on {acres:,} acres", f"{max((typical - expected) * acres, 0) * u['factor']:,.0f}")
    else:
        st.info(f"We have no reported {CROP_NAMES[crop].lower()} yield for {county}, so we can show the percentage but not tons or bushels.")
    html(f"<div class='callout finding'><span class='tagline'>Can you trust it?</span><span class='{css}'>{text}</span></div>")
    st.markdown(f"<span class='small'>Based on <b>{row.train_n}</b> county-years in {STATE_NAMES[state]}{water} from 2000 to 2012. "
                "An average of past years, not a forecast.</span>", unsafe_allow_html=True)


def show():
    record, store_error = user_record()
    ss = st.session_state
    html("<div class='eyebrow'>Drought Outlook</div>")
    tab_outlook, tab_history = st.tabs(["Outlook", "History"])

    with tab_outlook:
        fields = record["fields"]
        cols = st.columns([1.4, 1.3, 1.2, 1.5])
        with cols[0]:
            if fields:
                ids = [None] + [f["id"] for f in fields]
                label = {f["id"]: f"{f['name']}" for f in fields}
                pick = st.selectbox("Saved field", ids, format_func=lambda i: "Choose a county instead" if i is None else label[i],
                                    index=ids.index(ss.get("active_field")) if ss.get("active_field") in ids else 0, key="outlook_field")
                if pick != ss.get("active_field"):
                    ss.active_field = pick
                    if pick:
                        f = next(f for f in fields if f["id"] == pick)
                        push(fips=f["fips"], state=data.counties().set_index("fips").state_alpha[f["fips"]], crop=f["crops"][0])
                        st.rerun()
            else:
                st.caption("No saved field yet. Add one under My Fields.")
        with cols[1]:
            county_select()
        with cols[2]:
            crop_select()
        with cols[3]:
            period_select()
        if store_error:
            st.warning(store_error)

        ctx = context(record)
        crop, fips = ctx["crop"], ctx["fips"]
        p = county_profile(fips, crop, ss.period)

        chapter("Where drought has hurt", f"{p['county']}, {STATE_NAMES[p['state']]}",
                "Historical drought cost by county. Grey counties have too few drought years with a reported yield.",
                hint=(f"Each colored county shows the average yield change for {CROP_NAMES[crop].lower()} in seasons when its worst weekly drought level reached D2 (severe) or worse, 2000 to 2025, "
                      "measured against that county's own trend. Counties need at least three such seasons. This is history, not a prediction."))
        status_table()
        left, right = st.columns([1.7, 1], gap="large")
        with left:
            st.plotly_chart(drought_map(crop, fips), width="stretch", config={"displayModeBar": False})
        with right:
            if p["years"]:
                st.metric(f"Seasons at D2 or worse ({PERIODS[ss.period][1]})", f"{p['d2_years']} of {p['years']}",
                          help="Historical frequency in this county for the period you chose. It describes the past; it is not a probability for next season.")
                st.metric("Longest spell", f"{p['worst_year']}", f"{p['worst_weeks']} weeks in D2 or worse", delta_color="off")
            if p["dry_change"] is not None:
                st.metric(f"{CROP_NAMES[crop]} yield in those seasons", below(p["dry_change"], 1),
                          help=f"Average over the {p['dry_years']} seasons this county reached D2 or worse, against its own trend.")
            elif not has_yield_record(p):
                st.info(f"We have no reported {CROP_NAMES[crop].lower()} yields for {p['county']}. County yield figures are unavailable here, but its drought and weather record is shown.")
            if p["area"]:
                st.caption(f"NASS: {p['area'][1]:,.0f} acres of {CROP_NAMES[crop].lower()} harvested in {p['area'][0]}.")

        st.markdown(f"### Weeks in D2 or worse, by year {tip('For each year, the number of weeks in the planning period when at least 1% of the county was in D2 (severe) drought or worse. Bar colour is the worst weekly level that year. Years with no bar did not reach D2.')}",
                    unsafe_allow_html=True)
        st.plotly_chart(record_chart(p), width="stretch", config={"displayModeBar": False})

        chapter("Why", "Key contributing factors", "What we can see in the records for this county, and where each fact comes from.",
                hint="Each factor is read from a file in our data folder for the county and crop you chose. None is a model output. Soil water storage is context only: in Iowa the data shows a very weak link to drought-year yield.")
        html(factors_table(p))

        estimate_block(ctx, p, record)

    with tab_history:
        history.show(record)
