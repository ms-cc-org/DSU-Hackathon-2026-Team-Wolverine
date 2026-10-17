import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.data_loader import load_master
from wolverine import data_prep, drought_timing as dt, reality_table as rt
from wolverine.contracts import *

st.set_page_config(page_title="Drought Category Reality Check", page_icon=":ear_of_corn:", layout="wide")

COMING_SOON = "Coming soon: this part isn't merged yet."


# Data

@st.cache_data
def load_all():
    notes = []
    try:
        panel = data_prep.build_panel()
    except NotImplementedError:
        panel = load_master()                  # Ralph's panel not merged yet
        notes.append("Using the raw master dataset (data_prep.build_panel not merged yet).")
    try:
        panel = data_prep.add_strict_anomaly(panel)
    except NotImplementedError:
        notes.append("Strict trend not available yet (data_prep.add_strict_anomaly not merged).")
    try:
        panel = panel.merge(dt.drought_timing(), on=["fips", "crop", "year"], how="left")
        panel = panel.merge(dt.irrigation_groups(), on=["fips", "crop"], how="left")
    except NotImplementedError:
        pass                                   # Connor's part not merged yet
    return panel, notes


panel, load_notes = load_all()


# Sidebar

st.sidebar.header("Settings")
crop = st.sidebar.radio("Crop", CROPS, format_func=str.title)
version = st.sidebar.radio("Trend version", ["Strict trend (2000–2012 only)", "Master trend (all years)"])
strict = version.startswith("Strict")
if strict and STRICT_ANOM not in panel:
    st.sidebar.warning("Strict trend not ready, showing the master trend.")
    strict = False
anom = STRICT_ANOM if strict else "yield_anomaly_pct"
view = panel[panel.crop == crop]
for note in load_notes:
    st.sidebar.caption(note)

st.title("Drought Category Reality Check")
st.caption(f"Does the same drought level mean the same yield loss in Iowa and Nebraska? · {crop.title()} · {version}")

tab_answer, tab_check, tab_why, tab_about = st.tabs(
    ["The answer", "Did it hold up? (2013–2025)", "Why it misses", "About the data"]
)


# Tab 1: the answer

with tab_answer:
    try:
        table = rt.build_table(view, TRAIN_YEARS, anom)
        check = rt.backtest(view, anom)
        st.subheader(rt.recommendation(check, table))

        d3 = rt.same_meaning(table, level=4, crop=crop)
        c1, c2, c3 = st.columns(3)
        c1.metric("Iowa D3 loss", f"{d3['ia']:.1f}%")
        c2.metric("Nebraska D3 loss", f"{d3['ne']:.1f}%")
        c3.metric("Gap", f"{d3['gap']:.1f} pts",
                  "same within tolerance" if d3["same"] else "differs", delta_color="off")

        fig = px.bar(
            table, x="level_label", y="mean_loss", color="state_alpha", barmode="group",
            category_orders={"level_label": [LEVEL_LABELS[l] for l in LEVELS]},
            labels={"level_label": "Drought level", "mean_loss": "Mean yield anomaly (%)", "state_alpha": "State"},
            hover_data=["n"],
        )
        st.plotly_chart(fig, width="stretch")
    except NotImplementedError:
        st.info(COMING_SOON)


# Tab 2: did it hold up?

with tab_check:
    try:
        check = rt.backtest(view, anom)
        s = rt.score(check)
        c1, c2, c3 = st.columns(3)
        c1.metric(f"Cells within {TOLERANCE_PTS:g} pts", f"{s['share_within_tol']:.0%}")
        c2.metric("Weighted mean error", f"{s['weighted_mae']:.1f} pts")
        c3.metric("Cells scored", f"{s['cells_scored']} of {len(check)}")

        def colour(row):
            if not row.enough_rows:
                bg = "#e0e0e0"
            elif row.within_tol:
                bg = "#d4edda"
            else:
                bg = "#f8d7da"
            return [f"background-color: {bg}"] * len(row)

        shown = check.drop(columns=["crop", "level"])
        st.dataframe(shown.style.apply(colour, axis=1), width="stretch", hide_index=True)
        st.caption(f"Green: within {TOLERANCE_PTS:g} points. Red: missed. Grey: fewer than {MIN_CELL_N} rows in a period, not scored.")

        fig = px.scatter(
            shown.dropna(subset=["train_mean", "test_mean"]), x="train_mean", y="test_mean",
            color="state_alpha", text="level_label",
            labels={"train_mean": "2000–2012 mean (%)", "test_mean": "2013–2025 mean (%)", "state_alpha": "State"},
        )
        lo = float(min(shown.train_mean.min(), shown.test_mean.min())) - 2
        hi = float(max(shown.train_mean.max(), shown.test_mean.max())) + 2
        fig.add_trace(go.Scatter(x=[lo, hi, hi, lo], y=[lo + TOLERANCE_PTS, hi + TOLERANCE_PTS, hi - TOLERANCE_PTS, lo - TOLERANCE_PTS],
                                 fill="toself", fillcolor="rgba(128,128,128,0.15)", line_width=0,
                                 name=f"±{TOLERANCE_PTS:g} pts", hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=[lo, hi], y=[lo, hi], mode="lines", line=dict(dash="dash", color="grey"),
                                 name="y = x"))
        fig.update_traces(textposition="top center", selector=dict(mode="markers+text"))
        st.plotly_chart(fig, width="stretch")
    except NotImplementedError:
        st.info(COMING_SOON)


# Tab 3: why it misses

with tab_why:
    if "timing" not in view and "irrig_group" not in view:
        st.info(COMING_SOON)

    if "timing" in view:
        st.subheader("Peak-season vs early drought")
        try:
            t = rt.build_table(view, (TRAIN_YEARS[0], TEST_YEARS[1]), anom, extra_by=["timing"])
            t = t[(t.level == 4) & t.timing.isin(["early", "peak"])]
            fig = px.bar(t, x="state_alpha", y="mean_loss", color="timing", barmode="group",
                         labels={"state_alpha": "State", "mean_loss": "Mean yield anomaly at D3 (%)"},
                         hover_data=["n"])
            st.plotly_chart(fig, width="stretch")
            covered = view.dropna(subset=["timing"])
            st.caption(f"Years {int(covered.year.min())}–{int(covered.year.max())}, "
                       f"{covered.fips.nunique()} counties with a timing label.")
        except NotImplementedError:
            st.info(COMING_SOON)

    if "irrig_group" in view:
        st.subheader("Nebraska: irrigated vs dryland")
        try:
            ne = view[view.state_alpha == "NE"]
            t = rt.build_table(ne, TRAIN_YEARS, anom, extra_by=["irrig_group"])
            t = t[t.irrig_group.isin(["mostly irrigated", "mostly dryland"])]
            fig = px.bar(t, x="level_label", y="mean_loss", color="irrig_group", barmode="group",
                         category_orders={"level_label": [LEVEL_LABELS[l] for l in LEVELS]},
                         labels={"level_label": "Drought level", "mean_loss": "Mean yield anomaly (%)",
                                 "irrig_group": "County group"},
                         hover_data=["n"])
            st.plotly_chart(fig, width="stretch")
            st.caption("Irrigation data ends 2018; each county gets one average irrigated share.")
        except NotImplementedError:
            st.info(COMING_SOON)


# Tab 4: about the data

with tab_about:
    try:
        st.dataframe(data_prep.coverage_report(view).reset_index(), width="stretch", hide_index=True)
    except NotImplementedError:
        st.info(COMING_SOON)

    st.subheader("Limitations")
    st.markdown(
        "- Drought level is the season's worst USDM category, so a single bad week counts the same as a whole bad season.\n"
        "- County yields come from NASS surveys; small counties drop out in some years.\n"
        "- The strict trend is fitted on 2000–2012 only, so 2013–2025 is a real out-of-sample check. "
        "The master trend uses all years and flatters the check.\n"
        "- Irrigation shares end in 2018 and are averaged to one value per county."
    )
    st.subheader("Credits")
    st.markdown(
        "- **U.S. Drought Monitor:** The U.S. Drought Monitor is jointly produced by the National Drought "
        "Mitigation Center at the University of Nebraska-Lincoln, the United States Department of Agriculture, "
        "and the National Oceanic and Atmospheric Administration.\n"
        "- **USDA NASS:** This product uses the NASS API but is not endorsed or certified by NASS.\n"
        "- **NOAA ACIS:** Weather data from the Applied Climate Information System (ACIS), NOAA Regional Climate Centers.\n"
        "- **Soil:** Soil Survey Staff, Natural Resources Conservation Service, United States Department of "
        "Agriculture. Soil Survey Geographic (SSURGO) Database, via Soil Data Access."
    )
