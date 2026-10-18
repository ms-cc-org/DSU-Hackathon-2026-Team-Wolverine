# DroughtLens

**See Drought Coming. Plan Ahead.**

**Team Wolverine** · Data to Harvest Hackathon, Delaware State University, October 17–18, 2026 · Direction: Drought Category Reality Check

The U.S. Drought Monitor rates every county each week, from no drought, through D0 (abnormally dry), up to D4 (exceptional drought). A "D3" in Iowa and a "D3" in Nebraska carry the same label. Do they cost a corn or soybean farmer the same share of their yield?

**User:** corn and soybean farmers in Iowa and Nebraska. When the Drought Monitor puts their county in a drought level, they need to decide how much yield loss to plan for: for example, how much grain to sell ahead of harvest, or what to confirm with their crop insurance agent.

**The problem.** No, the same label does not cost the same yield. In 2000–2012, extreme drought (D3) cut Iowa corn yields by 17.4% below trend, but Nebraska corn by only 6.0%. The loss also depends on whether the field is irrigated and on when the drought hits.

**Our solution, and how we know it works.** DroughtLens, our farmer app, lets a farmer pick their state, county, crop, acres and a drought level, and shows what that drought level cost yields in their state in 2000–2012, in percent and in tons (corn) or bushels (soybeans) on their acres, with a plain verdict on whether the estimate held up in 2013–2025. Behind it is a drought level → yield loss table we built on 2000–2012 and then tested on 2013–2025, years it never saw: **82% of the table's cells landed within 4 points** of what actually happened, for corn and for soybeans.

## Minimum deliverable

| Requirement | Where it is |
|---|---|
| A named user and decision | Top of this README: Iowa and Nebraska corn and soybean farmers; how much yield loss to plan for at a given drought level |
| Evidence, checked on years not used to build it | [Results](#results): table built on 2000–2012, checked on 2013–2025 |
| A tool the user can use | DroughtLens, `dashboard_app.py` ([How to run it](#how-to-run-it)) |
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

streamlit run dashboard_app.py     # DroughtLens, the farmer app (main app)
```

It opens at http://localhost:8501. Click **Explore My Drought Outlook**, then sign in with username `demo` and password `demo`. The data ships with the repo; no API keys are needed.

The evidence behind it (the table, its check and the recommendation) is in a second app:

```bash
streamlit run wolverine_app.py --server.port 8502
```

To check that all the parts fit together: `python scripts/smoke_check.py` (prints the backtest score, then `SMOKE OK`).

### What DroughtLens shows

DroughtLens covers Nebraska and Iowa only (192 counties). It looks back so a farmer can look ahead: it shows what past droughts cost and whether that held up. **It has no live conditions, no forecast and no prediction model**; the latest drought reading in the data is December 30, 2025, and every page says so.

| Page | What the farmer sees |
|---|---|
| Overview | The hero ("See Drought Coming. Plan Ahead."), what DroughtLens is and is not, and "Every Crop Has Different Needs": corn and soybean sections with growing season, drought sensitivity, historical context and what the data supports considering, plus how irrigation changes the answer |
| Sign in | A demo sign-in. It only gates the demo; it is not real security |
| Drought Outlook, Outlook tab | State, county, crop and planning period (early, peak, late, full season). A table that says which kinds of information are available (historical yes; current conditions, forecast and model prediction no). A county map of what drought has cost yield, the county's weeks in D2 or worse by year, key contributing factors, and the Drought Category Reality Check estimate with its 2013–2025 verdict |
| Drought Outlook, History tab | Same label, different cost; did it hold up; the county's rainfall, temperature, weekly drought, satellite greenness, soil and observed yield; why the states differ (timing and irrigation); and six questions the data answers, each with a hover button explaining how the answer was worked out |
| My Fields | Onboarding (state, county, field name, crops, optional acres, planting date, growing stage, irrigation) that refuses any location outside Nebraska and Iowa, and a dashboard that answers: what drought conditions may affect my farm, why does the system estimate this, and what should I do next |
| Farm Plan | A preparedness plan generated from the data in six sections. Every line is tagged **Data** or **General guidance**. The farmer can edit it, save it, come back to it, and download it as Markdown or printable HTML |
| Agricultural Advisor | A chat that answers from DroughtLens's data using fixed rules (**not a language model**), keeps data-backed findings apart from general guidance, and says so when the data cannot answer |
| Data sources, Methodology, Agricultural guidance, Privacy, Support | Linked from every page: every dataset with its rows and coverage, how the estimates are built and checked, what counts as guidance, what is stored and where, and how to report a problem |

The estimates are the evidence app's table: the average yield change at that drought level in 2000–2012 for the farmer's state and crop (for Nebraska, the irrigated or dryland county group). Every estimate is shown with its 2013–2025 check. Yield amounts use the farmer's county trend yield (its recent reported yield for counties with no trend). Corn is shown in tons per acre (a bushel of shelled corn is 56 pounds and a ton is 2,000 pounds, so tons = bushels × 0.028); soybeans stay in bushels per acre.

DroughtLens uses every dataset in `data/`: the master dataset, weekly drought, daily weather, NASS records, soil, MODIS greenness, irrigation and the county boundaries. Fields and plans a farmer saves are kept in `app_data/` on the server (git-ignored).

### What the evidence app shows

`wolverine_app.py` has four tabs: **The answer** (the recommendation and the loss table), **Did it hold up? (2013–2025)** (the backtest, cell by cell), **Why it misses** (drought timing and Nebraska irrigation) and **About the data**. The sidebar picks the crop and the trend version; it opens on the master trend.

### Code layout

| File | What it does |
|---|---|
| `dashboard_app.py` | DroughtLens, the farmer app (main app): page setup, navigation and routing |
| `droughtlens/` | The farmer app's code: `theme.py` (design tokens and styles), `logo.py` (the logo as SVG), `data.py` (loaders for every dataset), `reality.py` (the reality-check tables, units and the six questions), `insights.py` (county facts), `places.py` (Nebraska and Iowa location check), `farm.py` (fields, plans, export), `advisor.py` (the Advisor's rules) and `views/` (one file per page) |
| `wolverine_app.py` | The evidence app: the table, its check and the recommendation |
| `wolverine/` | The team's analysis code: shared settings (`contracts.py`), the data panel (`data_prep.py`), the table and backtest (`reality_table.py`), drought timing and irrigation groups (`drought_timing.py`) |
| `scripts/smoke_check.py` | Checks that every module runs and returns the agreed columns |
| `assets/`, `.streamlit/config.toml` | Photos, the DroughtLens logo files (`assets/logo/`, made by `scripts/make_logo_assets.py`) and the light theme shared by both apps |
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

- **DroughtLens's estimates are state-level averages of past years, not forecasts.** They are the evidence table's 2000–2012 averages, shown next to their 2013–2025 check. They do not vary by county; only the tons or bushels do, through the county's typical yield.
- **No live conditions, forecast or prediction.** The data ends December 30, 2025. County drought frequencies describe the past and are not probabilities for next season.
- **The Advisor is not a language model.** It assembles answers from the same tables by fixed rules, so it can only say what the data supports.
- **The growing stage maps to a planning period by our assumption** (stages up to vegetative growth to early season, flowering and grain fill to peak season, harvest to late season). Soil figures are water capacity, not measured soil moisture.
- **Saved fields and plans live in a file on the server**, and the sign-in is a demo.
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
| Edaijah Rodriguez | [@daejadoll](https://github.com/daejadoll) | DroughtLens: the farmer app, its logo and design, login and overview pages, county outlook and history, field onboarding, farm plans and the Advisor |

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
- **What for:** building the login page and the farmer drought yield dashboard; adding the welcome page, colour palette theme, crop icons and drought level legend; redesigning the dashboard into a story layout with farm photography; then rebuilding it on the team's analysis (the reality table, its 2013–2025 check, drought timing and irrigation) in plain language for farmers, and showing corn in tons per acre and adding the six data-dictionary questions with hover explanations; then building DroughtLens: the logo and design system, county map, field onboarding with the Nebraska and Iowa check, farm plans, the data-grounded Advisor and the transparency pages.
- **How it was checked:** *TODO (Edaijah): add how you checked the app's numbers and pages.* The assistant ran every page end to end with Streamlit's test runner (sign-in and the sign-in gate, both states, both crops, every planning period and drought level, a county with no reported yields, an unsupported and an ambiguous location, saving a field, generating, editing, saving and reopening a plan, every Advisor question, every transparency page, and logging out), and the README's headline numbers (17.4%, 6.0%, 82%, 1.8 points) match the app.

## Data and credits

The dataset and its documentation come from the hackathon organisers: see [`data/data_dictionary.md`](data/data_dictionary.md) and the original starter README at [`docs/hackathon_README.md`](docs/hackathon_README.md).

- **U.S. Drought Monitor:** The U.S. Drought Monitor is jointly produced by the National Drought Mitigation Center at the University of Nebraska-Lincoln, the United States Department of Agriculture, and the National Oceanic and Atmospheric Administration.
- **USDA NASS:** This product uses the NASS API but is not endorsed or certified by NASS.
- **NOAA ACIS:** Weather data from the Applied Climate Information System (ACIS), NOAA Regional Climate Centers.
- **Soil:** Soil Survey Staff, Natural Resources Conservation Service, United States Department of Agriculture. Soil Survey Geographic (SSURGO) Database, via Soil Data Access.

**Images in the dashboard**

| Image | Source and licence |
|---|---|
| `assets/aerial.jpg` (Overview hero) | [NRCSIA99087 – Iowa (2875), NRCS Photo Gallery](https://commons.wikimedia.org/wiki/File:NRCSIA99087_-_Iowa_(2875)(NRCS_Photo_Gallery).jpg). USDA NRCS, public domain, via Wikimedia Commons |
| `assets/hero.jpg` (sign-in page) | [Soybean Field with Healthy Soil](https://commons.wikimedia.org/wiki/File:Soybean_Field_with_Healthy_Soil_(9316804120).jpg). USDA, public domain, via Wikimedia Commons |
| `assets/corn.jpg` | [Corn in Residue with Healthy Soil](https://commons.wikimedia.org/wiki/File:Corn_in_Residue_with_Healthy_Soil_(9314025147).jpg). USDA, public domain, via Wikimedia Commons |
| `assets/soybeans.jpg` | [Soybeans in no-till field](https://commons.wikimedia.org/wiki/File:Soybeans_in_no-till_field.jpg). USDA NRCS (Lynn Betts), public domain, via Wikimedia Commons |
| `assets/drought.jpg` | [Corn shows the effect of drought](https://commons.wikimedia.org/wiki/File:Corn_shows_the_effect_of_drought.jpg). USDA, public domain, via Wikimedia Commons. Taken in Texas |
| `assets/irrigation.jpg` | [Center-pivot irrigation](https://commons.wikimedia.org/wiki/File:Center-pivot_irrigation.jpg). USDA, public domain, via Wikimedia Commons. Location not stated in the file |
| DroughtLens logo, corn and soybean icons | Drawn by the team as SVG (`droughtlens/logo.py`, `droughtlens/theme.py`) with PNG icons in `assets/logo/`; covered by this repo's MIT licence |
| Fonts (Lora, DM Sans) | Loaded from Google Fonts; SIL Open Font License |

Code and documentation are under the [MIT License](LICENSE).
