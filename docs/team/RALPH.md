# Ralph — Analysis panel + Reality table

Branch: `ralph`. You own: `wolverine/data_prep.py`, `wolverine/reality_table.py`, `docs/team/ralph_notes.md`, `notebooks/ralph_scratch.ipynb`.
Don't edit any other file. Don't import `drought_timing`. Column names come from `wolverine/contracts.py`.

Start with `data_prep.py` (Tolu's app needs it first), then `reality_table.py`.

## Part 1 — `wolverine/data_prep.py`

```python
from src.data_loader import load_master
from wolverine.contracts import STATES, CROPS, TRAIN_YEARS, PANEL_COLS, STRICT_ANOM

def build_panel():
    df = load_master()                                  # fips already a string
    df = df[df.state_alpha.isin(STATES) & df.crop.isin(CROPS)]
    df = df[df.yield_status == "reported"]
    df = df[df.max_drought_severity.notna()]
    return df[PANEL_COLS].reset_index(drop=True)

def add_strict_anomaly(panel):
    # Refit each county-crop trend on TRAINING years only, so test years never leak in.
    panel = panel.copy(); panel[STRICT_ANOM] = NaN
    for (fips, crop), g in panel.groupby(["fips", "crop"]):
        train = g[g.year.between(*TRAIN_YEARS)]
        if len(train) < 10: continue                    # trend too unstable, leave NaN
        b, a = numpy.polyfit(train.year, train.yield_per_acre, 1)
        fitted = a + b * g.year                         # extends into 2013–2025
        panel.loc[g.index, STRICT_ANOM] = (g.yield_per_acre - fitted) / fitted * 100
    return panel

def coverage_report(panel):
    period = where(panel.year <= TRAIN_YEARS[1], "train", "test")
    return panel.groupby(["state_alpha", "crop", "max_drought_severity", period]).size()
           .unstack(period).fillna(0)
```

Check (write results in `ralph_notes.md`):
- Polk County IA (`19153`) corn 2012 is in the panel and its `anom_strict` is negative.
- Per county, the mean of `anom_strict` over 2000–2012 is about 0.

## Part 2 — `wolverine/reality_table.py`

Every function takes a panel; nothing reads files.

```python
from wolverine.contracts import TRAIN_YEARS, TEST_YEARS, TOLERANCE_PTS, MIN_CELL_N, LEVEL_LABELS

def build_table(panel, years, anom_col="yield_anomaly_pct", extra_by=None):
    rows = panel[panel.year.between(*years) & panel[anom_col].notna()]
    by = ["state_alpha", "crop", "max_drought_severity"] + (extra_by or [])
    t = rows.groupby(by)[anom_col].agg(mean_loss="mean", n="size").reset_index()
    return t.rename(columns={"max_drought_severity": "level"})

def backtest(panel, anom_col="yield_anomaly_pct", extra_by=None):
    keys = ["state_alpha", "crop", "level"] + (extra_by or [])
    tr = build_table(panel, TRAIN_YEARS, anom_col, extra_by).rename(mean_loss="train_mean", n="train_n")
    te = build_table(panel, TEST_YEARS,  anom_col, extra_by).rename(mean_loss="test_mean",  n="test_n")
    m = tr.merge(te, on=keys, how="outer")
    m["abs_error"]  = (m.test_mean - m.train_mean).abs()
    m["within_tol"] = m.abs_error <= TOLERANCE_PTS
    m["enough_rows"] = (m.train_n >= MIN_CELL_N) & (m.test_n >= MIN_CELL_N)
    return m

def score(check):
    ok = check[check.enough_rows]
    return {
        "share_within_tol": ok.within_tol.mean(),
        "weighted_mae": (ok.abs_error * ok.test_n).sum() / ok.test_n.sum(),
        "cells_scored": len(ok),
        "worst_cells": ok.nlargest(3, "abs_error"),
    }

def same_meaning(table, level, crop):
    ia = table row where state_alpha=="IA", crop==crop, level==level  -> mean_loss
    ne = same for "NE"
    gap = ia - ne
    return {"ia": ia, "ne": ne, "gap": gap, "same": abs(gap) <= TOLERANCE_PTS}

def recommendation(check, table):
    crop = table.crop.iloc[0]
    d = same_meaning(table, level=4, crop=crop)        # 4 = D3
    s = score(check)
    if d["same"]:
        return f"D3 cost {crop.lower()} about the same in Iowa ({d['ia']:.1f}%) and Nebraska ({d['ne']:.1f}%), so one trigger can serve both."
    return (f"D3 cost Iowa {crop.lower()} {d['ia']:.1f}% vs Nebraska {d['ne']:.1f}% in 2000–2012: "
            f"use state-specific triggers, and trust only the table cells that held up in 2013–2025 "
            f"({s['share_within_tol']:.0%} did).")
```

Check: with `anom_col="yield_anomaly_pct"`, Iowa corn level 4 must give train −17.4, test −3.9 (PLAN.md table). If it does, your code is right. Then record the same numbers with `anom_strict`.

## Notes file (`docs/team/ralph_notes.md`, Saturday night)
What you built, the numbers from both checks, limitations (thin D4 cells, 2012 dominates training), and your AI disclosure (tool, what for, how you verified).

## Pitch part (about 1 minute)
"How we know it works": the 2013–2025 check, % of cells within 4 points, and the Iowa D3 miss.
