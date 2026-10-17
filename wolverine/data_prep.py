"""Analysis panel: the filtered county x crop x year rows every Wolverine module works from."""
import numpy as np
import pandas as pd

from src.data_loader import load_master
from wolverine.contracts import STATES, CROPS, TRAIN_YEARS, PANEL_COLS, STRICT_ANOM


def build_panel():
    # Rows with a NASS-reported yield and a drought reading, in our states and crops
    df = load_master()  # fips already a string
    df = df[df.state_alpha.isin(STATES) & df.crop.isin(CROPS)]
    df = df[df.yield_status == "reported"]
    df = df[df.max_drought_severity.notna()]
    return df[PANEL_COLS].reset_index(drop=True)


def add_strict_anomaly(panel):
    # Refit each county-crop trend on training years only, so test years never leak in
    panel = panel.copy()
    panel[STRICT_ANOM] = np.nan
    for _, g in panel.groupby(["fips", "crop"]):
        train = g[g.year.between(*TRAIN_YEARS)]
        if len(train) < 10:
            continue  # trend too unstable, leave NaN
        b, a = np.polyfit(train.year, train.yield_per_acre, 1)
        fitted = a + b * g.year  # extends into the test years
        panel.loc[g.index, STRICT_ANOM] = (g.yield_per_acre - fitted) / fitted * 100
    return panel


def coverage_report(panel):
    # Row counts per state x crop x drought level, split into train and test columns
    period = pd.Series(np.where(panel.year <= TRAIN_YEARS[1], "train", "test"),
                       index=panel.index, name="period")
    return (panel.groupby(["state_alpha", "crop", "max_drought_severity", period])
                 .size().unstack("period").fillna(0).astype(int))
