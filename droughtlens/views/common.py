"""Shared page pieces: session state, navigation bar, sticky selectors, footer."""
import streamlit as st

from droughtlens import data, farm, logo
from droughtlens.data import CROP_NAMES, CROPS, PERIODS, STATE_NAMES
from droughtlens.theme import html

# Demo accounts only: replace with a real user store before sharing outside the team.
DEMO_USERS = {"farmer": "wolverine", "demo": "demo"}
NAV = [("overview", "Overview"), ("outlook", "Drought Outlook"), ("fields", "My Fields"), ("plan", "Farm Plan")]
GATED = {"outlook", "fields", "plan", "advisor"}


def push(**values):
    """Change remembered values from code (not from the widget itself): the widgets pick them up on the next run."""
    for key, value in values.items():
        st.session_state[key] = value
        st.session_state["_push_" + key] = True


def goto(page, **state):
    """Button callback: go to a page, optionally setting session values first."""
    push(**state)
    st.session_state.page = page


def init_state():
    ss = st.session_state
    ss.setdefault("page", "overview")
    ss.setdefault("state", "NE")
    ss.setdefault("crop", "CORN")
    ss.setdefault("period", "peak")
    ss.setdefault("chat", [])
    ss.setdefault("trust_section", "Data sources")


def signed_in():
    return bool(st.session_state.get("user"))


def sticky(widget, key, label, options=None, default=None, **kwargs):
    """A widget whose value survives page changes (Streamlit forgets widgets that are not drawn on a page).

    `options` is given for selectbox and radio, left out for inputs and sliders. `default` is the starting value;
    it is set through session state, because Streamlit warns when a widget gets both a value argument and a stored value.
    """
    ss = st.session_state
    wkey = "w_" + key
    # Restore the remembered value when the widget was not drawn on the last run (another page) or when code changed it on purpose.
    # A change the farmer makes in the widget is saved by the callback below, so it is never overwritten here.
    if ss.pop("_push_" + key, False) or (wkey not in ss and key in ss):
        if key in ss and (options is None or ss[key] in list(options)):
            ss[wkey] = ss[key]
    if options is not None and wkey in ss and ss[wkey] not in list(options):
        del ss[wkey]            # e.g. the county belonged to the other state
    if wkey not in ss and default is not None:
        ss[wkey] = default
    kwargs.update(on_change=_remember, args=(key,))
    value = widget(label, key=wkey, **kwargs) if options is None else widget(label, options, key=wkey, **kwargs)
    ss[key] = value
    return value


def _remember(key):
    st.session_state[key] = st.session_state["w_" + key]


def county_options(state):
    cs = data.counties()
    return list(cs[cs.state_alpha == state].fips)


def county_select(label="County", **kwargs):
    """County picker for the selected state, remembered across pages. Returns the FIPS code."""
    names = data.counties().set_index("fips").county_name
    return sticky(st.selectbox, "fips", label, county_options(st.session_state.state), format_func=lambda f: names[f].replace(" County", ""), **kwargs)


def crop_select(label="Crop", **kwargs):
    return sticky(st.radio, "crop", label, CROPS, format_func=CROP_NAMES.get, horizontal=True, **kwargs)


def period_select(label="Planning period", **kwargs):
    return sticky(st.selectbox, "period", label, list(PERIODS), format_func=lambda k: f"{PERIODS[k][0]} ({PERIODS[k][1]})", **kwargs)


def user_record():
    """The signed-in farmer's saved fields and plans, or an empty record with a flag if the store could not be read."""
    try:
        return farm.load_user(st.session_state.user), None
    except farm.StoreError as exc:
        return {"fields": [], "plans": []}, str(exc)


def active_field(record):
    """The saved field the farmer has chosen, if any."""
    fid = st.session_state.get("active_field")
    return next((f for f in record["fields"] if f["id"] == fid), None)


def context(record=None):
    """What the Advisor and the plan builder know about the current selection.

    The selected county always wins. A saved field applies only while it is in that county.
    """
    ss = st.session_state
    fips = ss.get("fips") or county_options(ss.state)[0]
    field = active_field(record) if record else None
    if field and field["fips"] != fips:
        field = None
    return {"state": data.counties().set_index("fips").state_alpha[fips], "fips": fips, "county": data.county_name(fips),
            "crop": ss.crop, "period": ss.period, "field": field, "acres": field.get("acres") if field else None, "user": ss.get("user")}


def logout():
    for k in ("user", "active_field", "chat"):
        st.session_state.pop(k, None)
    st.session_state.page = "overview"


def navbar():
    ss = st.session_state
    cols = st.columns([2.0, 4.6, 1.5, 1.5, 1.2], vertical_alignment="center")
    with cols[0]:
        html(f"<div class='navbar'>{logo.compact(height=38)}</div>")
    with cols[1]:
        for col, (key, label) in zip(st.columns(len(NAV)), NAV):
            col.button(label, key=f"nav_{key}", type="primary" if ss.page == key else "tertiary", on_click=goto, args=(key,), width="stretch")
    with cols[2]:
        sticky(st.selectbox, "state", "State", list(STATE_NAMES), format_func=STATE_NAMES.get, label_visibility="collapsed")
        if ss.get("fips") and data.counties().set_index("fips").state_alpha[ss.fips] != ss.state:
            ss.pop("fips")      # the county belonged to the other state
    with cols[3]:
        st.button("Ask the Advisor", key="nav_advisor", on_click=goto, args=("advisor",), width="stretch")
    with cols[4]:
        with st.popover(ss.user.title() if signed_in() else "Account", width="stretch"):
            if signed_in():
                st.markdown(f"Signed in as **{ss.user}**")
                st.button("My Fields", key="acct_fields", on_click=goto, args=("fields",), width="stretch")
                st.button("Log out", key="acct_logout", on_click=logout, width="stretch")
            else:
                st.button("Sign in", key="acct_signin", on_click=goto, args=("login",), width="stretch")
    html("<div class='navrule'></div>")


def footer():
    """Transparency links on every page."""
    html("<div class='footer'></div>")
    cols = st.columns([1, 1, 1, 1, 1, 2.2])
    for col, label in zip(cols, ["Data sources", "Methodology", "Agricultural guidance", "Privacy", "Support"]):
        col.button(label, key=f"foot_{label}", type="tertiary", on_click=goto, args=("trust",), kwargs={"trust_section": label}, width="stretch")
    html("<p class='small'>DroughtLens shows what past droughts cost corn and soybean farmers in Nebraska and Iowa. "
         "It is not an official drought assessment or a weather forecast. Built by Team Wolverine, Data to Harvest Hackathon, Delaware State University.</p>")
