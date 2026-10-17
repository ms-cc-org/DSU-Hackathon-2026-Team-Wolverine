# Team Wolverine — Build Plan: Drought Category Reality Check

Shared overview. Each member's pseudocode is in their own file:
`docs/team/TOLU.md`, `docs/team/RALPH.md`, `docs/team/CONNOR.md`.

## 1. What we are building

**The state drought task force** needs to decide **whether a drought level such as D3 should mean the same thing in Iowa and Nebraska**. Our tool shows them **a drought level → yield-loss table built on 2000–2012, how well it predicted 2013–2025, and why it misses where it misses (drought timing and irrigation).**

> Fix before checkpoint 1: our PDF says the user is "any corn farmer". The README direction names the **state drought task force**, and the minimum covers **corn AND soybeans** in Iowa and Nebraska.

### Minimum deliverable (all required)
1. Table: mean `yield_anomaly_pct` by state × crop × drought level, built on **2000–2012**.
2. Its check on **2013–2025** (target: within about 4 points).
3. A one-sentence recommendation.
4. A simple Streamlit tool showing all of it.

### Baseline already run (master's `yield_anomaly_pct`, reported yields, IA + NE)

`max_drought_severity` is offset by 1: 0 none, 1 D0, 2 D1, 3 D2, **4 D3**, 5 D4. Use the master value in code; show D-labels only in the app.

| Worst level (master value) | IA corn train → test | NE corn train → test | IA soy train → test | NE soy train → test |
|---|---|---|---|---|
| D2 (3) | −3.0 → −2.2 | −5.0 → −0.7 | −1.1 → −2.8 | −2.6 → −1.1 |
| **D3 (4)** | **−17.4 → −3.9** | −6.0 → −4.6 | **−15.1 → −3.9** | −9.9 → −6.2 |
| D4 (5) | −25.6 → −8.2 (5 train rows) | −9.4 → −12.1 | −19.2 → −11.6 (5) | −13.1 → −16.3 |

75% of cells land within 4 points. The big miss is Iowa at D3: −17 in training, −4 in testing, because training is dominated by 2012's July drought (pollination). Our story: **the same D-label costs different amounts depending on when it hits and whether the field is irrigated.**

Caveat: `yield_anomaly_pct` uses a trend fitted on all 26 years, so that test isn't strict. Ralph's `add_strict_anomaly` fixes it.

## 2. File ownership — nobody touches another person's file

| Member | Branch | Owns (and ONLY these) |
|---|---|---|
| **Tolu** (owner, integrator) | `tolu` | `wolverine/__init__.py`, `wolverine/contracts.py`, `wolverine_app.py`, `scripts/smoke_check.py`, `README.md`, `docs/team/*` plan files |
| **Ralph** (RRR-Reyes) | `ralph` | `wolverine/data_prep.py`, `wolverine/reality_table.py`, `docs/team/ralph_notes.md`, `notebooks/ralph_scratch.ipynb` |
| **Connor** (GAMEMONKEI) | `connor` | `wolverine/drought_timing.py`, `docs/team/connor_notes.md`, `notebooks/connor_scratch.ipynb` |

**Read-only for everyone:** `src/`, `data/`, `requirements.txt`, the starter `app.py`. Everything we need is already in `requirements.txt`.

**Why it can't conflict**
- Each `.py` file has exactly one owner.
- Every analysis function takes a DataFrame in and returns a DataFrame out. Ralph's and Connor's modules never import each other. Only `wolverine_app.py` (Tolu) wires them together.
- Column names live in `contracts.py`, written once by Tolu before anyone branches. Changes to it go through the group chat, and Tolu makes them.
- Don't name files `test.py` or `notes.py`: `.gitignore` ignores them.
- Clear notebook outputs before committing.

## 3. Shared contract — `wolverine/contracts.py` (Tolu writes this in step 0)

```python
STATES = ["IA", "NE"]
CROPS = ["CORN", "SOYBEANS"]
TRAIN_YEARS = (2000, 2012)
TEST_YEARS  = (2013, 2025)
TOLERANCE_PTS = 4.0
MIN_CELL_N = 10

LEVEL_LABELS = {0: "None", 1: "D0", 2: "D1", 3: "D2", 4: "D3", 5: "D4"}

PANEL_COLS = ["fips", "county_name", "state_alpha", "crop", "year",
              "yield_per_acre", "yield_anomaly_pct", "max_drought_severity",
              "weeks_in_d2_plus", "mean_dsci", "aws_100cm_mm"]
STRICT_ANOM = "anom_strict"
TABLE_COLS  = ["state_alpha", "crop", "level", "mean_loss", "n"]
CHECK_COLS  = ["state_alpha", "crop", "level", "train_mean", "test_mean",
               "train_n", "test_n", "abs_error", "within_tol"]
TIMING_COLS = ["fips", "crop", "year", "peak_level", "timing"]
IRRIG_COLS  = ["fips", "crop", "irrig_group"]
TIMING_VALUES = ["none", "early", "peak", "late"]
```

## 4. Git rules
1. Wait for Tolu's step-0 push, then: `git checkout main && git pull && git checkout -b <yourname>`.
2. Commit only your own files, on your own branch.
3. Before a PR: `git fetch origin && git merge origin/main`. Files don't overlap, so this is always clean.
4. Only Tolu merges into `main`, and runs `python scripts/smoke_check.py` after each merge.

## 5. Timeline (Sat Oct 17 → submission Sun noon)

| When | Who | What |
|---|---|---|
| Sat ~3:45 PM | Tolu | Step-0 scaffold pushed to `main`; checkpoint 1 statement fixed |
| Sat 4–6 PM | Ralph, Connor | First working version on own branch; open PR |
| Sat ~6 PM | Tolu | Merge **Ralph → Connor**, smoke check after each |
| Sat evening | All | **Checkpoint 2:** app shows Tab 1 + Tab 2 with real numbers |
| Sat night | All | Polish; Tolu wires Tab 3; Ralph and Connor write their notes files (what, how verified, AI disclosure) |
| Sun ~9 AM | Tolu | Final merges, README (run steps, results, AI disclosure), freeze |
| Sun ~10 AM | All | Rehearse: each person presents their own piece |
| Sun before noon | Tolu | Submit the form with the full 40-character commit SHA |

## 6. Pitch skeleton
1. **User:** Iowa/Nebraska state drought task force.
2. **Decision:** should D3 trigger the same response in both states?
3. **Evidence:** 2000–2012 table of yield loss by level, state and crop; drought timing from the weekly maps; Nebraska irrigation share.
4. **How we know:** checked on 2013–2025 with a trend refit on training years only; X% of cells within 4 points; misses explained by 2012's peak-season drought.
