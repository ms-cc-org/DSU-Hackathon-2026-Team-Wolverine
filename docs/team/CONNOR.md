# Connor — Drought timing + Nebraska irrigation split

Branch: `connor`. You own: `wolverine/drought_timing.py`, `docs/team/connor_notes.md`, `notebooks/connor_scratch.ipynb`.
Don't edit any other file. Don't import `data_prep` or `reality_table`. Column names come from `wolverine/contracts.py`.

Your job explains **why** the table misses: the same D3 label hurts more when it lands in July–August (pollination, pod fill), and less on irrigated land.

## Data facts you need
- Weekly panel: `load_weekly_drought()` → `fips, map_date, county_name, state_alpha, none_pct, D0, D1, D2, D3, D4, dsci`.
- D0–D4 are **non-overlapping** percentages (they sum to 100 with `none_pct`). "D2 or worse" = `D2 + D3 + D4`.
- Irrigation: `load_irrigation()` → `fips, state_alpha, crop, year, irrigated_share, yield_irrigated, yield_non_irrigated`. Nebraska corn and soybeans only cover **2000–2018**.

## `wolverine/drought_timing.py`

```python
import numpy as np, pandas as pd
from src.data_loader import load_weekly_drought, load_irrigation
from wolverine.contracts import TIMING_COLS, IRRIG_COLS

SEASON = {"CORN": (5, 1, 9, 30), "SOYBEANS": (5, 1, 10, 31)}   # month/day start, end
PEAK = (7, 1, 8, 31)                                            # Jul 1 – Aug 31

def week_levels(d):
    # Same 1% rule and 0–5 scale as the master's max_drought_severity
    d2p = d.D2 + d.D3 + d.D4
    conds = [d.D4 > 1,
             d.D3 + d.D4 > 1,
             d2p > 1,
             d.D1 + d2p > 1,
             d.D0 + d.D1 + d2p > 1]
    return np.select(conds, [5, 4, 3, 2, 1], default=0)          # vectorised, no loop

def in_window(dates, m1, d1, m2, d2):
    md = dates.dt.month * 100 + dates.dt.day
    return (md >= m1 * 100 + d1) & (md <= m2 * 100 + d2)

def drought_timing():
    d = load_weekly_drought()
    d = d[d.state_alpha.isin(["IA", "NE"])].copy()
    d["level"] = week_levels(d)
    d["year"] = d.map_date.dt.year
    d["peak_week"] = in_window(d.map_date, *PEAK)
    out = []
    for crop, win in SEASON.items():
        s = d[in_window(d.map_date, *win)].copy()
        s["d2p"] = s.level >= 3
        g = s.groupby(["fips", "year"])
        res = pd.DataFrame({
            "peak_level": g.apply(lambda x: x.loc[x.peak_week, "level"].max()),
            "any_d2p":    g.d2p.any(),
            "peak_d2p":   g.apply(lambda x: (x.d2p & x.peak_week).any()),
            "early_d2p":  g.apply(lambda x: (x.d2p & (x.map_date.dt.month < 7)).any()),
        }).reset_index()
        res["timing"] = np.select(
            [~res.any_d2p, res.peak_d2p, res.early_d2p],
            ["none",       "peak",       "early"],
            default="late")
        res["crop"] = crop
        out.append(res)
    return pd.concat(out)[TIMING_COLS]

def irrigation_groups():
    i = load_irrigation()
    i = i[(i.state_alpha == "NE") & i.crop.isin(["CORN", "SOYBEANS"])]
    share = i.groupby(["fips", "crop"]).irrigated_share.mean().reset_index()
    share["irrig_group"] = np.where(share.irrigated_share >= 0.5,
                                    "mostly irrigated", "mostly dryland")
    return share[IRRIG_COLS]
```

## Checks (write results in `docs/team/connor_notes.md`)
1. Output has exactly one row per `fips, crop, year`, and `timing` only takes values `none / early / peak / late`.
2. Iowa 2012 corn: most counties should be `peak`. If not, check the date windows.
3. Recompute `max(level)` over the full season and compare to the master's `max_drought_severity` for a few counties. They should match; if they do, your level rule is right.
4. Count Nebraska counties per `irrig_group` for corn and for soybeans.

To try the splits yourself before the app is wired, in your notebook:

```python
panel = master filtered to IA/NE, corn/soy, reported yields
panel = panel.merge(drought_timing(), on=["fips", "crop", "year"])
panel[panel.max_drought_severity == 4].groupby(["state_alpha", "timing"]).yield_anomaly_pct.agg(["mean", "size"])
```

Expected story: D3 with `peak` timing loses clearly more than D3 with `early` timing.

## Limitations to state
- Irrigation groups use one average share per county; the data stops in 2018.
- Timing uses fixed calendar windows for all counties.

## Notes file and pitch
`connor_notes.md` (Saturday night): what you built, check results, limitations, AI disclosure.
Pitch part (about 1 minute): "Why the table misses": peak vs early drought, irrigated vs dryland Nebraska.
