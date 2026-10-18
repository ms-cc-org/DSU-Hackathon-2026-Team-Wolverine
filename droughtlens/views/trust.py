"""Trust and transparency: data sources, methodology, guidance, privacy and support."""
import streamlit as st
from wolverine import reality_table as rt
from wolverine.contracts import MIN_CELL_N, TOLERANCE_PTS

from droughtlens import data
from droughtlens.reality import analysis
from droughtlens.theme import callout, chapter, html
from droughtlens.views.common import sticky

SECTIONS = ["Data sources", "Methodology", "Agricultural guidance", "Privacy", "Support"]
REPO = "https://github.com/ms-cc-org/DSU-Hackathon-2026-Team-Wolverine"


def sources():
    chapter("Data sources", "Every number comes from these files", "DroughtLens uses every dataset in the project's data folder. Nothing is invented or filled in.")
    rows = "".join(f"<tr><td><b>{n}</b></td><td>{d}</td><td>{r:,}</td><td>{c}</td><td class='small'>{src}</td></tr>" for n, d, r, c, src in data.source_summary())
    html(f"<table class='vt'><tr><th>Dataset</th><th>What it holds</th><th>Rows</th><th>Coverage</th><th>Source</th></tr>{rows}</table>")
    st.markdown(f"The latest drought reading in our data is **{data.latest_observation():%B %d, %Y}**. DroughtLens has no live feed. "
                "The full field-by-field description is in `data/data_dictionary.md`.")
    st.markdown("**Credits**")
    st.markdown(
        "- **U.S. Drought Monitor:** jointly produced by the National Drought Mitigation Center at the University of Nebraska-Lincoln, the United States Department of Agriculture, and the National Oceanic and Atmospheric Administration.\n"
        "- **USDA NASS:** this product uses the NASS API but is not endorsed or certified by NASS.\n"
        "- **NOAA ACIS:** weather data from the Applied Climate Information System, NOAA Regional Climate Centers.\n"
        "- **Soil:** Soil Survey Staff, Natural Resources Conservation Service, United States Department of Agriculture. Soil Survey Geographic (SSURGO) Database, via Soil Data Access.\n"
        "- **Satellite greenness:** NASA MODIS MOD13Q1, extracted with Google Earth Engine.\n"
        "- **Photos:** USDA and NRCS, public domain, via Wikimedia Commons.")


def methodology():
    chapter("Methodology", "How DroughtLens works, and what it does not do")
    s = [rt.score(analysis(c)["check"]) for c in ("CORN", "SOYBEANS")]
    st.markdown(
        "**DroughtLens does not predict drought or yield.** It shows what past droughts cost, and checks whether that held steady. This is the Drought Category Reality Check:\n\n"
        "1. For each state, crop and drought level we averaged how far yield sat from each county's own trend line in **2000 to 2012**. A normal year is 0%.\n"
        f"2. We checked each average against **2013 to 2025**, years we never used to build it. An estimate *held up* if later years landed within {TOLERANCE_PTS:g} points. "
        f"A level is checked only with at least {MIN_CELL_N} county-years in both periods.\n"
        f"3. On the master trend, {s[0]['share_within_tol']:.0%} of corn estimates and {s[1]['share_within_tol']:.0%} of soybean estimates held up (average miss {s[0]['weighted_mae']:.1f} and {s[1]['weighted_mae']:.1f} points).")
    callout("<span class='tagline'>Limitations</span>"
            "Drought level is the season's worst weekly category, so one bad week counts like a whole bad season. County yields come from NASS surveys and small counties drop out in some years. "
            "The master trend is fitted on all 26 years and flatters the check; the strict trend (2000 to 2012 only) is the harder test. Irrigation data runs 2000 to 2018. "
            "Some drought levels have too few past years to quote. Estimates are averages of past years, not forecasts.", "warning")
    st.markdown("**Official sources versus DroughtLens.** Drought levels come from the U.S. Drought Monitor, yields from USDA NASS and weather from NOAA. "
                "The estimates, the Advisor's answers and the plans are produced by DroughtLens with fixed rules. They are **not** official drought assessments, weather forecasts or professional agronomic advice.")
    st.markdown("When data is missing, DroughtLens says so: counties without reported yields show their drought and weather record but no yield figures, and current conditions and forecasts are marked not available.")


def guidance():
    chapter("Agricultural guidance", "What counts as guidance")
    st.markdown(
        "Lines marked **General guidance** are common practice, such as checking the Drought Monitor, scouting fields and talking with your crop insurance agent. They are **not** derived from our data. "
        "Lines marked **Data** are read from our files.\n\n"
        "DroughtLens does not recommend costly interventions, irrigation volumes or schedules, or changes to what you plant, because the data here cannot support those decisions. "
        "Before spending money, talk with your **county extension office** and your **crop insurance agent**, and trust what you see in your own fields.")


def privacy():
    chapter("Privacy", "What we keep, and where")
    st.markdown(
        "- **Fields and plans you save** are stored in a file on the server running this app (`app_data/`). That folder is excluded from the project's shared repository.\n"
        "- **Sign-in is a demo.** It gates the demo and is not real security. Do not enter anything you would not want the people who run this server to see.\n"
        "- **No data is sent to other services** by DroughtLens. Your browser loads fonts from Google Fonts.\n"
        "- You can **remove a field or delete a plan** at any time under My Fields and My Farm Plan.")


def support():
    chapter("Support", "Questions, corrections and feedback")
    st.markdown(f"DroughtLens was built by Team Wolverine for the Data to Harvest Hackathon at Delaware State University. "
                f"To report a problem or suggest a change, open an issue on the team's repository: [{REPO}]({REPO}).\n\n"
                "For drought conditions and decisions on your farm, contact your county extension office.")


def show():
    html("<div class='eyebrow'>Trust and transparency</div>")
    section = sticky(st.radio, "trust_section", "Section", SECTIONS, horizontal=True)
    {"Data sources": sources, "Methodology": methodology, "Agricultural guidance": guidance, "Privacy": privacy, "Support": support}[section]()
