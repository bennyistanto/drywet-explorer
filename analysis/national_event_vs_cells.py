"""Does "Indonesia has been in a wet event since June 2024" mean the same places were wet throughout?

The national event is found on the mean of all cells (SPI-3): it began in 2024-06 and was still running in
2025-12. This script looks at the cells one by one over those 19 months:
  - how many were in a wet event of their own for the whole time, and how many at the end only;
  - how many were in a wet CLASS (index at or above +1.0) every month, in some months, or never;
  - how the wet-class share moved month by month, and how much of it was the same cells as the month before.

Run from the repository root:  python analysis/national_event_vs_cells.py
"""
import sys
from pathlib import Path

import numpy as np
import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline import config as C                      # noqa: E402
from pipeline import conventions as K                 # noqa: E402
from pipeline import status as S                      # noqa: E402
from pipeline.step0_grid import open_window           # noqa: E402
from pipeline.step1_classes import source_of          # noqa: E402

INDEX, SCALE, START, END = "spi", 3, "2024-06", "2025-12"
t0, t1 = K.month_position(START), K.month_position(END)
grid = xr.open_dataset(C.STEP0 / "grid.nc")
cell_area = grid["cell_area_km2"].values.astype(np.float64).ravel()
grid.close()
drawn = np.fromfile(C.STEP1 / "maps" / "cells.u32", "<u4").astype(np.int64)
area = cell_area[drawn]
path, var, _ = source_of(INDEX, SCALE)
ds, sub = open_window(path, var)
v = K.to_float(sub.values.reshape(K.N_MONTHS, -1)[:, drawn])
ds.close()
ok = np.isfinite(v[t1])
w = area / area[ok].sum()
share = lambda m: float(w[m & ok].sum()) * 100          # noqa: E731

wet = -v * K.DRY_SIGN[INDEX]                             # positive on the wet side
run = S.running(wet, K.EVENT_ONSET)                      # months so far of each cell's own wet event
n = t1 - t0 + 1
mean = np.array([np.average(v[t][ok], weights=area[ok]) for t in range(t0, t1 + 1)])
print(f"{INDEX.upper()}-{SCALE}, {START} to {END}: {n} months. National mean {mean.min():+.2f} to {mean.max():+.2f}, last {mean[-1]:+.2f}")

print("\nEach cell's own wet event, at the last month:")
print(f"  in a wet event now                         {share(run[t1] > 0):5.1f}% of area")
print(f"  in one that has run {n} months or more       {share(run[t1] >= n):5.1f}%")
print(f"  in one that has run 12 months or more       {share(run[t1] >= 12):5.1f}%")
print(f"  in a wet event in every one of the {n} months {share((run[t0:t1 + 1] > 0).all(axis=0)):5.1f}%")
print(f"  in a wet event in at least one of them      {share((run[t0:t1 + 1] > 0).any(axis=0)):5.1f}%")

cls = wet[t0:t1 + 1] >= 1.0                              # wet class (moderately wet or more)
k = cls.sum(axis=0)
print("\nWet CLASS (index at or beyond the wet onset level), over the same months:")
print(f"  every month                                 {share(k == n):5.1f}% of area")
print(f"  at least half of the months                 {share(k >= n / 2):5.1f}%")
print(f"  at least one month                          {share(k >= 1):5.1f}%")
print(f"  never                                       {share(k == 0):5.1f}%")
dry_cls = wet[t0:t1 + 1] <= -1.0
print(f"  in a DRY class in at least one month        {share(dry_cls.any(axis=0)):5.1f}%")

print("\nMonth by month: share in a wet class, and how much of it was also wet the month before")
for i, t in enumerate(range(t0, t1 + 1)):
    now = wet[t] >= 1.0
    before = wet[t - 1] >= 1.0
    s = share(now)
    kept = share(now & before) / s * 100 if s else float("nan")
    print(f"  {1950 + t // 12}-{t % 12 + 1:02d}  mean {mean[i]:+.2f}  wet class {s:5.1f}%  dry class {share(wet[t] <= -1.0):5.1f}%  same cells as last month {kept:5.1f}%")
