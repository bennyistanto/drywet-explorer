"""Retest of emerging hot spot analysis on this project's data, before anything is built on it.

`nino` found the taxonomy collapsed on 76 annual bins. Here the cube is monthly and ends at the month being
monitored, so the question is: for which window length are the categories populated?

For each window length W (months) and each end month (every December 1990..2025), classify the drawn cells
with pipeline.hotspot and count cells per category. The neighbourhood sums are built once, as step 4 does.

Run from the repository root:  python -u analysis/ehsa_retest.py spi 3
"""
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline import config as C                      # noqa: E402
from pipeline import conventions as K                 # noqa: E402
from pipeline import hotspot as H                     # noqa: E402
from pipeline.step0_grid import open_window           # noqa: E402
from pipeline.step1_classes import source_of          # noqa: E402
from pipeline.step4_hotspot import neighbourhood_sums  # noqa: E402

index = sys.argv[1] if len(sys.argv) > 1 else "spi"
scale = int(sys.argv[2]) if len(sys.argv) > 2 else 3
WINDOWS = [12, 24, 36, 60]
T0 = time.time()

path, var, _ = source_of(index, scale)
ds, sub = open_window(path, var)
drawn = np.fromfile(C.STEP1 / "maps" / "cells.u32", "<u4")
v, sx, sw = neighbourhood_sums(sub, K.DRY_SIGN[index], drawn, sub.shape[1:])
ds.close()
print(f"{index.upper()}-{scale}: read {v.shape} in {time.time() - T0:.0f}s; positive is dry; "
      f"neighbourhood {H.SPATIAL}x{H.SPATIAL} cells and {H.TIME_STEP} step back", flush=True)

ends = [(y - 1950) * 12 + 11 for y in range(1990, 2026)]
codes = [0] + list(range(1, 9)) + list(range(-1, -9, -1))
print(f"reference: {H.REFERENCE}")
for fdr in (True,):
    print(f"\n===== significance at 90%, {'with' if fdr else 'without'} FDR correction =====")
    print("Mean share of drawn cells per category over 36 Decembers (1990..2025), %; "
          "in brackets the number of those Decembers in which the category has any cell")
    table = {}
    for W in WINDOWS:
        counts = np.zeros((len(ends), len(codes)))
        for i, e in enumerate(ends):
            w = slice(e - W + 1, e + 1)
            cat = H.classify(H.z_from_sums(sx[w], sw[w], v[w]), fdr)
            valid = cat != -128
            counts[i] = [(cat[valid] == c).sum() / valid.sum() * 100 for c in codes]
        npop = (counts > 0).sum(axis=1)
        table[W] = (counts.mean(axis=0), (counts > 0).sum(axis=0), counts[-1], npop)
        print(f"  W={W:3d} done at {time.time() - T0:.0f}s", flush=True)
    print(f"\n{'category':26s}" + "".join(f"{'W=' + str(W):>14s}" for W in WINDOWS))
    for j, c in enumerate(codes):
        print(f"{H.CATEGORIES[c]:26s}" + "".join(f"{table[W][0][j]:8.2f} [{table[W][1][j]:2d}] " for W in WINDOWS))
    print(f"{'categories populated':26s}" + "".join(f"{table[W][3].mean():6.1f} of 17  " for W in WINDOWS) + " (mean over Decembers)")
    print(f"{'  min / max':26s}" + "".join(f"{table[W][3].min():6d} /{table[W][3].max():3d}   " for W in WINDOWS))
    print("\nDecember 2025 alone, % of drawn cells")
    for j, c in enumerate(codes):
        print(f"{H.CATEGORIES[c]:26s}" + "".join(f"{table[W][2][j]:13.2f} " for W in WINDOWS))
print(f"\ntotal {time.time() - T0:.0f}s")
