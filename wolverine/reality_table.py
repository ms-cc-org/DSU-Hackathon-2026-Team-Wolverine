"""Reality table: what each drought level actually cost each state's crops, and a 2013-2025 backtest.

Every function takes a panel (from wolverine.data_prep); nothing here reads files.
"""
import numpy as np

from wolverine.contracts import TRAIN_YEARS, TEST_YEARS, TOLERANCE_PTS, MIN_CELL_N, LEVEL_LABELS


def build_table(panel, years, anom_col="yield_anomaly_pct", extra_by=None):
    # Mean yield anomaly and row count per state x crop x drought level over `years`
    rows = panel[panel.year.between(*years) & panel[anom_col].notna()]
    by = ["state_alpha", "crop", "max_drought_severity"] + (extra_by or [])
    t = rows.groupby(by)[anom_col].agg(mean_loss="mean", n="size").reset_index()
    t = t.rename(columns={"max_drought_severity": "level"})
    t["level_label"] = t.level.map(LEVEL_LABELS)
    return t


def backtest(panel, anom_col="yield_anomaly_pct", extra_by=None):
    # Does the 2000-2012 table still describe 2013-2025? One row per cell.
    keys = ["state_alpha", "crop", "level", "level_label"] + (extra_by or [])
    tr = build_table(panel, TRAIN_YEARS, anom_col, extra_by).rename(
        columns={"mean_loss": "train_mean", "n": "train_n"})
    te = build_table(panel, TEST_YEARS, anom_col, extra_by).rename(
        columns={"mean_loss": "test_mean", "n": "test_n"})
    m = tr.merge(te, on=keys, how="outer")
    m[["train_n", "test_n"]] = m[["train_n", "test_n"]].fillna(0).astype(int)
    m["abs_error"] = (m.test_mean - m.train_mean).abs()
    m["within_tol"] = m.abs_error <= TOLERANCE_PTS
    m["enough_rows"] = (m.train_n >= MIN_CELL_N) & (m.test_n >= MIN_CELL_N)
    return m


def score(check):
    # Summary of the backtest over cells with enough rows in both periods
    ok = check[check.enough_rows]
    return {
        "share_within_tol": ok.within_tol.mean() if len(ok) else np.nan,
        "weighted_mae": (ok.abs_error * ok.test_n).sum() / ok.test_n.sum() if len(ok) else np.nan,
        "cells_scored": len(ok),
        "worst_cells": ok.nlargest(3, "abs_error"),
    }


def _cell(table, state, crop, level):
    hit = table[(table.state_alpha == state) & (table.crop == crop) & (table.level == level)]
    return hit.mean_loss.iloc[0] if len(hit) else np.nan


def same_meaning(table, level, crop):
    # Does a given drought level cost this crop the same in Iowa and Nebraska?
    ia = _cell(table, "IA", crop, level)
    ne = _cell(table, "NE", crop, level)
    gap = ia - ne
    return {"ia": ia, "ne": ne, "gap": gap, "same": bool(abs(gap) <= TOLERANCE_PTS)}


def recommendation(check, table):
    # One plain-English sentence for the app, from the training table and the backtest
    crop = table.crop.iloc[0]
    d = same_meaning(table, level=4, crop=crop)  # 4 = D3
    s = score(check)
    if d["same"]:
        return (f"D3 cost {crop.lower()} about the same in Iowa ({d['ia']:.1f}%) "
                f"and Nebraska ({d['ne']:.1f}%), so one trigger can serve both.")
    return (f"D3 cost Iowa {crop.lower()} {d['ia']:.1f}% vs Nebraska {d['ne']:.1f}% in 2000–2012: "
            f"use state-specific triggers, and trust only the table cells that held up in 2013–2025 "
            f"({s['share_within_tol']:.0%} did).")
