# Tolu — Scaffold, Streamlit app, integration

Branch: `tolu`. You own: `wolverine/__init__.py`, `wolverine/contracts.py`, `wolverine_app.py`, `scripts/smoke_check.py`, `README.md`, `docs/team/*` plan files.
You never edit `wolverine/data_prep.py`, `wolverine/reality_table.py` or `wolverine/drought_timing.py` after step 0.

## Step 0 — first 20 minutes, push to `main` before anyone branches

Create:

```
wolverine/__init__.py        empty
wolverine/contracts.py       copy from PLAN.md section 3
wolverine/data_prep.py       stub for Ralph
wolverine/reality_table.py   stub for Ralph
wolverine/drought_timing.py  stub for Connor
docs/team/PLAN.md, TOLU.md, RALPH.md, CONNOR.md
```

Stubs only hold the signatures, so everyone can import from the start:

```python
# wolverine/data_prep.py
def build_panel(): raise NotImplementedError
def add_strict_anomaly(panel): raise NotImplementedError
def coverage_report(panel): raise NotImplementedError

# wolverine/reality_table.py
def build_table(panel, years, anom_col="yield_anomaly_pct", extra_by=None): raise NotImplementedError
def backtest(panel, anom_col="yield_anomaly_pct", extra_by=None): raise NotImplementedError
def score(check): raise NotImplementedError
def same_meaning(table, level, crop): raise NotImplementedError
def recommendation(check, table): raise NotImplementedError

# wolverine/drought_timing.py
def drought_timing(): raise NotImplementedError
def irrigation_groups(): raise NotImplementedError
```

Push, then tell Ralph and Connor to branch.

## `wolverine_app.py` (starter `app.py` stays untouched)

Run from repo root: `streamlit run wolverine_app.py`.

```python
import streamlit as st, plotly.express as px
from wolverine import data_prep, reality_table as rt, drought_timing as dt
from wolverine.contracts import *

st.set_page_config(title="Drought Category Reality Check", layout="wide")

@st.cache_data
def load_all():
    panel = data_prep.add_strict_anomaly(data_prep.build_panel())
    try:
        panel = panel.merge(dt.drought_timing(),   on=["fips","crop","year"], how="left")
        panel = panel.merge(dt.irrigation_groups(), on=["fips","crop"],        how="left")
    except NotImplementedError:
        pass                                   # Connor's part not merged yet
    return panel

panel = load_all()

sidebar:
    crop = radio(CROPS)
    version = radio(["Strict trend (2000–2012 only)", "Master trend (all years)"])
    anom = STRICT_ANOM if strict else "yield_anomaly_pct"
    view = panel[panel.crop == crop]

Tab 1 "The answer"
    table = rt.build_table(view, TRAIN_YEARS, anom)
    check = rt.backtest(view, anom)
    big text: rt.recommendation(check, table)
    d3 = rt.same_meaning(table, level=4, crop=crop)
    3 metrics: Iowa D3 loss, Nebraska D3 loss, gap
    grouped bar: x = level (mapped through LEVEL_LABELS), y = mean_loss, color = state_alpha

Tab 2 "Did it hold up? (2013–2025)"
    s = rt.score(check)
    metrics: % cells within 4 pts, weighted mean error
    dataframe of check, rows green if within_tol, red if not, grey if n < MIN_CELL_N
    scatter: x = train_mean, y = test_mean, color = state; add y = x line and ±4 band

Tab 3 "Why it misses"
    if "timing" in view:
        t = rt.build_table(view, TRAIN_YEARS + TEST_YEARS span, anom, extra_by=["timing"])
        bar: loss at D3 for peak vs early drought, per state
        caption: years and counties covered
    if "irrig_group" in view:
        ne = view[view.state_alpha == "NE"]
        t = rt.build_table(ne, TRAIN_YEARS, anom, extra_by=["irrig_group"])
        bar: loss by level for mostly irrigated vs mostly dryland
        caption: irrigation data ends 2018, one average share per county

Tab 4 "About the data"
    data_prep.coverage_report(view)
    limitations + source credits (copy from README "Credits")
```

Every call that hits a stub: wrap in `try/except NotImplementedError: st.info("Coming soon")` so the app runs at every stage.

## `scripts/smoke_check.py` — run after every merge into `main`

```python
import sys; sys.path.insert(0, ".")
panel = add_strict_anomaly(build_panel());   assert len(panel) > 0 and STRICT_ANOM in panel
check = backtest(panel);                     assert set(CHECK_COLS) <= set(check.columns)
print(score(check))
t = drought_timing();                        assert set(TIMING_COLS) <= set(t.columns)
assert t.timing.isin(TIMING_VALUES).all()
i = irrigation_groups();                     assert set(IRRIG_COLS) <= set(i.columns)
print("SMOKE OK")
```

## Merging
1. Ralph's PR first (Connor's app tabs need nothing from Ralph, but the app's Tab 1–2 do).
2. Then Connor's PR.
3. `python scripts/smoke_check.py` + `streamlit run wolverine_app.py` after each.

## README (Sunday morning)
Sections: what the tool does (user, decision), how to run (venv, `pip install -r requirements.txt`, `streamlit run wolverine_app.py`), results (score + recommendation), limitations, team, **AI disclosure** (assemble from `ralph_notes.md`, `connor_notes.md` and your own: tools used, for what, which parts, how verified).

## Submission
Submission form with team name, all members and GitHub usernames, repo URL, full 40-character SHA of the final commit on `main`.
