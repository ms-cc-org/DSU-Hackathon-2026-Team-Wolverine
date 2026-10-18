"""My Fields: onboarding for a field, and the personal dashboard that answers three questions:
what drought conditions may affect my farm, why does the system estimate this, and what should I do next."""
import numpy as np
import plotly.graph_objects as go
import streamlit as st

from droughtlens import data, farm
from droughtlens.charts import style
from droughtlens.data import CROP_NAMES, CROPS, PERIODS, STATE_NAMES
from droughtlens.farm import IRRIGATION, IRRIGATION_LABEL, STAGES
from droughtlens.insights import county_profile, has_yield_record
from droughtlens.places import SUPPORT_MESSAGE, resolve_location
from droughtlens.reality import below, get_panel, lc_first, loss_phrase, per_acre, state_estimate, total_amount, typical_yield, YIELD_UNITS
from droughtlens.theme import AMBER, FOREST, LEVEL_NAME, OLIVE, RED, callout, chapter, html, tip
from droughtlens.views.common import county_select, goto, push, user_record
from droughtlens.views.outlook import factors_table, record_chart, status_table


def _locate():
    """Callback for the 'type a county' box: set the county if it is supported, otherwise say so. Never substitutes."""
    ss = st.session_state
    status, fips, msg = resolve_location(ss.get("loc_text", ""))
    ss.loc_result = (status, msg)
    if status == "ok":
        push(fips=fips, state=data.counties().set_index("fips").state_alpha[fips])


def onboarding(record):
    ss = st.session_state
    chapter("Set up", "Add a field", "A few details help us pick the right county record. Only the name, county and crop are required.")
    st.text_input("Find your county by name (optional)", key="loc_text", on_change=_locate, placeholder="For example: Polk County, Iowa",
                  help="DroughtLens covers Nebraska and Iowa counties only. Press Enter to look it up.")
    status, msg = ss.get("loc_result", ("empty", ""))
    if status == "ok":
        st.success(f"Using {msg}.")
    elif status == "ambiguous":
        st.warning(msg)
    elif status == "unsupported":
        st.error(msg)
        st.caption("Type a county and state, for example “Hall County, Nebraska”, or choose from the lists below.")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**State:** {STATE_NAMES[ss.state]} (change it in the bar above)")
    with c2:
        fips = county_select()
    name = st.text_input("Farm or field name", placeholder="For example: North 80", key="new_field_name")
    crops = st.multiselect("Crops on this field", CROPS, default=[ss.crop], format_func=CROP_NAMES.get, key="new_field_crops")
    c3, c4 = st.columns(2)
    acres = c3.number_input("Acres (optional)", min_value=1, max_value=100000, value=None, step=10, key="new_field_acres")
    planting = c4.date_input("Planting date (optional)", value=None, key="new_field_planting")
    stage = st.selectbox("Growing stage (optional)", ["Not sure"] + list(STAGES), key="new_field_stage",
                         help="We use the stage to pick which part of the season to look at: early (May to June), peak (July to August) or late.")
    state = data.counties().set_index("fips").state_alpha[fips]
    if state == "NE":
        irr_label = st.radio("Irrigation (optional)", list(IRRIGATION), horizontal=True, index=2, key="new_field_irr",
                             help="Nebraska dryland counties lost far more than irrigated counties at extreme drought.")
        irrigation = IRRIGATION[irr_label]
    else:
        st.caption("Iowa is rain-fed. NASS publishes no irrigation series for Iowa, so there is nothing to choose here.")
        irrigation = None

    if st.button("Save field", type="primary", key="save_field"):
        if not name.strip():
            st.error("Give the field a name so you can find it later.")
        elif not crops:
            st.error("Choose at least one crop.")
        elif any(f["name"].lower() == name.strip().lower() for f in record["fields"]):
            st.error("You already have a field with that name. Choose a different name.")
        else:
            field = farm.new_field(name, fips, crops, int(acres) if acres else None, planting, None if stage == "Not sure" else stage, irrigation)
            record["fields"].append(field)
            try:
                farm.save_user(ss.user, record)
            except farm.StoreError as exc:
                st.error(str(exc))
                return
            ss.active_field = field["id"]
            push(crop=crops[0])
            ss.field_saved = field["name"]
            st.rerun()


def _precip_chart(season, fips):
    s = season.dropna(subset=["precip_mm"])
    fig = go.Figure()
    fig.add_trace(go.Bar(x=s.year, y=s.precip_mm, marker_color=[RED if lv >= data.SEVERE else OLIVE for lv in s.level], name="Season rain",
                         customdata=[LEVEL_NAME[int(lv)] for lv in s.level], hovertemplate="%{x}: %{y:.0f} mm<br>worst level: %{customdata}<extra></extra>"))
    fig.add_hline(y=s.precip_mm.mean(), line_dash="dash", line_color="#292D29", annotation_text="county average", annotation_position="top left")
    style(fig, 300, legend=False).update_yaxes(title="Growing-season rain (mm)").update_xaxes(dtick=2)
    return fig


def _temp_chart(season):
    s = season.dropna(subset=["tavg_c"])
    slope, intercept = np.polyfit(s.year, s.tavg_c, 1)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=s.year, y=s.tavg_c, mode="lines+markers", line=dict(color=AMBER, width=2), name="Season average"))
    fig.add_trace(go.Scatter(x=s.year, y=intercept + slope * s.year, mode="lines", line=dict(color="#292D29", dash="dash"), name="Trend"))
    style(fig, 300).update_yaxes(title="Average temperature (°C)").update_xaxes(dtick=2)
    return fig


def field_dashboard(field):
    ss = st.session_state
    fips = field["fips"]
    state = data.counties().set_index("fips").state_alpha[fips]
    county = data.county_name(fips)
    crop = st.radio("Crop to look at", field["crops"], format_func=CROP_NAMES.get, horizontal=True, key="field_crop") if len(field["crops"]) > 1 else field["crops"][0]
    if ss.crop != crop:
        push(crop=crop)
    period = STAGES.get(field.get("stage"), "full") if field.get("stage") else "full"
    p = county_profile(fips, crop, period)
    season = data.season_rows(fips, crop)
    crop_name = CROP_NAMES[crop].lower()

    bits = [f"{county}, {STATE_NAMES[state]}", ", ".join(CROP_NAMES[c] for c in field["crops"])]
    if field.get("acres"):
        bits.append(f"{field['acres']:,} acres")
    if field.get("stage"):
        bits.append(f"stage: {field['stage'].lower()}")
    if field.get("irrigation"):
        bits.append(IRRIGATION_LABEL[field["irrigation"]].lower())
    html(f"<div class='sec'><div class='eyebrow'>Your field</div><h2>{field['name']}</h2><p class='lead'>{' · '.join(bits)}</p></div>")

    # 1. What may affect my farm
    chapter("1", "What drought conditions may affect my farm?", f"Your county's record for the {PERIODS[period][0].lower()} ({PERIODS[period][1]}), which matches the growing stage you entered."
            if field.get("stage") else "Your county's record for the whole growing season. Add a growing stage to look at one part of the season.",
            hint="This is the county's own history from the weekly U.S. Drought Monitor, 2000 to 2025. It tells you how often drought has reached your county, not whether it will this year.")
    status_table()
    c1, c2, c3 = st.columns(3)
    c1.metric("Seasons at D2 or worse", f"{p['d2_years']} of {p['years']}", help="Historical frequency for this county and period. Not a probability for next season.")
    c2.metric("Longest spell", f"{p['worst_year']}", f"{p['worst_weeks']} weeks in D2 or worse", delta_color="off")
    if p["dry_change"] is not None:
        c3.metric(f"{CROP_NAMES[crop]} in those seasons", below(p["dry_change"], 1), help=f"Average over {p['dry_years']} seasons, against this county's own trend.")
    elif not has_yield_record(p):
        c3.info(f"No reported {crop_name} yields for {county}.")
    st.plotly_chart(record_chart(p), width="stretch", config={"displayModeBar": False})

    # 2. Why this estimate
    chapter("2", "Why does the system estimate this level of risk?", "What we can see in the records, and what past droughts cost.",
            hint="The estimate is the Drought Category Reality Check: the average yield change in 2000 to 2012 for your state and crop at each drought level, checked against 2013 to 2025. Nothing here is a forecast.")
    html(factors_table(p))
    irrig = field.get("irrigation") if state == "NE" else None
    typical = typical_yield(get_panel(), state, county, crop) if has_yield_record(p) else float("nan")
    rows_html = ""
    for lv in (3, 4):
        row, css, text = state_estimate(crop, state, lv, irrig)
        if row is None:
            continue
        at_risk = ""
        if typical == typical and field.get("acres"):
            lost = max(typical * -row.train_mean / 100 * field["acres"], 0)
            at_risk = f" About {total_amount(crop, lost)} on {field['acres']:,} acres."
        rows_html += (f"<tr><td><b>{LEVEL_NAME[lv]}</b></td><td>{below(row.train_mean, 1)}{at_risk}</td><td class='{css}'>{text}</td></tr>")
    if rows_html:
        html(f"<table class='vt'><tr><th>If your county reached…</th><th>Past droughts of that level (2000–2012)</th><th>Did it hold up on 2013–2025?</th></tr>{rows_html}</table>")
    else:
        st.info(f"We have no past {crop_name} years at severe or extreme drought for {STATE_NAMES[state]} to estimate from.")
    st.markdown(f"### Rain each season {tip('Growing-season rain for each year. Red bars are seasons when the county reached D2 or worse. The dashed line is the county average.')}", unsafe_allow_html=True)
    st.plotly_chart(_precip_chart(season, fips), width="stretch", config={"displayModeBar": False})
    st.markdown(f"### Temperature trend {tip('Average temperature over the growing season for each year, with a straight-line trend. Twenty-six years is a rough guide, not a forecast.')}", unsafe_allow_html=True)
    st.plotly_chart(_temp_chart(season), width="stretch", config={"displayModeBar": False})
    if p["soil"]:
        s = p["soil"]
        st.caption(f"Soil: {county} can hold about {s['aws_mm']:.0f} mm of plant-available water in the top metre (Nebraska and Iowa median {s['aws_median_mm']:.0f} mm). "
                   "Measured soil moisture is not in our data.")

    # 3. What next
    chapter("3", "What should I do next?", "General steps that fit a county with this record. They are common practice, not predictions.")
    callout("<span class='tagline'>General guidance</span>"
            "1. Check where your county stands on the U.S. Drought Monitor this week.<br>"
            "2. Walk the field and check soil moisture at several spots.<br>"
            "3. Confirm your crop insurance coverage and reporting dates with your agent.<br>"
            "4. Talk with your county extension office about what you are seeing.", "guidance")
    b1, b2, _ = st.columns([1.3, 1.3, 2])
    b1.button("Open my farm plan", key="to_plan", type="primary", on_click=goto, args=("plan",), width="stretch")
    b2.button("Ask the Advisor", key="to_advisor", on_click=goto, args=("advisor",), width="stretch")


def show():
    ss = st.session_state
    record, store_error = user_record()
    html("<div class='eyebrow'>My Fields</div>")
    if store_error:
        st.error(store_error)
    if ss.get("field_saved"):
        st.success(f"Saved “{ss.pop('field_saved')}”. Here is its dashboard.")

    fields = record["fields"]
    if not fields:
        html("<h2 style='margin-top:.2rem'>Let's set up your first field</h2>")
        st.info("You have no saved fields yet. Add one to see its drought record and to build a plan.")
        onboarding(record)
        return

    ids = [f["id"] for f in fields]
    if ss.get("active_field") not in ids:
        ss.active_field = ids[0]
    c1, c2, c3 = st.columns([2, 1, 1], vertical_alignment="bottom")
    with c1:
        pick = st.selectbox("Field", ids, format_func=lambda i: farm.field_label(next(f for f in fields if f["id"] == i)), index=ids.index(ss.active_field), key="field_pick")
        ss.active_field = pick
    field = next(f for f in fields if f["id"] == ss.active_field)
    with c3:
        if st.button("Remove this field", key="remove_field", width="stretch"):
            record["fields"] = [f for f in fields if f["id"] != field["id"]]
            record["plans"] = [p for p in record["plans"] if p["field_id"] != field["id"]]
            try:
                farm.save_user(ss.user, record)
            except farm.StoreError as exc:
                st.error(str(exc))
            else:
                ss.pop("active_field", None)
                st.rerun()
    if ss.get("synced_field") != field["id"]:      # move the county and state selectors to this field once, when it is chosen
        push(fips=field["fips"], state=data.counties().set_index("fips").state_alpha[field["fips"]])
        ss.synced_field = field["id"]
        st.rerun()
    field_dashboard(field)
    with st.expander("Add another field"):
        onboarding(record)
