# Shared names every module imports. Change only with the whole team agreeing.
# Names and values match Ralph's reality_table/data_prep (written against PLAN.md section 3).
# The timing and irrigation entries are still a draft until Connor's branch lands.

STATES = ["IA", "NE"]
CROPS = ["CORN", "SOYBEANS"]

TRAIN_YEARS = (2000, 2012)   # inclusive: build the table
TEST_YEARS = (2013, 2025)    # inclusive: check it held up

# master max_drought_severity: 0 = none, 1..5 = D0..D4 (offset by 1 from USDM labels)
LEVELS = [0, 1, 2, 3, 4, 5]
LEVEL_LABELS = {0: "None", 1: "D0", 2: "D1", 3: "D2", 4: "D3", 5: "D4"}

STRICT_ANOM = "anom_strict"   # trend fitted on TRAIN_YEARS only

TOLERANCE_PTS = 4.0   # a cell "held up" if |test_mean - train_mean| <= this many points
MIN_CELL_N = 20       # a cell is scored only with this many rows in both periods

# build_panel() returns these columns
PANEL_COLS = ["fips", "county_name", "state_alpha", "year", "crop",
              "yield_per_acre", "acres_harvested", "yield_anomaly_pct",
              "max_drought_severity", "weeks_in_d2_plus", "mean_dsci"]

# build_table(...) returns these columns (+ any extra_by columns)
TABLE_COLS = ["state_alpha", "crop", "level", "level_label", "mean_loss", "n"]

# backtest(...) returns these columns (+ any extra_by columns)
CHECK_COLS = ["state_alpha", "crop", "level", "level_label",
              "train_mean", "train_n", "test_mean", "test_n",
              "abs_error", "within_tol", "enough_rows"]

# drought_timing() returns one row per fips x crop x year
TIMING_COLS = ["fips", "crop", "year", "timing"]
TIMING_VALUES = ["none", "early", "peak", "late"]

# irrigation_groups() returns one row per fips x crop
IRRIG_COLS = ["fips", "crop", "irrigated_share", "irrig_group"]
IRRIG_VALUES = ["mostly irrigated", "mixed", "mostly dryland"]
