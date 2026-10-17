import numpy as np, pandas as pd
from src.data_loader import load_weekly_drought, load_irrigation
from wolverine.contracts import TIMING_COLS, IRRIG_COLS

SEASON = {"CORN": (5, 1, 9, 30), "SOYBEANS": (5, 1, 10, 31)} 
PEAK = (7, 1, 8, 31)                                            

def week_levels(d):

    d2p = d.D2 + d.D3 + d.D4
    conds = [d.D4 > 1,
             d.D3 + d.D4 > 1,
             d2p > 1,
             d.D1 + d2p > 1,
             d.D0 + d.D1 + d2p > 1]
    return np.select(conds, [5, 4, 3, 2, 1], default=0)         

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
