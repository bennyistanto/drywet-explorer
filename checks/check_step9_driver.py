"""Independent check of step 9's driver maps.

For a few accumulations and months, every drawn cell's stored code is rebuilt by another route: one month of
each index is read from its source file and compared with plain inequalities written out here (no call to
conventions.is_dry or to step9_driver). The check then prints, for Indonesia and for one province, the share
of cell area dry or wet on at least one index and the share per driver, to set beside what the page shows.

Run from the repository root:  python -u checks/check_step9_driver.py > checks/check_step9_driver.txt
"""
import gzip
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline import config as C                      # noqa: E402
from pipeline import conventions as K                 # noqa: E402
from pipeline.step0_grid import open_window           # noqa: E402
from pipeline.step1_classes import source_of          # noqa: E402

CASES = [(3, "1997-09"), (1, "2019-10"), (12, "2015-12"), (6, "1983-03"), (3, "2025-12"), (12, "1950-06")]
PROVINCE = 1   # unit id in units_adm1.csv (Aceh), for the page comparison
meta = json.load(open(C.SITE_DATA / "driver.json", encoding="utf-8"))
drawn = np.fromfile(C.STEP1 / "maps" / "cells.u32", "<u4").astype(np.int64)
n = len(drawn)
area = np.frombuffer(gzip.open(C.SITE_DATA / "cell_area.f32.gz").read(), "<f4").astype(np.float64)
mem = np.frombuffer(gzip.open(C.SITE_DATA / "members" / "adm1.u32.gz").read(), "<u4")
prov_cells = mem[mem[0] + 2 + mem[PROVINCE]: mem[0] + 2 + mem[PROVINCE + 1]].astype(np.int64)
assert len(area) == n
bad = 0


def month_of(index, scale, t):
    path, var, _ = source_of(index, scale)
    ds, sub = open_window(path, var)
    raw = sub.isel(time=t).values.reshape(-1)[drawn]
    ds.close()
    v = np.ma.filled(np.ma.masked_invalid(np.asarray(raw, dtype=np.float64)), np.nan)
    v[np.abs(v) > 10] = np.nan
    return v


def shares(code, cells, label):
    c = code[cells]
    a = area[cells]
    valid = a[c > 0].sum()
    if not valid > 0:
        print(f"    {label}: no value")
        return
    k = c.astype(int) - 1
    sp, se, ed = k % 3, (k // 3) % 3, k // 9
    ok = c > 0
    out = []
    for side, v in (("dry", 1), ("wet", 2)):
        anyv = ok & ((sp == v) | (se == v) | (ed == v))
        both = ok & (sp == v) & (ed == v)
        rain = ok & (sp == v) & (ed != v)
        dem = ok & (sp != v) & (ed == v)
        bal = ok & (sp != v) & (ed != v) & (se == v)
        out.append(f"{side} any {a[anyv].sum() / valid:.1%} (rain and demand {a[both].sum() / valid:.1%}, rain alone {a[rain].sum() / valid:.1%}, "
                   f"demand alone {a[dem].sum() / valid:.1%}, balance only {a[bal].sum() / valid:.1%})")
    print(f"    {label}: " + "; ".join(out))


for scale, ym in CASES:
    tag = f"s{scale:02d}"
    if tag not in meta["layers"]:
        print(f"{tag}: not built, skipped")
        continue
    t = K.month_position(ym)
    f = meta["layers"][tag]["maps"][str((1950 + t // 12) // 10 * 10)]
    stored = np.frombuffer(gzip.open(C.SITE_DATA / f["file"]).read(), np.uint8).reshape(f["months"], n)[t - f["first_month"]]
    spi, spei, eddi = month_of("spi", scale, t), month_of("spei", scale, t), month_of("eddi", scale, t)
    want = np.ones(n, np.int64)
    want += np.where(spi <= -1.0, 1, np.where(spi >= 1.0, 2, 0))
    want += 3 * np.where(spei <= -1.0, 1, np.where(spei >= 1.0, 2, 0))
    want += 9 * np.where(eddi >= 1.0, 1, np.where(eddi <= -1.0, 2, 0))          # EDDI: high demand is the dry side
    want[~(np.isfinite(spi) & np.isfinite(spei) & np.isfinite(eddi))] = 0
    diff = int((want != stored).sum())
    bad += diff > 0
    print(f"{tag} {ym}: {diff} of {n:,} cells differ; no value in {int((stored == 0).sum()):,}")
    shares(stored, np.arange(n), "Indonesia")
    shares(stored, prov_cells, f"province id {PROVINCE}")
print("ALL MATCH" if not bad else f"{bad} CASES DIFFER")
