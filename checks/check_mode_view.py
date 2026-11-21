"""Reference figures for the page's mode view ("How long", "Status", "Pattern"), computed in Python.

The page works these out itself, from the per-cell maps and each unit's list of cells. This script computes
the same headline shares by its own route: the unit's cells come from step 0's weights file through
step1_classes.weights_matrix (not from the members files the page reads), and the codes are decoded with
pipeline.status.decode_combined (the page uses its own arithmetic in site/components/palette.js).

Compare the printed lines with the four figures the page shows for the same choice. They were compared on
2026-11-21; the result is in check_mode_view.txt.

Run from the repository root:  python checks/check_mode_view.py
"""
import gzip
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline import config as C                      # noqa: E402
from pipeline import conventions as K                 # noqa: E402
from pipeline import status as S                      # noqa: E402
from pipeline.step1_classes import weights_matrix     # noqa: E402

TAG, YM = "spi03", "2025-12"
UNITS = [(0, None), (1, "Kalimantan Selatan"), (2, "Barito Kuala")]      # level, name (level 0: the country)

t = K.month_position(YM)
grid = xr.open_dataset(C.STEP0 / "grid.nc")
ny, nx = grid["cell_area_km2"].shape
cell_area = grid["cell_area_km2"].values.astype(np.float64).ravel()
grid.close()
drawn = np.fromfile(C.STEP1 / "maps" / "cells.u32", "<u4").astype(np.int64)
n = len(drawn)
pos_of_cell = np.full(ny * nx, -1, np.int64)
pos_of_cell[drawn] = np.arange(n)
area = cell_area[drawn]


def month_codes(meta_file, folder):
    meta = json.load(open(C.SITE_DATA / meta_file, encoding="utf-8"))
    f = meta["layers"][TAG]["maps"][str((1950 + t // 12) // 10 * 10)]
    raw = np.frombuffer(gzip.open(C.SITE_DATA / f["file"]).read(), np.uint8).reshape(f["months"], n)
    return raw[t - f["first_month"]]


combined = month_codes("status.json", "status")
status, howlong = S.decode_combined(combined)
pattern = month_codes("hotspot.json", "hotspot").astype(np.int16) - 9          # category, -9 = no result

for level, name in UNITS:
    if level == 0:
        w = area.copy()
        label = "Indonesia"
    else:
        units = pd.read_csv(C.STEP0 / f"units_adm{level}.csv", dtype={"code": str})
        uid = int(units.loc[units["name"] == name, "id"].iloc[0])
        wf = np.load(C.STEP0 / f"weights_adm{level}.npz")
        W = weights_matrix(wf["cell"], wf["unit"], pos_of_cell, cell_area, len(units)).tocsr()
        w = np.asarray(W[uid - 1].todense()).ravel()
        label = name
    pc = lambda mask, valid: 100 * w[mask & valid].sum() / w[valid].sum()   # noqa: E731
    v = status > 0
    dry_run, wet_run = (status >= 2) & (status <= 5), (status >= 7) & (status <= 10)
    print(f"{label}, {TAG}, {YM}")
    print(f"  Status:   dry event {pc(dry_run, v):.0f}%, deepening {pc(status == 3, v):.0f}%, wet event {pc(wet_run, v):.0f}%, deepening {pc(status == 8, v):.0f}%")
    print(f"  How long: dry event {pc(dry_run, v):.0f}%, 6 months or more {pc(dry_run & (howlong >= 4) & (howlong <= 6), v):.0f}%, "
          f"wet event {pc(wet_run, v):.0f}%, 6 months or more {pc(wet_run & (howlong >= 9), v):.0f}%")
    v = pattern > -9
    print(f"  Pattern:  dry cluster {pc((pattern >= 1) & (pattern <= 7), v):.0f}%, new or consecutive {pc((pattern == 1) | (pattern == 2), v):.0f}%, "
          f"wet cluster {pc((pattern <= -1) & (pattern >= -7), v):.0f}%, new or consecutive {pc((pattern == -1) | (pattern == -2), v):.0f}%")
