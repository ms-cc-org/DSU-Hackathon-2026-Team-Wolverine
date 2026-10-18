# Drought Category Reality Check

**Team Wolverine** · Data to Harvest Hackathon, Delaware State University, October 17–18, 2026

The U.S. Drought Monitor puts every county in a drought level from D0 (abnormally dry) to D4 (exceptional). A "D3" in Iowa and a "D3" in Nebraska carry the same label. Do they cost a corn or soybean farmer the same share of their yield?

This tool answers that with 26 years of county yield and drought records. Its answer: **no**.

## What the tool does and who it's for

**User:** corn and soybean farmers in Iowa and Nebraska, and the state drought task forces whose drought triggers they rely on.

**Decision:** how much yield to expect to lose when their county reaches a given drought level, and whether one drought trigger can serve both states.

**How it works:**
1. We build a **drought level → yield loss table** from 2000–2012. Each cell is the average yield anomaly (how far a county's yield fell below its trend) for one state, crop and drought level.
2. We **check the table on 2013–2025**, years it never saw. A cell "holds up" if the later years land within 4 percentage points of it.
3. We look at **why some cells miss**: whether drought struck in the peak season (July–August) or earlier, and whether Nebraska counties are mostly irrigated or mostly dryland.

The Streamlit app has four tabs:

| Tab | What it shows |
|---|---|
| The answer | The one-sentence recommendation; Iowa vs Nebraska loss at D3; loss by drought level for each state |
| Did it hold up? (2013–2025) | Share of cells within 4 points; each cell coloured green (held up), red (missed) or grey (too few rows to score); train vs test scatter |
| Why it misses | Loss at D3 for peak-season vs early drought; Nebraska loss by drought level for mostly irrigated vs mostly dryland counties |
| About the data | Row counts per state, crop, drought level and period; limitations; source credits |

The sidebar picks the crop and the trend version. The app opens on the master trend; the strict trend is a robustness check (see [Limitations](#limitations)).

### The farmer dashboard (Drought Yield Estimator)

`dashboard_app.py` is the landing page for farmers. It has three pages:

| Page | What it does |
|---|---|
| Welcome | What the tool is for, with a **Get started** button |
| Login | Demo sign-in (username `demo`, password `demo`). It only gates the demo; it is not real security |
| Dashboard | The farmer picks state, county, acres, crop and drought level, and optionally drought timing and irrigation. The dashboard averages the yield change in past years that match, starting with the farmer's county and widening to the state when the county has too few matching years |

It uses the same data and the team's drought timing and irrigation groups (`wolverine/drought_timing.py`).

## How to run it

Needs Python 3.11 or newer (3.12 recommended). From the repo root:

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run wolverine_app.py
```

The app opens in your browser at http://localhost:8501. The data ships with the repo; no API keys are needed.

To open the farmer dashboard instead:

```bash
streamlit run dashboard_app.py                       # or, alongside the main app:
streamlit run dashboard_app.py --server.port 8502
```

Both apps use the colour theme in `.streamlit/config.toml`.

To check that all the parts fit together:

```bash
python scripts/smoke_check.py      # prints the backtest score, then SMOKE OK
```

### Code layout

| File | What it does |
|---|---|
| `wolverine_app.py` | The Streamlit app: the table, its check and the recommendation |
| `dashboard_app.py` | The farmer dashboard: welcome, login and yield estimator pages |
| `assets/` | Photos used by the dashboard (USDA and NRCS, public domain) |
| `.streamlit/config.toml` | Colour theme shared by both apps |
| `wolverine/contracts.py` | Shared settings: states, crops, year ranges, tolerance, column names |
| `wolverine/data_prep.py` | Builds the analysis panel and the strict anomaly |
| `wolverine/reality_table.py` | The loss table, the 2013–2025 backtest, the score and the recommendation |
| `wolverine/drought_timing.py` | Drought timing per county-season, and Nebraska irrigation groups |
| `scripts/smoke_check.py` | End-to-end check that every module runs and returns the agreed columns |
| `notebooks/Ralph.ipynb` | Exploration and checks behind the table |

## Results

The panel has **8,708 county-crop-years** (190 counties, Iowa and Nebraska, corn and soybeans, 2000–2025) with a NASS-reported yield and a drought reading.

### The recommendation

> D3 cost Iowa corn −17.4% vs Nebraska −6.0% in 2000–2012: use state-specific triggers, and trust only the table cells that held up in 2013–2025 (82% did).

This is the sentence the app shows for corn on the master trend, its default view.

| Crop | Iowa at D3 | Nebraska at D3 | Gap | Same within 4 pts? |
|---|---|---|---|---|
| Corn | −17.4% | −6.0% | 11.4 pts | No |
| Soybeans | −15.1% | −9.9% | 5.2 pts | No |

*(2000–2012, master trend.)*

### Did the table hold up on 2013–2025?

**On the master trend, 82% of scored cells held up within 4 points, for corn and for soybeans.**

Each crop has 12 cells (2 states × 6 drought levels). A cell is scored only when it has at least 10 rows in both periods, which leaves 11 per crop (the Iowa D4 cell has only 5 training rows). The weighted mean error weights each cell by its 2013–2025 row count. Every row below matches the "Did it hold up?" tab for that crop and trend.

| Crop | Trend version | Cells within 4 pts | Weighted mean error |
|---|---|---|---|
| Corn | Master trend (main result) | **82%** (9 of 11) | **1.8 pts** |
| Soybeans | Master trend (main result) | **82%** (9 of 11) | **3.1 pts** |
| Corn | Strict trend (robustness check) | 55% (6 of 11) | 13.9 pts |
| Soybeans | Strict trend (robustness check) | 82% (9 of 11) | 3.0 pts |

The biggest miss is the same with either trend: **Iowa at D3**. In 2000–2012 it cost Iowa corn 17.4%; in 2013–2025 it cost 3.9%. Soybeans: 15.1% then 3.9%. Most of Iowa's training-era D3 rows come from the single 2012 drought, so one severe year set the number, and later D3 seasons were milder.

### Why the two states differ

- **Irrigation explains most of the Nebraska gap.** At D3 in 2000–2012 (master trend), mostly dryland Nebraska counties lost 17.8% of their corn yield; mostly irrigated counties lost 0.9%. Soybeans: 17.6% vs 4.6%. Dryland Nebraska loses about what Iowa does.
- **Timing matters.** Almost all D3 seasons include drought in July–August. Iowa corn at D3 with peak-season drought lost 12.5% on average (2000–2025, master trend, 248 county-years). Early-only D3 seasons are too rare (9 county-years in Iowa) to quote.

## Limitations

- **2012 dominates the training years.** 61% of Iowa corn's D3-and-worse training rows (51% for soybeans, 29% in Nebraska) are from 2012. The Iowa D3 numbers are close to "Iowa in 2012".
- **On the strict trend, Iowa corn scores worst** (55% of cells within 4 points) because the 2012 drought flattens its 2000–2012 trend line.
- **Why the strict trend is unreliable for Iowa corn after 2012.** Fitting each county's trend on 2000–2012 ends on the 2012 drought, which flattens the slope (median 0.64 bu/ac/yr with 2012 vs 2.02 without). Extended forward, that trend under-predicts 2013–2025, so Iowa corn's strict test anomalies average +23.5%. That is why corn's strict score is lower; soybeans are not affected (82% on both trends). A trend fit that is robust to one extreme year would fix it.
- **The master trend leaks.** `yield_anomaly_pct` comes from a trend fitted on all 26 years, including the test years, so its scores are somewhat flattering. That is why we report the strict trend alongside it.
- **The drought level is the season's worst week.** `max_drought_severity` is the worst level reached in any week of the season. One bad week counts the same as a whole bad season.
- **Thin cells.** Iowa has only 5 training rows at D4 for each crop. Don't quote Iowa D4 numbers.
- **Irrigation groups are coarse.** Each Nebraska county gets one irrigated share, averaged over 2000–2018 (the last year of irrigation data for corn and soybeans), and is split at 50% into "mostly irrigated" or "mostly dryland". Iowa counties are not split.
- **Timing labels use the full season.** A season is "peak" if severe drought (D2 or worse) reached the county in July–August, and "early" if it did so only before July. That is known only at the end of the season, so it explains losses after the fact rather than forecasting them.
- **Yields come from NASS surveys.** Small counties drop out in some years, and county-crop pairs with too few reported years have no anomaly.

## Team

| Name | GitHub | Role |
|---|---|---|
| Tolu Adeola | [@lod23](https://github.com/lod23) | Shared code skeleton, Streamlit app, integration and merges, README |
| Ralph Reyes | [@RRR-Reyes](https://github.com/RRR-Reyes) | Analysis panel, strict trend, reality table and backtest |
| Connor Little | [@GAMEMONKEI](https://github.com/GAMEMONKEI) | Drought timing and irrigation groups; problem statement |
| Edaijah Rodriguez | [@daejadoll](https://github.com/daejadoll) | Landing page and farmer dashboard: welcome and login pages, colour theme, photos, yield estimator |

## AI disclosure

We used AI tools as described below and checked every number against the data before relying on it.

**Tolu (app and integration)**
- **Tool:** Claude Code (Claude Opus 5.5).
- **What for:** creating the shared module skeleton (`contracts.py` and the function stubs); writing `wolverine_app.py` and `scripts/smoke_check.py`; merging Ralph's and Connor's branches and fitting the app to their outputs; testing the merged dashboard; drafting this README.
- **How it was checked:** the app was run headlessly with Streamlit's test runner at each stage: with the stubs only, with stand-in functions, and with the real modules for both crops, with no errors. Every README number was recomputed from the merged code and matched against Ralph's notes (both crops combined on the master trend: 82% within 4 points, 2.4 pts; Iowa corn D3 −17.4 / −3.9). Before merging Connor's code, we confirmed the irrigated share is a 0–1 fraction and that the weekly D0–D4 percentages are non-overlapping.

**Ralph (data prep and reality table)**
- **Tool:** Claude Code (Claude Opus 5.5).
- **What for:** turning the task spec's pseudo-code into working pandas; writing the check script; finding the cause of the strict-anomaly bias in test years; drafting his notes.
- **How it was checked:** the Iowa corn D3 cell reproduces the planned values exactly (train −17.4, test −3.9). He checked Polk County 2012 and the per-county training means by hand. He confirmed the 2012 slope effect by refitting each Iowa county's trend with and without 2012. Full notes: [`docs/team/ralph_notes.md`](docs/team/ralph_notes.md).

**Connor (drought timing and irrigation)**
- **What:** `wolverine/drought_timing.py`, written to the specification in [`docs/team/CONNOR.md`](docs/team/CONNOR.md).
- **AI use:** Connor used an AI assistant while writing this module. Its output was accepted only after the checks below.
- **How it was checked:** the four checks from that specification were run on the merged code:
  1. one row per county, crop and year (9,984 rows, no duplicates), and `timing` only takes the values none, early, peak or late;
  2. Iowa corn in 2012: all 99 counties are labelled `peak`, as expected for the July 2012 drought;
  3. the worst weekly level over each season matches the master's `max_drought_severity` for 100% of 9,620 county-crop-years, so the level rule is right;
  4. Nebraska counties per irrigation group: corn 59 mostly irrigated and 32 mostly dryland; soybeans 48 and 32.

**Edaijah (landing page and farmer dashboard)**
- **What:** `dashboard_app.py`, the photos in `assets/` and the theme in `.streamlit/config.toml`.
- **How it was checked:** after merging, the welcome, login and dashboard pages were run headlessly with Streamlit's test runner, for both states and both crops, with no errors; the smoke check still prints SMOKE OK.

## Data and credits

The dataset and its documentation come from the hackathon organisers: see [`data/data_dictionary.md`](data/data_dictionary.md) and the original starter README at [`docs/hackathon_README.md`](docs/hackathon_README.md).

- **U.S. Drought Monitor:** The U.S. Drought Monitor is jointly produced by the National Drought Mitigation Center at the University of Nebraska-Lincoln, the United States Department of Agriculture, and the National Oceanic and Atmospheric Administration.
- **USDA NASS:** This product uses the NASS API but is not endorsed or certified by NASS.
- **NOAA ACIS:** Weather data from the Applied Climate Information System (ACIS), NOAA Regional Climate Centers.
- **Soil:** Soil Survey Staff, Natural Resources Conservation Service, United States Department of Agriculture. Soil Survey Geographic (SSURGO) Database, via Soil Data Access.

Code and documentation are under the [MIT License](LICENSE).
