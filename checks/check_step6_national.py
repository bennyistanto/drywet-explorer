"""Independent check of step 6 (Indonesia as one unit).

1. Share of area per class: rebuilt from step 1's stored class maps (one class code per drawn cell and month)
   and the cell areas, without reading a source cube and without calling unit_stats. Compared with the
   stored national shares, every layer, every month.
2. Mean index: for a few layers and months, read from the source file directly and averaged with np.average.
3. Events: the national events re-found from the stored (rounded) national mean by a plain loop; starts and
   ends compared with the stored events. A rounded mean can differ from the unrounded one exactly at the
   onset level or at zero, so mismatches are counted, not asserted to be none.

Run from the repository root:  python -u checks/check_step6_national.py
"""
import gzip
import json
import sys
from pathlib import Path

import numpy as np
import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline import config as C                      # noqa: E402
from pipeline import conventions as K                 # noqa: E402
from pipeline.step0_grid import open_window           # noqa: E402
from pipeline.step1_classes import source_of          # noqa: E402

grid = xr.open_dataset(C.STEP0 / "grid.nc")
cell_area = grid["cell_area_km2"].values.astype(np.float64).ravel()
ny, nx = grid["cell_area_km2"].shape
grid.close()
drawn = np.fromfile(C.STEP1 / "maps" / "cells.u32", "<u4").astype(np.int64)
area = cell_area[drawn]
n = len(drawn)
meta = json.load(open(C.SITE_DATA / "national.json", encoding="utf-8"))
E = K.SHARE_ENCODING[1]
bad = 0
print(f"unit: {meta['unit']['n_cells']:,} cells, {meta['unit']['cells_km2']:,.0f} km2; recomputed {n:,} cells, {area.sum():,.0f} km2")
bad += abs(meta["unit"]["cells_km2"] - area.sum()) > 0.5

for tag, L in sorted(meta["layers"].items()):
    codes = L["classes"]
    nc = len(codes)
    share = np.frombuffer(gzip.open(C.SITE_DATA / "national" / f"{tag}_share.u16.gz").read(), "<u2").reshape(K.N_MONTHS, nc)
    mean = np.frombuffer(gzip.open(C.SITE_DATA / "national" / f"{tag}_mean.i16.gz").read(), "<i2").astype(np.float64)
    mean = np.where(mean == K.MEAN_MISSING, np.nan, mean / E["mean_scale"])
    # ---- 1. shares from the class maps
    worst = 0.0
    for y in range(1950, 2026):
        cm = np.frombuffer(gzip.open(C.STEP1 / "maps" / tag / f"{y}.u8.gz").read(), np.uint8).reshape(12, n)
        for m in range(12):
            t = (y - 1950) * 12 + m
            a = np.array([area[cm[m] == c].sum() for c in codes])
            if a.sum() == 0:
                bad += not (share[t] == E["share_missing"]).all()
                continue
            want = a / a.sum()
            got = share[t] / E["share_scale"]
            worst = max(worst, float(np.abs(want - got).max()))
    ok1 = worst <= 0.5 / E["share_scale"] + 1e-9
    bad += not ok1
    # ---- 3. events from the stored mean
    ev = json.load(open(C.SITE_DATA / "national" / f"{tag}_events.json", encoding="utf-8"))
    stored = {(s, a, b) for s, a, b in zip(ev["side"], ev["start"], ev["end"])}
    found = set()
    for side, sg in ((0, K.DRY_SIGN[L["index"]]), (1, -K.DRY_SIGN[L["index"]])):
        d = mean * sg
        t = 0
        while t < K.N_MONTHS:
            if np.isfinite(d[t]) and d[t] >= K.EVENT_ONSET:
                e = t
                while e + 1 < K.N_MONTHS and np.isfinite(d[e + 1]) and d[e + 1] >= 0:
                    e += 1
                found.add((side, t, e))
                t = e + 1
            else:
                t += 1
    print(f"{tag}: largest share difference {worst:.6f} (half a storage step is {0.5 / E['share_scale']:.6f}) {'ok' if ok1 else 'BAD'}; "
          f"events stored {len(stored)}, re-found {len(found)}, in both {len(stored & found)}")

# ---- 2. mean from the source, a few cases
for index, scale, ym in (("spi", 3, "1997-09"), ("spei", 12, "2015-12"), ("eddi", 1, "2019-10"), ("spi", 12, "1961-03")):
    tag = f"{index}{scale:02d}"
    if tag not in meta["layers"]:
        continue
    t = K.month_position(ym)
    path, var, _ = source_of(index, scale)
    ds, sub = open_window(path, var)
    v = K.to_float(sub.isel(time=t).values).ravel()[drawn]
    ds.close()
    okv = np.isfinite(v)
    want = float(np.average(v[okv], weights=area[okv]))
    got = np.frombuffer(gzip.open(C.SITE_DATA / "national" / f"{tag}_mean.i16.gz").read(), "<i2")[t] / E["mean_scale"]
    ok2 = abs(want - got) <= 0.5 / E["mean_scale"] + 1e-9
    bad += not ok2
    print(f"{tag} {ym}: mean from source {want:+.4f}, stored {got:+.3f} {'ok' if ok2 else 'BAD'}")
print("ALL OK" if not bad else f"{bad} PROBLEMS")
