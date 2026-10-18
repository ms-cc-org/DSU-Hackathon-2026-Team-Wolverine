# Drought Category Reality Check

**Team Wolverine** · Data to Harvest Hackathon, Delaware State University, October 17–18, 2026 · Farmer dashboard and evidence app

The U.S. Drought Monitor rates every county each week, from no drought, through D0 (abnormally dry), up to D4 (exceptional drought). A "D3" in Iowa and a "D3" in Nebraska carry the same label. Do they cost a corn or soybean farmer the same share of their yield?

**User:** corn and soybean farmers in Iowa and Nebraska. When the Drought Monitor puts their county in a drought level, they need to decide how much yield loss to plan for: for example, how much grain to sell ahead of harvest, or what to confirm with their crop insurance agent.

**The problem.** No, the same label does not cost the same yield. In 2000–2012, extreme drought (D3) cut Iowa corn yields by 17.4% below trend, but Nebraska corn by only 6.0%. The loss also depends on whether the field is irrigated and on when the drought hits.

**Our solution, and how we know it works.** The farmer dashboard lets a farmer pick their state, county, crop, acres and a drought level, and shows what that drought level cost yields in their state in 2000–2012, in percent and in bushels on their acres, with a plain verdict on whether the estimate held up in 2013–2025. Behind it is a drought level → yield loss table we built on 2000–2012 and then tested on 2013–2025, years it never saw: **82% of the table's cells landed within 4 points** of what actually happened, for corn and for soybeans.

## Minimum deliverable

| Requirement | Where it is |
|---|---|
| A named user and decision | Top of this README: Iowa and Nebraska corn and soybean farmers; how much yield loss to plan for at a given drought level |
| Evidence, checked on years not used to build it | [Results](#results): table built on 2000–2012, checked on 2013–2025 |
| A tool the user can use | The farmer dashboard, `dashboard_app.py` ([How to run it](#how-to-run-it)) |
| Our direction: the table | Evidence app, tab "The answer"; [Results](#results) |
| Our direction: its 2013–2025 check | Evidence app, tab "Did it hold up?"; [Results](#results) |
| Our direction: a one-sentence recommendation | Evidence app, top of tab "The answer"; [Results](#results) |
| A 5-minute pitch with a live demo | Presented on Sunday |

## How to run it

Needs Python 3.11 or newer (3.12 recommended). From the repo root:

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

streamlit run dashboard_app.py     # the farmer dashboard (main app)
```

It opens at http://localhost:8501. Click **Get started**, then sign in with username `demo` and password `demo`. The data ships with the repo; no API keys are needed.

The evidence behind it (the table, its check and the recommendation) is in a second app:

```bash
streamlit run wolverine_app.py --server.port 8502
```

To check that all the parts fit together: `python scripts/smoke_check.py` (prints the backtest score, then `SMOKE OK`).

### What the farmer dashboard shows

| Page | What the farmer sees |
|---|---|
| Welcome | The question (same drought label, same yield loss?), the story in three parts (drought levels, what D3 cost each state, how water and timing explain the gap), and the size of the data |
| Sign in | A demo sign-in. It only gates the demo; it is not real security |
| Dashboard, step 1 | Pick state, county, acres and crop. Nebraska farmers also say whether the field is irrigated or rain-only |
| Step 2 | The answer: the one-sentence recommendation, Iowa and Nebraska at D3 and the gap between them, and the yield change at every drought level for both states (2000–2012) |
| Step 3 | Choose a drought level. The dashboard shows the expected yield change for the farmer's state and crop (for Nebraska, the irrigated or dryland group), typical vs expected bushels per acre, bushels at risk on the farmer's acres, and whether that estimate held up on 2013–2025 |
| Step 4 | Did it hold up? The share of estimates within 4 points, the average miss, and a level-by-level check for the farmer's state. A panel for the data-curious has every cell for both states, the train-vs-test scatter and a switch to the strict trend |
| Step 5 | Why the states differ: peak-season vs early D3 drought, and Nebraska irrigated vs dryland counties |
| Step 6 | Practical steps (insurance, water, the weekly drought map, risky weeks, storage and marketing, the county extension office), each filled in with the farmer's own numbers |
| About the numbers | County-years behind each number, limitations and credits |

The estimates are the evidence app's table: the average yield change at that drought level in 2000–2012 for the farmer's state and crop (for Nebraska, the irrigated or dryland county group). Every estimate is shown with its 2013–2025 check. Bushels use the farmer's county trend yield (its recent reported yield for counties with no trend).

### What the evidence app shows

`wolverine_app.py` has four tabs: **The answer** (the recommendation and the loss table), **Did it hold up? (2013–2025)** (the backtest, cell by cell), **Why it misses** (drought timing and Nebraska irrigation) and **About the data**. The sidebar picks the crop and the trend version; it opens on the master trend.

### Code layout

| File | What it does |
|---|---|
| `dashboard_app.py` | The farmer dashboard (main app) |
| `wolverine_app.py` | The evidence app: the table, its check and the recommendation |
| `wolverine/` | The team's analysis code: shared settings (`contracts.py`), the data panel (`data_prep.py`), the table and backtest (`reality_table.py`), drought timing and irrigation groups (`drought_timing.py`) |
| `scripts/smoke_check.py` | Checks that every module runs and returns the agreed columns |
| `assets/`, `.streamlit/config.toml` | Dashboard photos and the colour theme shared by both apps |
| `notebooks/Ralph.ipynb` | Exploration and checks behind the table |

## Results

The analysis uses **8,708 county-crop-years** (190 counties, Iowa and Nebraska, corn and soybeans, 2000–2025) with a USDA-reported yield and a drought reading. "Yield change" means how far a county's yield fell above or below its own trend line. All numbers below use the master trend, the evidence app's default view.

### The recommendation

> Don't read the drought map the same way in every state: at D3, plan for about a 17% yield loss on Iowa corn but about 6% in Nebraska (much less on irrigated land). These estimates held up on 2013–2025: about 4 in 5 of the table's cells (82%) landed within 4 points.

| Crop | Iowa at D3 | Nebraska at D3 | Gap | Same within 4 points? |
|---|---|---|---|---|
| Corn | −17.4% | −6.0% | 11.4 points | No |
| Soybeans | −15.1% | −9.9% | 5.2 points | No |

### Did the table hold up on 2013–2025?

Each crop's table has 12 cells (2 states × 6 drought levels). A cell is scored only when it has at least 10 county-years in both periods, which leaves 11 per crop (Iowa D4 has only 5 training years). The error is the average miss, weighted by how many 2013–2025 county-years each cell has. Each row matches the evidence app's "Did it hold up?" tab for that crop and trend.

| Crop | Trend version | Cells within 4 points | Average miss |
|---|---|---|---|
| Corn | Master trend (main result) | **82%** (9 of 11) | **1.8 points** |
| Soybeans | Master trend (main result) | **82%** (9 of 11) | **3.1 points** |
| Corn | Strict trend (robustness check) | 55% (6 of 11) | 13.9 points |
| Soybeans | Strict trend (robustness check) | 82% (9 of 11) | 3.0 points |

The biggest miss is **Iowa at D3**: −17.4% in 2000–2012, −3.9% in 2013–2025 for corn (soybeans −15.1% then −3.9%). Most of Iowa's training-era D3 years come from the single 2012 drought, and later D3 seasons were milder.

### Why the two states differ

- **Irrigation.** At D3 in 2000–2012, mostly dryland Nebraska counties lost 17.8% of their corn yield and mostly irrigated counties 0.9% (soybeans 17.6% vs 4.6%). Dryland Nebraska loses about what Iowa does.
- **Timing.** Almost every D3 season had drought in July–August, when corn pollinates and soybeans fill pods. Iowa corn lost 12.5% in those seasons (2000–2025, 248 county-years). Early-only D3 seasons are too rare to quote (9 county-years in Iowa).

## Limitations

- **The dashboard's estimates are state-level averages of past years, not forecasts.** They are the evidence table's 2000–2012 averages, shown next to their 2013–2025 check. They do not vary by county; only the bushels do, through the county's typical yield.
- **2012 dominates the training years.** 61% of Iowa corn's D3-and-worse training years (51% for soybeans, 29% in Nebraska) are from 2012.
- **The strict trend is unreliable for Iowa corn.** On the strict trend, Iowa corn scores worst (55% of cells within 4 points) because the 2012 drought flattens its 2000–2012 trend line (median slope 0.64 bu/ac/yr with 2012, 2.02 without), so 2013–2025 looks better than it was. Soybeans are not affected.
- **The master trend sees the test years.** It is fitted on all 26 years, so its scores are somewhat flattering. That is why we also report the strict trend.
- **Drought level is the season's worst week.** One bad week counts the same as a whole bad season.
- **Thin cells.** Iowa has only 5 training years at D4 for each crop. Don't quote Iowa D4 numbers.
- **Irrigation groups are coarse.** Each Nebraska county gets one irrigated share, averaged over 2000–2018 (the last year of irrigation data for corn and soybeans), split at 50%. Iowa counties are not split.
- **Timing is known only at the end of the season.** "Peak" means severe drought (D2 or worse) reached the county in July–August; "early" means only before July. It explains losses after the fact rather than forecasting them.
- **Yields come from USDA surveys.** Small counties drop out in some years.

## Team

| Name | GitHub | Role |
|---|---|---|
| Tolu Adeola | [@lod23](https://github.com/lod23) | Shared code skeleton, evidence app, integration and merges, README |
| Ralph Reyes | [@RRR-Reyes](https://github.com/RRR-Reyes) | Analysis panel, strict trend, reality table and backtest |
| Connor Little | [@GAMEMONKEI](https://github.com/GAMEMONKEI) | Drought timing and irrigation groups; problem statement |
| Edaijah Rodriguez | [@daejadoll](https://github.com/daejadoll) | Farmer dashboard, login and welcome pages, story layout, colour palette, drought level legend |

## AI disclosure

We used AI tools as described below and checked every number against the data before relying on it.

**Tolu (evidence app and integration)**
- **Tool:** Claude Code (Claude Opus 5.5).
- **What for:** the shared module skeleton (`contracts.py` and function stubs); `wolverine_app.py` and `scripts/smoke_check.py`; merging the team's branches and fitting the app to their outputs; testing the merged dashboard; drafting this README.
- **How it was checked:** the apps were run headlessly with Streamlit's test runner at each stage, for both crops and both trends, with no errors. Every README number was recomputed from the merged code and matched against Ralph's notes (both crops combined on the master trend: 82% within 4 points, 2.4 points; Iowa corn D3 −17.4 / −3.9).

**Ralph (data prep and reality table)**
- **Tool:** Claude Code (Claude Opus 5.5).
- **What for:** turning the task spec's pseudo-code into working pandas; writing the check script; finding the cause of the strict-trend bias in test years; drafting his notes.
- **How it was checked:** the Iowa corn D3 cell reproduces the planned values (train −17.4, test −3.9); Polk County 2012 and the per-county training means checked by hand; the 2012 slope effect confirmed by refitting each Iowa county's trend with and without 2012. Full notes: [`docs/team/ralph_notes.md`](docs/team/ralph_notes.md).

**Connor (drought timing and irrigation)**
- **What:** `wolverine/drought_timing.py`, written to the specification in [`docs/team/CONNOR.md`](docs/team/CONNOR.md). Connor used an AI assistant while writing it.
- **How it was checked:** the specification's four checks were run on the merged code: one row per county, crop and year (9,984 rows, no duplicates) with only valid timing labels; all 99 Iowa counties labelled `peak` for corn in 2012; the season's worst weekly level matches the master dataset for 100% of 9,620 county-crop-years; Nebraska irrigation groups of 59 irrigated and 32 dryland counties for corn, 48 and 32 for soybeans.

**Edaijah (farmer dashboard)**
- **Tool:** Claude (Claude Sonnet 5.5), credited as co-author on her commits.
- **What for:** building the login page and the farmer drought yield dashboard; adding the welcome page, colour palette theme, crop icons and drought level legend; redesigning the dashboard into a story layout with farm photography; then rebuilding it on the team's analysis (the reality table, its 2013–2025 check, drought timing and irrigation) in plain language for farmers, and renaming it Drought Category Reality Check.
- **How it was checked:** *TODO (Edaijah): how you checked the dashboard's numbers and pages.* After merging, Tolu ran the welcome, sign-in and dashboard pages headlessly for both states and both crops with no errors.

## Data and credits

The dataset and its documentation come from the hackathon organisers: see [`data/data_dictionary.md`](data/data_dictionary.md) and the original starter README at [`docs/hackathon_README.md`](docs/hackathon_README.md).

- **U.S. Drought Monitor:** The U.S. Drought Monitor is jointly produced by the National Drought Mitigation Center at the University of Nebraska-Lincoln, the United States Department of Agriculture, and the National Oceanic and Atmospheric Administration.
- **USDA NASS:** This product uses the NASS API but is not endorsed or certified by NASS.
- **NOAA ACIS:** Weather data from the Applied Climate Information System (ACIS), NOAA Regional Climate Centers.
- **Soil:** Soil Survey Staff, Natural Resources Conservation Service, United States Department of Agriculture. Soil Survey Geographic (SSURGO) Database, via Soil Data Access.

**Images in the dashboard**

| Image | Source and licence |
|---|---|
| `assets/hero.jpg` (welcome page), `assets/corn.jpg`, `assets/soybeans.jpg` | USDA and NRCS, public domain, via Wikimedia Commons, as stated in the dashboard. *TODO: the source page for each photo.* |
| `assets/drought.jpg` (drought-damaged corn) | USDA photo, public domain, as captioned in the dashboard. *TODO: the source page.* |
| Corn and soybean icons | Drawn by the team as SVG in `dashboard_app.py`; covered by this repo's MIT licence |
| Fonts (Fraunces, Source Sans 3) | Loaded from Google Fonts; SIL Open Font License |

Code and documentation are under the [MIT License](LICENSE).
