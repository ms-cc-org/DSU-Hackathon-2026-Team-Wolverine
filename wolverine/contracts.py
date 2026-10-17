# Shared names every module imports. Change only with the whole team agreeing.
# DRAFT: reconstructed from TOLU.md because PLAN.md section 3 was not in the repo.
# Reconcile with PLAN.md section 3 before anyone branches.

CROPS = ["CORN", "SOYBEANS"]
STATES = ["IA", "NE"]

TRAIN_YEARS = list(range(2000, 2013))   # 2000-2012: build the table
TEST_YEARS = list(range(2013, 2026))    # 2013-2025: check it held up

# master max_drought_severity: 0 = none, 1..5 = D0..D4 (offset by 1 from USDM labels)
LEVELS = [0, 1, 2, 3, 4, 5]
LEVEL_LABELS = {0: "None", 1: "D0", 2: "D1", 3: "D2", 4: "D3", 5: "D4"}
LEVEL_COL = "max_drought_severity"

STRICT_ANOM = "yield_anomaly_strict_pct"   # trend fitted on TRAIN_YEARS only

TOL_PTS = 4.0      # a cell "held up" if |test_mean - train_mean| <= this many points
MIN_CELL_N = 10    # cells with fewer county-years are shown grey and not scored

# build_table(...) returns these columns (+ any extra_by columns)
TABLE_COLS = ["state_alpha", "level", "n", "mean_loss"]

# backtest(...) returns these columns (+ any extra_by columns)
CHECK_COLS = ["state_alpha", "level", "n_train", "train_mean",
              "n", "test_mean", "error", "within_tol"]

# drought_timing() returns one row per fips x crop x year
TIMING_COLS = ["fips", "crop", "year", "timing"]
TIMING_VALUES = ["none", "early", "peak", "late"]

# irrigation_groups() returns one row per fips x crop
IRRIG_COLS = ["fips", "crop", "irrigated_share", "irrig_group"]
IRRIG_VALUES = ["mostly irrigated", "mixed", "mostly dryland"]
