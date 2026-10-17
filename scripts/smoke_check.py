# Run from repo root after every merge into main: python scripts/smoke_check.py
import sys; sys.path.insert(0, ".")

from wolverine.contracts import *
from wolverine.data_prep import build_panel, add_strict_anomaly
from wolverine.reality_table import backtest, score
from wolverine.drought_timing import drought_timing, irrigation_groups

panel = add_strict_anomaly(build_panel());   assert len(panel) > 0 and STRICT_ANOM in panel
check = backtest(panel);                     assert set(CHECK_COLS) <= set(check.columns)
print(score(check))
t = drought_timing();                        assert set(TIMING_COLS) <= set(t.columns)
assert t.timing.isin(TIMING_VALUES).all()
i = irrigation_groups();                     assert set(IRRIG_COLS) <= set(i.columns)
print("SMOKE OK")
