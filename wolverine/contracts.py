# Shared names every module imports (PLAN.md section 3).
# Changes go through the group chat, and Tolu makes them.

STATES = ["IA", "NE"]
CROPS = ["CORN", "SOYBEANS"]
TRAIN_YEARS = (2000, 2012)
TEST_YEARS  = (2013, 2025)
TOLERANCE_PTS = 4.0
MIN_CELL_N = 10

LEVEL_LABELS = {0: "None", 1: "D0", 2: "D1", 3: "D2", 4: "D3", 5: "D4"}
LEVELS = list(LEVEL_LABELS)   # 0..5, in order; the app uses it to sort the bars

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
