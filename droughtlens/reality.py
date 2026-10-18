"""The Drought Category Reality Check: Team Wolverine's table (2000-2012), its 2013-2025 check, timing and irrigation.

This is the analysis the farmer-facing numbers come from. The functions here moved over from the earlier dashboard
unchanged in behaviour, so the figures still match the README and the evidence app.
"""
import numpy as np
import pandas as pd
import streamlit as st

from src.data_loader import load_master, load_irrigation
from wolverine import data_prep, drought_timing as dt, reality_table as rt
from wolverine.contracts import TRAIN_YEARS, TEST_YEARS, TOLERANCE_PTS, MIN_CELL_N, STRICT_ANOM

from droughtlens.data import SEVERE, STATE_NAMES, CROP_NAMES

MASTER_ANOM = "yield_anomaly_pct"

# The dataset records every crop in bushels per acre. Corn is shown in tons per acre:
# a bushel of shelled corn is 56 pounds and a ton is 2,000 pounds. Soybeans stay in bushels.
YIELD_UNITS = {
    "CORN": {"per_acre": "tons per acre", "short": "tons/ac", "total": "tons", "factor": 56 / 2000, "digits": 2},
    "SOYBEANS": {"per_acre": "bushels per acre", "short": "bu/ac", "total": "bushels", "factor": 1.0, "digits": 0},
}


def per_acre(crop, bushels, signed=False):
    u = YIELD_UNITS[crop]
    return f"{bushels * u['factor']:{'+' if signed else ''}.{u['digits']}f} {u['short']}"


def total_amount(crop, bushels):
    u = YIELD_UNITS[crop]
    return f"{bushels * u['factor']:,.0f} {u['total']}"


def lc_first(text):
    """Lower-case the first letter only, so 'Extreme drought (D3)' keeps its D-code."""
    return text[0].lower() + text[1:]


def below(v, digits=0):
    """'17% below normal' for a mean yield change in percent (negative = below)."""
    return f"{abs(v):.{digits}f}% {'below' if v < 0 else 'above'} normal"


def loss_text(v):
    """'17% loss' or '3% gain' for a mean yield change in percent."""
    return f"{abs(v):.0f}% {'loss' if v < 0 else 'gain'}"


def loss_phrase(v):
    """'a 12% loss' or 'an 18% loss' (right article for the number)."""
    n = round(abs(v))
    article = "an" if n in (8, 11, 18) or 80 <= n <= 89 else "a"
    return f"{article} {loss_text(v)}"


def crop_adj(crop):
    """'corn' or 'soybean', for 'corn yields' and 'soybean yields'."""
    return "corn" if crop == "CORN" else "soybean"


# --- The analysis panel and its tables ------------------------------------------
@st.cache_data(show_spinner=False)
def get_panel():
    """Reported county yields with a drought reading, plus drought timing and Nebraska irrigation group."""
    panel = data_prep.add_strict_anomaly(data_prep.build_panel())
    panel = panel.merge(dt.drought_timing(), on=["fips", "crop", "year"], how="left")
    return panel.merge(dt.irrigation_groups(), on=["fips", "crop"], how="left")


@st.cache_data(show_spinner=False)
def analysis(crop, anom=MASTER_ANOM):
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


def verdict(row):
    """(css class, sentence): did the 2000-2012 estimate hold up on 2013-2025?"""
    if row is None or not row.enough_rows:
        return "na", f"Too few past years to check (fewer than {MIN_CELL_N} in one period). Don't rely on this number."
    if row.within_tol:
        return "ok", f"Held up. 2013–2025 came in at {below(row.test_mean)}, within {TOLERANCE_PTS:g} points."
    return "miss", f"Missed. 2013–2025 came in at {below(row.test_mean)}, {row.abs_error:.0f} points away. Treat this estimate with care."


def state_estimate(crop, state, level, irrig=None):
    """The reality-check estimate for a state, crop and drought level (optionally the Nebraska irrigation group).

    Returns (backtest row or None, verdict css class, verdict sentence).
    """
    a = analysis(crop)
    row = cell(a["irr_check"], "NE", level, irrig) if irrig and state == "NE" else cell(a["check"], state, level)
    css, text = verdict(row)
    return row, css, text


def typical_yield(panel, state, county, crop):
    """The county's recent trend yield (bushels per acre) in a normal year; recent reported yields if no trend exists."""
    rows = panel[(panel.state_alpha == state) & (panel.county_name == county) & (panel.crop == crop)].sort_values("year")
    trend = (rows.yield_per_acre / (1 + rows.yield_anomaly_pct / 100)).dropna()
    return trend.tail(3).mean() if len(trend) else rows.yield_per_acre.tail(3).mean()


def peak_share(a):
    """Share of D3 seasons in which severe drought reached the county in July or August."""
    counts = a["d3_timing"]
    return counts.get("peak", 0) / counts.sum() if counts.sum() else None


# --- The six questions in the data dictionary -----------------------------------
WEEK_BINS, WEEK_LABELS = [-1, 0, 4, 9, 100], ["None", "1–4 weeks", "5–9 weeks", "10 or more weeks"]
HEAT_BINS, HEAT_LABELS = [-1, 0, 2, 5, 9, 14, 100], ["0 days", "1–2", "3–5", "6–9", "10–14", "15 or more"]
SHARP = -5.0        # "sharply negative": an average yield change at or below this many percent


def r_squared(d, y, cols):
    """Share of the variation in y that a straight-line fit on `cols` explains."""
    X = np.column_stack([np.ones(len(d))] + [d[c].values for c in cols])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return 1 - (y - X @ beta).var() / y.var()


@st.cache_data(show_spinner=False)
def research(crop):
    """One result per question. Q1, Q2 and Q6 follow the selected crop; Q3, Q4 and Q5 are fixed comparisons."""
    m = load_master()
    m = m[m.yield_status == "reported"].assign(severe=lambda d: d.max_drought_severity >= SEVERE)
    out = {}

    q = m[m.state_alpha.isin(["IA", "NE"]) & (m.crop == crop)].dropna(subset=["yield_anomaly_pct", "max_drought_severity", "weeks_in_d2_plus"])
    out["q1_flag"] = {k: (g.yield_anomaly_pct.mean(), len(g)) for k, g in q.groupby(["state_alpha", "severe"])}
    out["q1_weeks"] = (q.assign(weeks=pd.cut(q.weeks_in_d2_plus, WEEK_BINS, labels=WEEK_LABELS))
                        .groupby(["state_alpha", "weeks"], observed=True).yield_anomaly_pct.agg(["mean", "size"]).reset_index())

    g = (q[(q.state_alpha == "IA") & q.severe].groupby("fips")
          .agg(change=("yield_anomaly_pct", "mean"), years=("yield_anomaly_pct", "size"), aws=("aws_100cm_mm", "first")))
    g = g[g.years >= 3].dropna()
    g["third"] = pd.qcut(g.aws, 3, labels=["Lowest third", "Middle third", "Highest third"])
    out["q2"] = {"r": np.corrcoef(g.aws, g.change)[0, 1], "counties": len(g),
                 "thirds": g.groupby("third", observed=True).agg(change=("change", "mean"), aws=("aws", "mean")).reset_index()}

    ne = m[(m.state_alpha == "NE") & m.crop.isin(["CORN", "SOYBEANS", "SORGHUM"])].dropna(subset=["yield_anomaly_pct", "max_drought_severity"])
    irr = load_irrigation()
    irr = irr[irr.state_alpha == "NE"].groupby("crop").irrigated_share.mean()
    sorghum = m[(m.state_alpha == "NE") & (m.crop == "SORGHUM")].groupby("year").fips.nunique()
    out["q3"] = {"change": ne[ne.severe].groupby("crop").yield_anomaly_pct.mean(), "irrigated": irr,
                 "counties": {y: int(sorghum.get(y, 0)) for y in (2000, 2005, 2010, 2015, 2020, 2025)}}

    out["q4"] = []
    for state, c, label in (("IA", "CORN", "Iowa corn"), ("IA", "SOYBEANS", "Iowa soybeans"), ("NE", "CORN", "Nebraska corn"), ("CA", "CORN", "California corn")):
        d = m[(m.state_alpha == state) & (m.crop == c)].dropna(subset=["yield_anomaly_pct", "precip_anomaly_pct"])
        r = np.corrcoef(d.precip_anomaly_pct, d.yield_anomaly_pct)[0, 1]
        out["q4"].append({"label": label, "r": r, "r2": r * r, "n": len(d)})

    h = m[m.state_alpha.isin(["IA", "NE"]) & m.crop.isin(["CORN", "SOYBEANS"])].dropna(subset=["yield_anomaly_pct", "extreme_heat_days"])
    out["q5"] = (h.assign(heat=pd.cut(h.extreme_heat_days, HEAT_BINS, labels=HEAT_LABELS))
                  .groupby(["crop", "heat"], observed=True).yield_anomaly_pct.agg(["mean", "size"]).reset_index())

    out["q6"] = {}
    for state in ("IA", "NE"):
        d = m[(m.state_alpha == state) & (m.crop == crop)].dropna(subset=["yield_per_acre", "nccpi_crop", "weeks_in_d2_plus", "mean_dsci"]).copy()
        y = (d.yield_per_acre - d.groupby("year").yield_per_acre.transform("mean")).values
        soil = r_squared(d, y, ["nccpi_crop"])
        both = r_squared(d, y, ["nccpi_crop", "weeks_in_d2_plus", "mean_dsci"])
        out["q6"][state] = {"soil": soil, "drought": both - soil, "rest": 1 - both, "n": len(d)}
    return out


def first_bucket(rows, test):
    """The first heat-day group whose average yield change meets `test`, or None."""
    hit = rows[test(rows["mean"])]
    return str(hit.heat.iloc[0]) if len(hit) else None


def heat_thresholds(crop):
    """(first group with a negative average, first group at or below SHARP) of extreme-heat days for a crop."""
    g = research("CORN")["q5"]
    g = g[g.crop == crop]
    return first_bucket(g, lambda v: v < 0), first_bucket(g, lambda v: v <= SHARP)
