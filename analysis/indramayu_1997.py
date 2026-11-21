"""Why does SPI-3 look calm in Indramayu in July to September 1997?

Reads TerraClimate monthly rainfall for the kabupaten's all-touched cells and
the unit means the dashboard uses (step 1 tables), and prints, month by month
for 1997 and early 1998: the rainfall, how it ranks in the record, what the
baseline normally gets, and every index at every scale.

Run from the repository root: python analysis/indramayu_1997.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline import config as C  # noqa: E402
from pipeline.step0_grid import open_window  # noqa: E402

NAME = "Indramayu"
PPT = r"G:\temp\terraclimate\nc\wld_cli_terraclimate_ppt_1950_2025.nc"
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

u2 = pd.read_csv(C.STEP0 / "units_adm2.csv", dtype={"code": str})
row = u2[u2["name"] == NAME].iloc[0]
uid = int(row["id"])
grid = xr.open_dataset(C.STEP0 / "grid.nc")
land = grid["land"].values.astype(bool).ravel()
area = grid["cell_area_km2"].values.ravel().astype(float)
w = np.load(C.STEP0 / "weights_adm2.npz")
cells = w["cell"][w["unit"] == uid].astype(np.int64)
cells = cells[land[cells]]
print(f"{NAME}: unit id {uid}, code {row['code']}, {len(cells)} all-touched land cells")

ds, sub = open_window(PPT, "ppt")
p = sub.values.reshape(sub.shape[0], -1)[:, cells].astype(float)       # [month, cell], mm
ds.close()
wa = area[cells]
pm = (p * wa).sum(axis=1) / wa.sum()                                    # area-mean monthly rainfall
years = 1950 + np.arange(len(pm)) // 12
mons = np.arange(len(pm)) % 12
base = (years >= 1991) & (years <= 2020)
t = lambda y, m: (y - 1950) * 12 + m                                    # noqa: E731

print("\n=== 1. Monthly rainfall, area mean (mm) ===")
print("  month      1997   baseline mean  baseline median  1997 as % of mean  rank in 76 years (1 = driest)  baseline years with < 5 mm")
for m in range(12):
    allm = pm[mons == m]
    b = pm[base & (mons == m)]
    v = pm[t(1997, m)]
    print(f"  {MON[m]} 1997  {v:6.1f}   {b.mean():10.1f}   {np.median(b):12.1f}   {100 * v / b.mean():12.0f}%   "
          f"{int((allm < v).sum()) + 1:10d} of {len(allm)}   {int((b < 5).sum()):12d} of {len(b)}")

print("\n=== 2. Three-month totals ending in each month (mm) ===")
p3 = np.full(len(pm), np.nan)
p3[2:] = pm[2:] + pm[1:-1] + pm[:-2]
print("  3 months ending   1997 total   baseline mean   deficit mm   rank in record (1 = driest)   driest baseline year")
for m in range(12):
    allm = p3[mons == m]
    allm = allm[np.isfinite(allm)]
    b = p3[base & (mons == m)]
    v = p3[t(1997, m)]
    print(f"  {MON[m]} 1997          {v:8.1f}   {b.mean():10.1f}   {v - b.mean():+9.1f}   {int((allm < v).sum()) + 1:8d} of {len(allm)}   {b.min():14.1f}")
jas = [p3[t(y, 8)] for y in range(1950, 2026)]
order = np.argsort(jas)[:8]
print("  driest Jul-Sep totals on record: " + ", ".join(f"{1950 + i} {jas[i]:.0f} mm" for i in order))

print("\n=== 3. Zero and near-zero rainfall in the dry season, baseline 1991-2020, cell-months ===")
for m in (5, 6, 7, 8, 9):
    b = p[base & (mons == m)]
    print(f"  {MON[m]}: exactly 0 mm in {100 * (b == 0).mean():5.1f}% of cell-months, under 5 mm in {100 * (b < 5).mean():5.1f}%, median {np.median(b):.0f} mm")

print("\n=== 4. The indices the dashboard shows, unit mean, 1997-01 to 1998-06 ===")
m1 = json.load(open(C.STEP1 / "manifest.json", encoding="utf-8"))
sc = m1["share_encoding"]["per_level"]["adm2"]["mean_scale"]
miss = m1["share_encoding"]["mean_missing"]
tags = ["spi01", "spi03", "spi06", "spi12", "spei03", "spei12", "eddi03", "eddi12"]
val = {}
for tag in tags:
    a = np.load(C.STEP1 / "shares" / f"{tag}_adm2.npz")["mean"][:, uid - 1].astype(float)
    val[tag] = np.where(a == miss, np.nan, a / sc)
print("  month     " + "  ".join(f"{g:>7s}" for g in tags))
for k in range(t(1997, 0), t(1998, 6)):
    print(f"  {1950 + k // 12}-{MON[k % 12]}  " + "  ".join(f"{val[g][k]:+7.2f}" for g in tags))

print("\n=== 5. How low can each index go here, by calendar month? Lowest unit mean in the whole record ===")
print("  (for EDDI the dry side is positive, so its highest value is shown)")
print("  month  " + "  ".join(f"{g:>7s}" for g in tags))
for m in range(12):
    out = []
    for g in tags:
        x = val[g][mons == m]
        out.append(np.nanmax(x) if g.startswith("eddi") else np.nanmin(x))
    print(f"  {MON[m]}    " + "  ".join(f"{v:+7.2f}" for v in out))

print("\n=== 6. Share of the kabupaten's area in a dry class, 1997-05 to 1998-03 ===")
print("  month     " + "  ".join(f"{g:>7s}" for g in tags))
side = {g: np.load(C.STEP1 / "shares" / f"{g}_adm2.npz")["side"][:, uid - 1, 0].astype(float) / 100 for g in tags}
for k in range(t(1997, 4), t(1998, 3)):
    print(f"  {1950 + k // 12}-{MON[k % 12]}  " + "  ".join(f"{side[g][k]:6.0f}%" for g in tags))
