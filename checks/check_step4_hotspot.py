"""Independent check of step 4's hot spot maps, and a measurement of what "significant" means on this field.

1. For a few layers and months, rebuild the category of every drawn cell by another route: read the window
   from the source file, run pipeline.hotspot.gi_star on the full grid cube (step 4 never calls it: it slices
   pre-built sums), classify, and compare with the stored codes.
2. For the same months: what share of cells is a hot or a cold spot in the final month, and how far from
   zero is the cell's own index where it is one. Gi*'s null treats the 18 values of a neighbourhood as
   independent; on a smooth interpolated field they are not, so significance is reached at small values.

Run from the repository root:  python -u checks/check_step4_hotspot.py
"""
import gzip
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline import config as C                      # noqa: E402
from pipeline import conventions as K                 # noqa: E402
from pipeline import hotspot as H                     # noqa: E402
from pipeline.step0_grid import open_window           # noqa: E402
from pipeline.step1_classes import source_of          # noqa: E402

CASES = [("spi", 3, "2025-12"), ("spi", 3, "1997-09"), ("spi", 12, "2015-12"), ("spei", 6, "1983-03"),
         ("eddi", 1, "2019-10"), ("eddi", 12, "1951-06")]
meta = json.load(open(C.SITE_DATA / "hotspot.json", encoding="utf-8"))
W = meta["parameters"]["window_months"]
assert meta["parameters"]["reference"] == H.REFERENCE, "the maps were built with another reference"
print("reference:", H.REFERENCE)
drawn = np.fromfile(C.STEP1 / "maps" / "cells.u32", "<u4")
n = len(drawn)
bad = 0
for index, scale, ym in CASES:
    tag = f"{index}{scale:02d}"
    if tag not in meta["layers"]:
        print(f"{tag}: not built, skipped")
        continue
    t = K.month_position(ym)
    L = meta["layers"][tag]
    d = str((1950 + t // 12) // 10 * 10)
    f = L["maps"][d]
    raw = np.frombuffer(gzip.open(C.SITE_DATA / f["file"]).read(), np.uint8).reshape(f["months"], n)
    stored = raw[t - f["first_month"]]

    path, var, _ = source_of(index, scale)
    ds, sub = open_window(path, var)
    ny, nx = sub.shape[1:]
    cube = K.to_float(sub.isel(time=slice(t - W - H.TIME_STEP + 1, t + 1)).values) * K.DRY_SIGN[index]
    ds.close()
    mask = np.zeros(ny * nx, bool)
    mask[drawn] = True
    cube[:, ~mask.reshape(ny, nx)] = np.nan
    if t < L["first_month_with_result"]:
        ok = bool((stored == 0).all())
        print(f"{tag} {ym}: before the first result month; stored all zero: {ok}")
        bad += not ok
        continue
    z = H.gi_star(cube)
    cat = H.classify(z, fdr=True).ravel()[drawn]
    want = np.where(cat == -128, 0, cat.astype(np.int16) + 9).astype(np.uint8)
    diff = int((want != stored).sum())
    bad += diff > 0
    hot, cold = H.significant(z, fdr=True)
    fh, fc = hot[-1].ravel()[drawn], cold[-1].ravel()[drawn]
    own = cube[-1].ravel()[drawn]
    val = np.isfinite(own)
    q = lambda a: "none" if not a.size else f"{np.percentile(a, 5):+.2f} / {np.median(a):+.2f}"   # noqa: E731
    print(f"{tag} {ym}: cells differing from stored {diff} of {n}; final month hot {fh.sum() / val.sum():.1%}, "
          f"cold {fc.sum() / val.sum():.1%}; own index (positive = dry) where hot, 5th pct / median {q(own[fh])}; "
          f"where cold, 95th pct / median {'none' if not fc.any() else f'{np.percentile(own[fc], 95):+.2f} / {np.median(own[fc]):+.2f}'}; "
          f"share of cells with own |index| >= 1.0: {(np.abs(own[val]) >= 1).mean():.1%}")
print("ALL MATCH" if not bad else f"{bad} CASES DIFFER")
