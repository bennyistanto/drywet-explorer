"""Independent check of step 7's status maps.

For a few layers and months, and a sample of cells, the stored code is rebuilt by another route: the cell's
series is read from the source file, its events are found with events.events_reference (a plain per-series
loop that shares no code with status.running), and the state and duration bin are worked out by hand from
the event's start, the value this month and the value a month before.

Run from the repository root:  python -u checks/check_step7_status.py
"""
import gzip
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline import config as C                      # noqa: E402
from pipeline import conventions as K                 # noqa: E402
from pipeline.events import events_reference          # noqa: E402
from pipeline.step0_grid import open_window           # noqa: E402
from pipeline.step1_classes import source_of          # noqa: E402

CASES = [("spi", 3, "1997-09"), ("spi", 12, "2015-12"), ("spei", 6, "1983-03"), ("eddi", 1, "2019-10"), ("eddi", 12, "2025-12"),
         ("spi", 1, "1950-01")]
NCELLS = 400
BINS = ((1, 2), (3, 5), (6, 11), (12, 23), (24, 10 ** 6))
meta = json.load(open(C.SITE_DATA / "status.json", encoding="utf-8"))
drawn = np.fromfile(C.STEP1 / "maps" / "cells.u32", "<u4").astype(np.int64)
n = len(drawn)
rng = np.random.default_rng(11)
pick = np.sort(rng.choice(n, NCELLS, replace=False))
bad = 0


def expect(series, t):
    """Combined code of one cell at month t, from first principles. series: dry side positive."""
    x = series[t]
    if not np.isfinite(x):
        return 0
    for side, s in ((0, series), (1, -series)):
        for a, b, _ in events_reference(s[: t + 1]):
            if a <= t <= b:                                   # an event is running on this side
                dur = t - a + 1
                k = next(i for i, (lo, hi) in enumerate(BINS) if lo <= dur <= hi)
                if dur <= 2:
                    state = 0
                elif s[t] >= 1.0:
                    state = 1 if s[t] > s[t - 1] else 2
                else:
                    state = 3
                return 2 + side * 25 + state * 5 + k
    for side, s in ((0, series), (1, -series)):               # nothing running: did one end this month?
        if t > 0 and any(b == t - 1 for _, b, _ in events_reference(s[:t])):
            return 2 + side * 25 + 4 * 5
    return 1


for index, scale, ym in CASES:
    tag = f"{index}{scale:02d}"
    if tag not in meta["layers"]:
        print(f"{tag}: not built, skipped")
        continue
    t = K.month_position(ym)
    f = meta["layers"][tag]["maps"][str((1950 + t // 12) // 10 * 10)]
    stored = np.frombuffer(gzip.open(C.SITE_DATA / f["file"]).read(), np.uint8).reshape(f["months"], n)[t - f["first_month"], pick]
    path, var, _ = source_of(index, scale)
    ds, sub = open_window(path, var)
    v = K.to_float(sub.isel(time=slice(0, t + 1)).values.reshape(t + 1, -1)[:, drawn[pick]]) * K.DRY_SIGN[index]
    ds.close()
    want = np.array([expect(v[:, j], t) for j in range(NCELLS)], np.uint8)
    diff = int((want != stored).sum())
    bad += diff > 0
    kinds = np.bincount(np.where(stored < 2, stored, 2 + ((stored - 2) % 25) // 5), minlength=7)
    print(f"{tag} {ym}: {diff} of {NCELLS} sampled cells differ; in the sample: no value {kinds[0]}, no event {kinds[1]}, "
          f"new {kinds[2]}, deepening {kinds[3]}, persisting {kinds[4]}, easing {kinds[5]}, ended {kinds[6]}")
print("ALL MATCH" if not bad else f"{bad} CASES DIFFER")
