# Ralph — Analysis panel + Reality table

## What I built

**`wolverine/data_prep.py`**
- `build_panel()`: master dataset filtered to our states and crops, keeping only NASS-`reported` yields that also have a drought reading. Columns come from `contracts.PANEL_COLS`.
- `add_strict_anomaly(panel)`: adds `anom_strict`, a yield anomaly whose county-crop trend is fitted on 2000–2012 only and then extended into 2013–2025, so test years never shape the trend. Left NaN when a county-crop pair has fewer than 10 training years.
- `coverage_report(panel)`: row counts for each state, crop and drought level, split into train and test columns.

**`wolverine/reality_table.py`** (every function takes a panel and none reads files)
- `build_table`: mean yield anomaly and row count for each state × crop × drought level over a range of years.
- `backtest`: builds the table on 2000–2012 and on 2013–2025, then marks each cell with its absolute error, whether that error is within the tolerance, and whether both periods have enough rows.
- `score`: share of scored cells within tolerance, test-n-weighted MAE, number of cells scored, and the 3 worst cells.
- `same_meaning`: does a drought level cost a crop the same in Iowa and Nebraska?
- `recommendation`: the one-sentence takeaway for the app.

## Checks

`wolverine/contracts.py` wasn't pushed yet, so the results below were run with stand-in values that should be re-checked against it: IA + NE, corn + soybeans, train 2000–2012, test 2013–2025, tolerance 4 pts, minimum 20 rows per cell. The panel has 8,708 rows. `anom_strict` is NaN for 55 of them (thin county-crop pairs).

### Part 1
| Check | Result |
|---|---|
| Polk County IA (19153) corn 2012 is in the panel | Yes. Yield 149.1 bu/ac, severity 4 (D3) |
| Its `anom_strict` is negative | Yes, **−6.6%** (`yield_anomaly_pct` is −15.5%) |
| Each county's mean `anom_strict` over 2000–2012 is about 0 | Yes. The largest absolute mean across 361 county-crop pairs is 0.37 pts. It isn't exactly 0 because OLS centres residuals in bushels, not percent. |

### Part 2: Iowa corn, level 4 (D3)
| Anomaly column | Train mean (n) | Test mean (n) | Abs error | Matches PLAN.md? |
|---|---|---|---|---|
| `yield_anomaly_pct` | **−17.4** (147) | **−3.9** (114) | 13.5 | Yes |
| `anom_strict` | −15.5 (147) | +28.1 (114) | 43.6 | — |

### Backtest score (cells with ≥ 20 rows in both periods)
| Anomaly column | Cells scored | Within 4 pts | Weighted MAE |
|---|---|---|---|
| `yield_anomaly_pct` | 22 of 24 | **82%** | 2.4 pts |
| `anom_strict` | 22 of 24 | 68% | 8.7 pts |

Worst cells with `yield_anomaly_pct`: IA corn D3 (13.5 pts off), IA soybeans D3 (11.2), IA soybeans D1 (4.4).

### Iowa vs Nebraska at D3, 2000–2012
| Crop | Iowa | Nebraska | Gap | Same within 4 pts? |
|---|---|---|---|---|
| Corn | −17.4% | −6.0% | −11.4 | No |
| Soybeans | −15.1% | −9.9% | −5.2 | No |

Recommendation output (corn): *"D3 cost Iowa corn -17.4% vs Nebraska -6.0% in 2000–2012: use state-specific triggers, and trust only the table cells that held up in 2013–2025 (82% did)."*

## Limitations
- **2012 dominates training.** 61% of Iowa corn's D3+ training rows (51% for soybeans, 29% in Nebraska) come from 2012. The −17.4% for "Iowa corn at D3" is largely "Iowa corn in 2012". The 2013–2025 droughts were milder, so the cell misses by 13.5 pts.
- **`anom_strict` breaks for Iowa corn in test years.** 2012 falls at the end of the training window and flattens each county's trend: the median Iowa corn slope is 0.64 bu/ac/yr with 2012 and 2.02 without it. Extended forward, that trend under-predicts 2013–2025, so Iowa corn's test anomalies average +23.5% (about 0 for NE corn, NE soybeans and IA soybeans). Strict test numbers for Iowa corn are not trustworthy. The fix would be a robust trend fit, or dropping 2012 from the trend fit only, which needs a team decision.
- **D4 cells are thin.** Iowa has 5 training rows at D4 for both corn and soybeans, so those cells are excluded from scoring (they are the 2 unscored cells). Don't quote D4 numbers for Iowa.
- `yield_anomaly_pct` uses a trend fitted on all 26 years, so test years leak into the trend. That is why `anom_strict` exists, and why both results are reported.

## AI disclosure
- **Tool:** Claude Code (Claude Opus 5.5).
- **What for:** turning the task spec's pseudo-code into working pandas, writing the check script, finding the cause of the `anom_strict` bias in test years, and drafting this notes file.
- **How I verified:** the Iowa corn D3 cell reproduces PLAN.md exactly (train −17.4, test −3.9). I checked Polk County 2012 and the per-county training means by hand against the panel, and confirmed the 2012 slope effect by refitting each Iowa county's trend with and without 2012.

## Pitch (about 1 minute): "How we know it works"
> We built the table only on 2000–2012, then checked it against 13 years it had never seen. 82% of the cells with enough data landed within 4 points of what actually happened, with an average miss of 2.4 points. The big miss is honest and useful: in 2000–2012, extreme drought (D3) cost Iowa corn 17% of its yield, but in 2013–2025 it cost only 4%. Most of Iowa's training-era D3 is the single 2012 drought, so one bad year was setting the number. D3 also costs Iowa and Nebraska very differently (−17% vs −6%, because Nebraska irrigates), so one trigger can't serve both states. Use state-specific triggers, and trust only the cells that held up.
