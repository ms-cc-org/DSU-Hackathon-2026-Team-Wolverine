"""County-level facts, assembled from the datasets in data/. Every figure here is read from a file, none is modelled."""
import numpy as np
import pandas as pd

from droughtlens import data
from droughtlens.data import SEVERE, STATE_NAMES, CROP_NAMES, PERIODS, FIRST_YEAR, LAST_YEAR
from droughtlens.reality import below, lc_first
from droughtlens.theme import LEVEL_NAME


def county_state(fips):
    row = data.counties()[data.counties().fips == fips]
    return row.state_alpha.iloc[0]


def county_profile(fips, crop, period="full"):
    """Everything DroughtLens knows about one county, one crop and one planning period."""
    name, state = data.county_name(fips), county_state(fips)
    rec = data.period_record(fips, crop, period)
    n = len(rec)
    d2 = rec[rec.level >= SEVERE]
    worst = rec.sort_values(["level", "weeks_d2", "peak_d2_pct"], ascending=False).iloc[0] if n else None

    season = data.season_rows(fips, crop)
    rep = season[season.yield_status == "reported"].dropna(subset=["yield_anomaly_pct"])
    dry, other = rep[rep.level >= SEVERE], rep[rep.level < SEVERE]
    hardest = rep.loc[rep.yield_anomaly_pct.idxmin()] if len(rep) else None

    tavg = season.dropna(subset=["tavg_c"])
    slope = np.polyfit(tavg.year, tavg.tavg_c, 1)[0] * 10 if len(tavg) >= 5 else None

    return {
        "fips": fips, "county": name, "state": state, "crop": crop, "period": period,
        "years": n, "d2_years": len(d2), "d3_years": int((rec.level >= 4).sum()),
        "worst_year": int(worst.year) if worst is not None else None,
        "worst_level": int(worst.level) if worst is not None else None,
        "worst_weeks": int(worst.weeks_d2) if worst is not None else None,
        "avg_weeks_d2": float(rec.weeks_d2.mean()) if n else None,
        "record": rec,
        "reported_years": len(rep), "dry_years": len(dry),
        "dry_change": float(dry.yield_anomaly_pct.mean()) if len(dry) else None,
        "other_change": float(other.yield_anomaly_pct.mean()) if len(other) else None,
        "hardest_year": int(hardest.year) if hardest is not None else None,
        "hardest_change": float(hardest.yield_anomaly_pct) if hardest is not None else None,
        "hardest_level": int(hardest.level) if hardest is not None else None,
        "precip_dry": float(dry.precip_anomaly_pct.mean()) if len(dry) else None,
        "heat_dry": float(dry.extreme_heat_days.mean()) if len(dry) else None,
        "heat_all": float(season.extreme_heat_days.mean()) if len(season) else None,
        "season_precip_mm": float(season.precip_mm.mean()) if len(season) else None,
        "temp_trend_per_decade": float(slope) if slope is not None else None,
        "soil": data.soil(fips),
        "irrigation": data.irrigation(fips, crop) if state == "NE" else None,
        "area": data.harvested_area(fips, crop),
        "latest_observation": data.latest_observation(),
    }


def has_yield_record(p):
    return p["reported_years"] > 0


def factors(p):
    """The key contributing factors for a county and crop: (name, value, what it means, where it comes from)."""
    period_label = PERIODS[p["period"]][1]
    out = []
    if p["years"]:
        out.append(("Drought frequency",
                    f"{p['d2_years']} of {p['years']} seasons reached D2 or worse in {period_label}",
                    "How often drought of at least severe strength has reached this county in this part of the season, "
                    f"{FIRST_YEAR} to {LAST_YEAR}. It describes the past; it is not a probability for next year.",
                    "U.S. Drought Monitor, weekly"))
        if p["worst_year"]:
            out.append(("Longest spell",
                        f"{p['worst_year']}: {lc_first(LEVEL_NAME[p['worst_level']])}, {p['worst_weeks']} weeks in D2 or worse",
                        "The year this period was driest by Drought Monitor level, then by weeks spent in D2 or worse.",
                        "U.S. Drought Monitor, weekly"))
    if p["precip_dry"] is not None:
        out.append(("Rainfall in drought years",
                    f"{abs(p['precip_dry']):.0f}% {'below' if p['precip_dry'] < 0 else 'above'} the county's normal growing-season rain",
                    f"Average over the {p['dry_years']} seasons when this county reached D2 or worse.", "NOAA ACIS, growing season"))
    if p["heat_dry"] is not None:
        out.append(("Extreme-heat days",
                    f"{p['heat_dry']:.0f} days at 35 °C (95 °F) or hotter in drought years, against {p['heat_all']:.0f} across all years",
                    "Hot days add stress on top of a dry spell.", "NOAA ACIS, growing season"))
    if p["soil"]:
        s = p["soil"]
        out.append(("Soil water storage",
                    f"{s['aws_mm']:.0f} mm in the top metre, which is more than {s['aws_rank_pct']:.0%} of Nebraska and Iowa counties",
                    "How much water the soil can hold for plants. In Iowa, our data shows only a very weak link between storage and drought-year yield, so treat it as context, not a prediction.",
                    "USDA NRCS SSURGO"))
    if p["state"] == "NE":
        irr = p["irrigation"]
        out.append(("Water source",
                    (f"Mostly {'irrigated' if irr[0] == 'mostly irrigated' else 'dryland'} county ({irr[1]:.0%} of harvested acres irrigated on average)" if irr
                     else "No irrigation record for this county and crop"),
                    "In Nebraska, irrigated counties lost far less than dryland counties at extreme drought.", "USDA NASS irrigation records, 2000 to 2018"))
    else:
        out.append(("Water source", "Rain-fed. NASS publishes no irrigation series for Iowa.",
                    "Drought reaches the crop directly.", "Data dictionary"))
    return out


def season_comparison(p_early, p_late):
    """Compare two sets of seasons for one county: average weather and yield change, from the master dataset rows."""
    cols = {"Growing-season rain (mm)": "precip_mm", "Average temperature (°C)": "tavg_c", "Days at 35 °C or hotter": "extreme_heat_days",
            "Weeks in D2 or worse": "weeks_in_d2_plus", "Yield vs normal (%)": "yield_anomaly_pct"}
    rows = {label: [float(df[c].mean()) if df[c].notna().any() else np.nan for df in (p_early, p_late)] for label, c in cols.items()}
    return pd.DataFrame(rows, index=["2000–2012", "2013–2025"]).T
