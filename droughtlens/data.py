"""Loaders for every dataset in data/, cached, plus the Nebraska and Iowa place list and the season periods.

Nothing here invents data: each function reads a file in data/ and returns it filtered to what the page asked for.
"""
import numpy as np
import pandas as pd
import streamlit as st

from src import data_loader as dl
from wolverine import drought_timing as dt

STATE_NAMES = {"NE": "Nebraska", "IA": "Iowa"}
CROPS = ["CORN", "SOYBEANS"]
CROP_NAMES = {"CORN": "Corn", "SOYBEANS": "Soybeans"}
SEVERE = 3          # max_drought_severity 3 = D2 (severe). The dataset's scale is offset by one from the D-labels.
FIRST_YEAR, LAST_YEAR = 2000, 2025

# Planning periods: windows inside the crop's growing season (the master dataset's season windows).
PERIODS = {
    "early": ("Early season", "May to June"),
    "peak": ("Peak season", "July to August"),
    "late": ("Late season", "September to harvest"),
    "full": ("Full season", "May to harvest"),
}


def period_window(crop, period):
    """(month, day, month, day) for a planning period of a crop."""
    season = dt.SEASON[crop]
    return {"early": (5, 1, 6, 30), "peak": (7, 1, 8, 31), "late": (9, 1, season[2], season[3]), "full": season}[period]


# --- Places ----------------------------------------------------------------
@st.cache_data
def counties():
    """Every Nebraska and Iowa county DroughtLens supports (the 192 with weather and drought records)."""
    rows = [f["properties"] for f in dl.load_counties()["features"] if f["properties"]["state_alpha"] in STATE_NAMES]
    return pd.DataFrame(rows).sort_values(["state_alpha", "county_name"]).reset_index(drop=True)


@st.cache_data
def county_geojson():
    g = dl.load_counties()
    return {"type": "FeatureCollection", "features": [f for f in g["features"] if f["properties"]["state_alpha"] in STATE_NAMES]}


def county_name(fips):
    row = counties()[counties().fips == fips]
    return row.county_name.iloc[0] if len(row) else fips


# --- Yield, weather summary, drought summary, soil: the master dataset ---------
@st.cache_data
def master():
    """Nebraska and Iowa rows of the master dataset (county x crop x year), with the drought level as an integer."""
    m = dl.load_master()
    m = m[m.state_alpha.isin(STATE_NAMES)].copy()
    m["level"] = m["max_drought_severity"]
    return m


@st.cache_data
def season_rows(fips, crop):
    m = master()
    return m[(m.fips == fips) & (m.crop == crop)].sort_values("year").reset_index(drop=True)


@st.cache_data
def reported_counties(crop):
    """FIPS codes of counties with at least one reported yield for the crop."""
    m = master()
    return set(m[(m.crop == crop) & (m.yield_status == "reported")].fips)


# --- Drought Monitor, weekly --------------------------------------------------
@st.cache_data
def weekly(fips):
    """One county's weekly drought record, with the Drought Monitor level on the dataset's 0-5 scale."""
    d = pd.read_parquet(dl._ROOT / "data/processed/drought/drought_weekly.parquet", filters=[("fips", "==", fips)])
    d = d.sort_values("map_date").reset_index(drop=True)
    d["level"] = dt.week_levels(d)
    d["year"] = d.map_date.dt.year
    d["d2plus_pct"] = d.D2 + d.D3 + d.D4
    return d


@st.cache_data
def latest_observation():
    return dl.load_weekly_drought().map_date.max()


@st.cache_data
def period_record(fips, crop, period):
    """Per year: the worst weekly drought level in the period, weeks spent in D2 or worse, and the peak share of the county in D2 or worse."""
    w = weekly(fips)
    s = w[dt.in_window(w.map_date, *period_window(crop, period))]
    g = s.groupby("year")
    return pd.DataFrame({
        "level": g["level"].max(),
        "weeks_d2": g["level"].apply(lambda x: int((x >= SEVERE).sum())),
        "peak_d2_pct": g["d2plus_pct"].max(),
    }).reset_index()


# --- Daily weather ------------------------------------------------------------
@st.cache_data
def daily_weather(fips):
    w = pd.read_parquet(dl._ROOT / "data/processed/acis/weather_daily.parquet", filters=[("fips", "==", fips)])
    return w.sort_values("date").reset_index(drop=True)


@st.cache_data
def precip_curves(fips, crop, period="full"):
    """Cumulative precipitation (mm) through the period, one column per year. Row 1 is the first day of the window."""
    w = daily_weather(fips)
    m1, d1, m2, d2 = period_window(crop, period)
    w = w[dt.in_window(w.date, m1, d1, m2, d2)].copy()
    w["year"] = w.date.dt.year
    w["day"] = w.groupby("year").cumcount() + 1
    w["cum"] = w.groupby("year").pcpn_mm.cumsum()
    return w.pivot(index="day", columns="year", values="cum")


# --- Satellite, soil, irrigation, NASS area -----------------------------------
@st.cache_data
def modis(fips):
    m = dl.load_modis()
    return m[m.fips == fips].sort_values("year").reset_index(drop=True)


@st.cache_data
def soil(fips):
    """The county's soil water capacity and productivity, with where it ranks among Nebraska and Iowa counties."""
    s = dl.load_soil()
    ia_ne = s[s.state_alpha.isin(STATE_NAMES)]
    row = s[s.fips == fips]
    if row.empty or pd.isna(row.aws_100cm_mm.iloc[0]):
        return None
    r = row.iloc[0]
    return {
        "aws_mm": float(r.aws_100cm_mm), "droughty_pct": float(r.droughty_pct),
        "nccpi_corn": float(r.nccpi_corn), "nccpi_soy": float(r.nccpi_soy),
        "aws_rank_pct": float((ia_ne.aws_100cm_mm < r.aws_100cm_mm).mean()),
        "aws_median_mm": float(ia_ne.aws_100cm_mm.median()),
    }


@st.cache_data
def irrigation_groups():
    return dt.irrigation_groups()


@st.cache_data
def irrigation_share():
    """Average irrigated share of harvested acres per Nebraska county and crop (NASS irrigation records, 2000 to 2018)."""
    i = dl.load_irrigation()
    return i[i.state_alpha == "NE"].groupby(["fips", "crop"]).irrigated_share.mean()


@st.cache_data
def irrigation(fips, crop):
    """(group, average irrigated share) for a Nebraska county and crop, or None when NASS has no irrigation record for it."""
    g = irrigation_groups()
    g = g[(g.fips == fips) & (g.crop == crop)]
    share = irrigation_share().get((fips, crop))
    if g.empty or share is None:
        return None
    return g.irrig_group.iloc[0], float(share)


@st.cache_data
def harvested_area(fips, crop):
    """(year, acres) of the county's most recent NASS harvested-area figure for the crop, or None."""
    n = dl.load_nass_raw()
    n = n[(n.fips == fips) & (n.crop == crop) & (n.statistic == "AREA HARVESTED")].dropna(subset=["value"])
    if n.empty:
        return None
    last = n.sort_values("year").iloc[-1]
    return int(last.year), float(last.value)


# --- Sources, for the transparency page ---------------------------------------
@st.cache_data
def source_summary():
    """Row counts and coverage for each dataset, read from the files themselves."""
    master_all = dl.load_master()
    drought = dl.load_weekly_drought()
    weather = pd.read_parquet(dl._ROOT / "data/processed/acis/weather_daily.parquet", columns=["date"])
    modis_all, soil_all = dl.load_modis(), dl.load_soil()
    nass, irr = dl.load_nass_raw(), dl.load_irrigation()
    return [
        ("Master dataset", "County x crop x year yield, season weather, drought and soil", len(master_all),
         f"{master_all.fips.nunique()} counties, {int(master_all.year.min())} to {int(master_all.year.max())}", "USDA NASS, NOAA ACIS, U.S. Drought Monitor, NRCS SSURGO"),
        ("Weekly drought", "County percent in each Drought Monitor class, weekly", len(drought),
         f"{drought.fips.nunique()} counties, {drought.map_date.min():%b %Y} to {drought.map_date.max():%b %d, %Y}", "U.S. Drought Monitor"),
        ("Daily weather", "Daily high, low and precipitation", len(weather),
         f"{weather.date.min():%Y} to {weather.date.max():%Y}", "NOAA ACIS"),
        ("NASS records", "Yield, planted and harvested area", len(nass), f"{nass.fips.nunique()} counties", "USDA NASS Quick Stats"),
        ("Soil", "Water storage and soil productivity per county", len(soil_all), f"{soil_all.fips.nunique()} counties", "USDA NRCS SSURGO"),
        ("Satellite greenness", "Annual vegetation index per county", len(modis_all),
         f"{modis_all.fips.nunique()} counties, {int(modis_all.year.min())} to {int(modis_all.year.max())}", "NASA MODIS via Google Earth Engine"),
        ("Irrigation", "Irrigated share and yields, mostly Nebraska", len(irr),
         f"{int(irr.year.min())} to {int(irr.year.max())}", "USDA NASS Quick Stats"),
        ("County boundaries", "Map shapes", len(dl.load_counties()["features"]), "Iowa, Nebraska, California, Delaware", "Hackathon organisers"),
    ]
