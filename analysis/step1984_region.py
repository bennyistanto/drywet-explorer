"""Where is the early-1984 step, in rainfall (SPI-12) and in demand (EDDI-12)?

Purpose: propose a region and an end month for a region-and-period quality flag.

Per drawn cell, on the DRY-POSITIVE scale (SPI-12 negated, EDDI-12 as is):
  before = mean over 1975-01..1983-12     after = mean over 1985-01..1993-12
  step   = before - after                 (positive: drier before 1984 than after)
A cell "has the step" when before >= BEFORE_MIN and step >= STEP_MIN.
The same test at a placebo break (1995) shows how often it happens anyway.

Prints shares by province and kabupaten, the month-by-month transition, and
writes a map. Read-only on inputs.

Run from the repository root: python analysis/step1984_region.py
"""
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline import config as C  # noqa: E402
from pipeline.step0_grid import open_window  # noqa: E402

BEFORE_MIN = 1.0
STEP_MIN = 1.0
t0 = time.time()


def pos(y, m):
    return (y - 1950) * 12 + (m - 1)


grid = xr.open_dataset(C.STEP0 / "grid.nc")
lat, lon = grid["lat"].values, grid["lon"].values
drawn = (grid["land"].values == 1) & (grid["idn_fraction"].values >= 0.5)
a1 = grid["adm1_id"].values
a2 = grid["adm2_id"].values
riau = grid["flag_riau_block"].values == 1
u1 = pd.read_csv(C.STEP0 / "units_adm1.csv").set_index("id")
u2 = pd.read_csv(C.STEP0 / "units_adm2.csv").set_index("id")


def load(path, var, sign):
    ds, sub = open_window(path, var)
    v = sub.values * sign
    ds.close()
    return v


cube = {"spi12": load(C.SPI_FILE.format(n=12), C.SPI_VAR.format(n=12), -1.0),
        "eddi12": load(C.EDDI_FILE.format(n=12), C.EDDI_VAR, 1.0)}
print(f"loaded [{time.time() - t0:.0f}s]; drawn cells {int(drawn.sum()):,}")


def step_mask(v, break_year):
    b = np.nanmean(v[pos(break_year - 9, 1):pos(break_year - 1, 12) + 1], axis=0)
    a = np.nanmean(v[pos(break_year + 1, 1):pos(break_year + 9, 12) + 1], axis=0)
    return (b >= BEFORE_MIN) & ((b - a) >= STEP_MIN), b, a


res = {}
print(f"\n=== 1. Cells with the step (before >= {BEFORE_MIN}, before - after >= {STEP_MIN}), drawn cells ===")
for k, v in cube.items():
    m84, b, a = step_mask(v, 1984)
    m95, _, _ = step_mask(v, 1995)
    m74, _, _ = step_mask(v, 1974)
    res[k] = (m84, b, a)
    print(f"  {k}: break 1984 {int((m84 & drawn).sum()):6,} ({100 * (m84 & drawn).sum() / drawn.sum():.2f}%)   "
          f"placebo 1974 {int((m74 & drawn).sum()):6,}   placebo 1995 {int((m95 & drawn).sum()):6,}")
s, e = res["spi12"][0] & drawn, res["eddi12"][0] & drawn
either = s | e
print(f"  both {int((s & e).sum()):,}; SPI only {int((s & ~e).sum()):,}; EDDI only {int((e & ~s).sum()):,}; either {int(either.sum()):,}")
print(f"  of the {int((riau & drawn).sum()):,} riau_block cells: {int((riau & s).sum()):,} have the SPI step, {int((riau & e).sum()):,} the EDDI step")
print(f"  step cells outside riau_block: SPI {int((s & ~riau).sum()):,}, EDDI {int((e & ~riau).sum()):,}, either {int((either & ~riau).sum()):,}")

print("\n=== 2. By province: share of drawn cells with the step ===")
rows = []
for pid in np.unique(a1[drawn]):
    if pid == 0:
        continue
    m = drawn & (a1 == pid)
    rows.append((u1.at[pid, "name"], u1.at[pid, "island_group"], int(m.sum()), 100 * s[m].mean(), 100 * e[m].mean(), 100 * either[m].mean(),
                 100 * riau[m].mean()))
prov = pd.DataFrame(rows, columns=["province", "group", "cells", "spi_step", "eddi_step", "either", "riau_block"]).sort_values("either", ascending=False)
print(prov[prov["either"] >= 1.0].round(1).to_string(index=False))
print(f"  provinces with under 1% of cells stepped: {int((prov['either'] < 1.0).sum())}")
by_group = prov.groupby("group").apply(lambda d: pd.Series({"cells": d.cells.sum(), "either_pct": (d.either * d.cells).sum() / d.cells.sum()}))
print(by_group.round(1).to_string())

print("\n=== 3. Kabupaten with a majority of cells stepped ===")
rows = []
for kid in np.unique(a2[drawn]):
    if kid == 0:
        continue
    m = drawn & (a2 == kid)
    if m.sum() >= 5 and either[m].mean() > 0.5:
        rows.append((u1.at[int(u2.at[kid, "adm1_id"]), "name"] if u2.at[kid, "adm1_id"] > 0 else "?", u2.at[kid, "name"],
                     int(m.sum()), 100 * s[m].mean(), 100 * e[m].mean(), 100 * riau[m].mean()))
kab = pd.DataFrame(rows, columns=["province", "kabupaten", "cells", "spi_step", "eddi_step", "riau_block"])
print(f"  {len(kab)} kabupaten; by province:")
print(kab.groupby("province").agg(kabupaten=("kabupaten", "size"), cells=("cells", "sum"),
                                  riau_majority=("riau_block", lambda x: int((x > 50).sum()))).sort_values("kabupaten", ascending=False).to_string())

print("\n=== 4. Where the stepped cells sit ===")
yy, xx = np.where(either)
print(f"  lon {lon[xx].min():.2f}..{lon[xx].max():.2f}, lat {lat[yy].min():.2f}..{lat[yy].max():.2f}")
for name, (x0, x1, y0, y1) in {"Sumatra and its islands (lon < 106.5)": (94, 106.5, -6.5, 6.5),
                               "Kalimantan (108.5..119.5)": (108.5, 119.5, -4.5, 4.5),
                               "Java, Bali, Nusa Tenggara (lat < -5.8)": (105, 127, -11.5, -5.8),
                               "Sulawesi and Maluku (119.5..131)": (119.5, 131, -5.8, 6.5),
                               "Papua (> 131)": (131, 141.5, -11.5, 6.5)}.items():
    box = (lon[None, :] >= x0) & (lon[None, :] <= x1) & (lat[:, None] >= y0) & (lat[:, None] <= y1) & drawn
    print(f"  {name:42s} cells {int(box.sum()):6,}  SPI step {int((s & box).sum()):6,}  EDDI step {int((e & box).sum()):6,}  "
          f"either {100 * (either & box).sum() / max(box.sum(), 1):5.1f}%")

print("\n=== 5. When it ends: mean over stepped cells, month by month (dry-positive) ===")
for k in ("spi12", "eddi12"):
    m = res[k][0] & drawn
    ser = np.nanmean(cube[k][:, m], axis=1)
    rest = np.nanmean(cube[k][:, drawn & ~either], axis=1)
    print(f"  {k} (stepped cells / all other cells):")
    for y in (1982, 1983, 1984, 1985):
        print("    " + f"{y}: " + " ".join(f"{ser[pos(y, mo)]:+.2f}/{rest[pos(y, mo)]:+.2f}" for mo in range(1, 13)))
    yr = [np.nanmean(ser[pos(y, 1):pos(y, 12) + 1]) for y in range(1960, 1996)]
    print("    yearly mean, stepped cells 1960..1995: " + " ".join(f"{v:+.1f}" for v in yr))

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(3, 1, figsize=(13, 13), constrained_layout=True)
    for ax, (k, title) in zip(axes[:2], (("spi12", "SPI-12"), ("eddi12", "EDDI-12"))):
        d = np.where(drawn, res[k][1] - res[k][2], np.nan)
        im = ax.pcolormesh(lon, lat, d, cmap="RdBu_r", vmin=-2, vmax=2, shading="auto")
        ax.set_title(f"{title}: mean 1975-1983 minus mean 1985-1993, dry-positive (red = drier before 1984)")
        fig.colorbar(im, ax=ax, shrink=0.8, label="index units")
    cat = np.where(drawn, 0.0, np.nan)
    cat[s & ~e] = 1
    cat[e & ~s] = 2
    cat[s & e] = 3
    im = axes[2].pcolormesh(lon, lat, cat, cmap=matplotlib.colors.ListedColormap(["#e6e6e6", "#2166ac", "#f1a340", "#b2182b"]),
                            vmin=-0.5, vmax=3.5, shading="auto")
    axes[2].contour(lon, lat, (riau & drawn).astype(float), levels=[0.5], colors="k", linewidths=0.6)
    axes[2].set_title("Cells with the step: rainfall only (blue), demand only (orange), both (red). Black line: current riau_block")
    for ax in axes:
        ax.set_aspect("equal")
        ax.set_xlim(94.5, 141.5)
    out = (Path(__file__).resolve().parents[1] / "temp" / "fig" / "step1984_region.png")
    fig.savefig(out, dpi=120)
    print(f"\nmap written: {out}")
except Exception as ex:  # noqa: BLE001
    print("map not written:", repr(ex)[:200])
print(f"done in {time.time() - t0:.0f}s")
