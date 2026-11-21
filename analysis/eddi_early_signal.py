"""Does short-scale EDDI give early warning of rainfall deficit in Indonesia?

Tests the hypothesis on TerraClimate v1.1, 1950-01..2025-12, 1/24 deg, cells
inside Indonesian admin units. Read-only on all inputs. Prints every number.

Conventions: SPI dry = SPI <= -THR. EDDI dry = EDDI >= +THR.

Sections
  A  base rates, EDDI-1 vs SPI-1 correlation, demand-only share
  B  clean test, no window overlap: does EDDI-1 at month t tell you about
     SPI-1 at t+1, beyond what SPI-1 at t already tells you?
  C  operational test: SPI-3 dry-event onsets. Hit rate, false alarms, and
     added value after controlling for rain already fallen (SPI-2 at t-1)
  D  robustness: by decade and by province

Run: python analysis/eddi_early_signal.py
"""
import os
import time

import geopandas as gpd
import numpy as np
import xarray as xr
from rasterio import features
from rasterio.transform import from_origin

W, E, S, N = 94.5, 141.5, -11.5, 6.5
THR = 1.0
TC = r"G:\temp\terraclimate"
FILES = {
    "spi1": (TC + r"\spi\wld_cli_terraclimate_spi_gamma_1_month.nc", "spi_gamma_1_month"),
    "spi2": (TC + r"\spi\wld_cli_terraclimate_spi_gamma_2_month.nc", "spi_gamma_2_month"),
    "spi3": (TC + r"\spi\wld_cli_terraclimate_spi_gamma_3_month.nc", "spi_gamma_3_month"),
    "eddi1": (TC + r"\eddi\wld_cli_terraclimate_eddi_01month_1950_2025_base1991_2020.nc", "eddi"),
    "eddi3": (TC + r"\eddi\wld_cli_terraclimate_eddi_03month_1950_2025_base1991_2020.nc", "eddi"),
}
ADM1 = r"E:\temp\idn-bnd\idn_bnd_adm1.shp"


def load_window(path, var):
    ds = xr.open_dataset(path)
    lat = ds["lat"].values
    lon = ds["lon"].values
    li = np.where((lat >= S) & (lat <= N))[0]
    lo = np.where((lon >= W) & (lon <= E))[0]
    sub = ds[var].isel(lat=slice(li.min(), li.max() + 1), lon=slice(lo.min(), lo.max() + 1))
    arr = sub.values.astype(np.float32)
    out = (arr, sub["lat"].values, sub["lon"].values, ds["time"].values)
    ds.close()
    return out


def pct(x):
    return f"{100 * x:6.2f}%"


def rate(target, cond):
    n = int(cond.sum())
    return (float(target[cond].mean()) if n else float("nan")), n


def stratified(target, pred, control, valid, width=0.25):
    """Rate of target when pred is on, against the rate when pred is off
    re-weighted to the same distribution of `control` (bins of `width`)."""
    v = valid & np.isfinite(control)
    b = np.clip(np.floor((control[v] + 3.5) / width), 0, int(7 / width) - 1).astype(np.int64)
    p = pred[v]
    t = target[v]
    nb = int(7 / width)
    n1 = np.bincount(b[p], minlength=nb).astype(float)
    t1 = np.bincount(b[p & t], minlength=nb).astype(float)
    n0 = np.bincount(b[~p], minlength=nb).astype(float)
    t0 = np.bincount(b[(~p) & t], minlength=nb).astype(float)
    ok = (n1 > 0) & (n0 > 0)
    r1 = t1[ok].sum() / n1[ok].sum()
    r0 = (n1[ok] * (t0[ok] / n0[ok])).sum() / n1[ok].sum()
    return r1, r0, int(n1[ok].sum())


# ---------------------------------------------------------------- load
t0 = time.time()
cube = {}
for k, (f, v) in FILES.items():
    a, slat, slon, tt = load_window(f, v)
    cube[k] = a
    print(f"loaded {k:6s} {a.shape} from {os.path.basename(f)}  [{time.time() - t0:.0f}s]")
years = tt.astype("datetime64[Y]").astype(int) + 1970
print(f"time: {str(tt[0])[:7]} to {str(tt[-1])[:7]}, {len(tt)} months")

dx = abs(float(slon[1] - slon[0]))
dy = abs(float(slat[1] - slat[0]))
tr = from_origin(float(slon[0]) - dx / 2, float(slat[0]) + dy / 2, dx, dy)
g = gpd.read_file(ADM1, engine="pyogrio")
grid = features.rasterize(zip(g.geometry, range(1, len(g) + 1)), out_shape=(len(slat), len(slon)),
                          transform=tr, fill=0, dtype="int32")
land = np.isfinite(cube["spi1"]).any(axis=0) & np.isfinite(cube["eddi1"]).any(axis=0)
mask = (grid > 0) & land
prov = grid[mask]
print(f"Indonesian land cells: {int(mask.sum()):,}")

X = {k: a[:, mask] for k, a in cube.items()}
del cube
s1, s2, s3, e1, e3 = X["spi1"], X["spi2"], X["spi3"], X["eddi1"], X["eddi3"]
fin = np.isfinite(s1) & np.isfinite(s2) & np.isfinite(s3) & np.isfinite(e1) & np.isfinite(e3)
print(f"cell-months with all five indices finite: {int(fin.sum()):,} of {fin.size:,}")

dS1 = s1 <= -THR
dS3 = s3 <= -THR
dE1 = e1 >= THR
dE3 = e3 >= THR

# ---------------------------------------------------------------- A
print("\n=== A. Base rates and same-month relation (threshold +/-%.1f) ===" % THR)
for name, d in (("SPI-1 dry", dS1), ("SPI-3 dry", dS3), ("EDDI-1 dry", dE1), ("EDDI-3 dry", dE3)):
    print(f"  {name:11s} {pct(d[fin].mean())} of cell-months")


def cell_corr(a, b, ok):
    a = np.where(ok, a, np.nan)
    b = np.where(ok, b, np.nan)
    am = a - np.nanmean(a, axis=0)
    bm = b - np.nanmean(b, axis=0)
    return np.nansum(am * bm, axis=0) / np.sqrt(np.nansum(am ** 2, axis=0) * np.nansum(bm ** 2, axis=0))


r = cell_corr(e1, s1, fin)
print(f"  per-cell corr(EDDI-1, SPI-1) same month: median {np.nanmedian(r):+.3f}, "
      f"p10 {np.nanpercentile(r, 10):+.3f}, p90 {np.nanpercentile(r, 90):+.3f}")
r3 = cell_corr(e3, s3, fin)
print(f"  per-cell corr(EDDI-3, SPI-3) same month: median {np.nanmedian(r3):+.3f}")
for lag in (1, 2, 3):
    ok = fin[:-lag] & fin[lag:]
    ra = cell_corr(e1[:-lag], s1[lag:], ok)
    rb = cell_corr(s1[:-lag], s1[lag:], ok)
    rc = cell_corr(s1[:-lag], e1[lag:], ok)
    print(f"  lag {lag}: corr(EDDI-1[t], SPI-1[t+{lag}]) median {np.nanmedian(ra):+.3f} | "
          f"SPI-1 autocorr {np.nanmedian(rb):+.3f} | corr(SPI-1[t], EDDI-1[t+{lag}]) {np.nanmedian(rc):+.3f}")
both = (dE1 & dS1)[fin].mean()
eonly = (dE1 & ~dS1)[fin].mean()
sonly = (~dE1 & dS1)[fin].mean()
print(f"  same month: both dry {pct(both)}, EDDI-1 dry only {pct(eonly)}, SPI-1 dry only {pct(sonly)}")
print(f"  of EDDI-1 dry months, SPI-1 is also dry in {pct(both / (both + eonly))}")
print(f"  of SPI-1 dry months, EDDI-1 is also dry in {pct(both / (both + sonly))}")

# ---------------------------------------------------------------- B
print("\n=== B. Clean test: EDDI-1 at t against SPI-1 at t+1 (no shared months) ===")
T = dS1[1:]
Ep = dE1[:-1]
Sp = dS1[:-1]
C = s1[:-1]
V = fin[:-1] & fin[1:]
base, n = rate(T, V)
print(f"  P(SPI-1 dry next month)                              {pct(base)}  n={n:,}")
for label, cond in (
    ("| EDDI-1 dry now", V & Ep),
    ("| SPI-1 dry now (persistence)", V & Sp),
    ("| EDDI-1 dry, SPI-1 not dry", V & Ep & ~Sp),
    ("| EDDI-1 not dry, SPI-1 not dry", V & ~Ep & ~Sp),
    ("| EDDI-1 dry, SPI-1 dry", V & Ep & Sp),
    ("| EDDI-1 not dry, SPI-1 dry", V & ~Ep & Sp),
):
    p, n = rate(T, cond)
    print(f"  P(...) {label:36s} {pct(p)}  n={n:,}  lift x{p / base:.2f}")
r1, r0, n = stratified(T, Ep, C, V)
print(f"  Controlling for SPI-1 now in 0.25 bins: EDDI-1 dry {pct(r1)} vs matched EDDI-1 not dry {pct(r0)} "
      f"-> added {100 * (r1 - r0):+.2f} points, x{r1 / r0:.2f}  (n={n:,})")
r1b, r0b, n = stratified(T, Sp, e1[:-1], V)
print(f"  Reverse, controlling for EDDI-1 now: SPI-1 dry {pct(r1b)} vs matched SPI-1 not dry {pct(r0b)} "
      f"-> added {100 * (r1b - r0b):+.2f} points, x{r1b / r0b:.2f}")

# ---------------------------------------------------------------- C
print("\n=== C. SPI-3 dry-event onsets ===")
nt = dS3.shape[0]
onset = np.zeros_like(dS3)
onset[1:] = dS3[1:] & ~dS3[:-1]
onset3 = onset.copy()
onset3[:-2] &= dS3[1:-1] & dS3[2:]
onset3[-2:] = False
atrisk = np.zeros_like(dS3)
atrisk[1:] = ~dS3[:-1] & fin[1:] & fin[:-1]
prevE1 = np.zeros_like(dE1)
prevE1[1:] = dE1[:-1]
prevE3 = np.zeros_like(dE3)
prevE3[1:] = dE3[:-1]
prevS1 = np.zeros_like(dS1)
prevS1[1:] = dS1[:-1]
prevS2 = np.full_like(s2, np.nan)
prevS2[1:] = s2[:-1]
anyE1 = np.zeros_like(dE1)
for k in (1, 2, 3):
    anyE1[k:] |= dE1[:-k]
anyE1[:3] = False

for name, on in (("any length", onset), ("lasting 3+ months", onset3)):
    ar = atrisk.copy()
    if on is onset3:
        ar[-2:] = False
    base, n = rate(on, ar)
    n_on = int((on & ar).sum())
    print(f"\n  Onset = SPI-3 crosses <= -{THR}, {name}. {n_on:,} onsets in {n:,} at-risk cell-months, base {pct(base)}")
    hit1 = prevE1[on & ar].mean()
    hit3 = anyE1[on & ar].mean()
    hitS = prevS1[on & ar].mean()
    print(f"    hit rate: EDDI-1 dry the month before {pct(hit1)} (chance {pct(prevE1[ar].mean())}); "
          f"dry in any of the 3 months before {pct(hit3)} (chance {pct(anyE1[ar].mean())})")
    print(f"    for comparison, SPI-1 dry the month before: {pct(hitS)} (chance {pct(prevS1[ar].mean())})")
    for label, cond in (
        ("| EDDI-1 dry at t-1", ar & prevE1),
        ("| EDDI-3 dry at t-1", ar & prevE3),
        ("| SPI-1 dry at t-1", ar & prevS1),
        ("| EDDI-1 dry, SPI-1 not dry at t-1", ar & prevE1 & ~prevS1),
        ("| neither dry at t-1", ar & ~prevE1 & ~prevS1),
    ):
        p, n = rate(on, cond)
        print(f"    P(onset) {label:36s} {pct(p)}  n={n:,}  lift x{p / base:.2f}")
    r1, r0, n = stratified(on, prevE1, prevS2, ar)
    print(f"    Controlling for rain already fallen (SPI-2 at t-1): EDDI-1 dry {pct(r1)} vs matched not dry {pct(r0)} "
          f"-> added {100 * (r1 - r0):+.2f} points, x{r1 / r0:.2f}  (n={n:,})")

# false alarms: EDDI-1 signal starts while SPI-3 is not dry; does an onset follow within 3 months?
sig = np.zeros_like(dE1)
sig[1:] = dE1[1:] & ~dE1[:-1]
sig &= ~dS3 & fin
follow = np.zeros_like(dS3)
for k in (1, 2, 3):
    follow[:-k] |= onset[k:]
ok = np.ones(nt, bool)
ok[-3:] = False
c = sig & ok[:, None]
p, n = rate(follow, c)
ref = (~dS3) & fin & ok[:, None]
pb, nb = rate(follow, ref)
pn, nn = rate(follow, ref & ~dE1)
print(f"\n  EDDI-1 signals (crossing >= +{THR} while SPI-3 not dry): {n:,}")
print(f"    followed by an SPI-3 onset within 3 months: {pct(p)}  -> false alarm ratio {pct(1 - p)}")
print(f"    any not-dry month is followed by an onset within 3 months: {pct(pb)}; when EDDI-1 is not dry: {pct(pn)}")

# ---------------------------------------------------------------- D
print("\n=== D. Robustness of the section B added value (points, ratio) ===")
dec = (years[:-1] // 10) * 10
for d in sorted(set(dec.tolist())):
    m = V & (dec == d)[:, None]
    r1, r0, n = stratified(T, Ep, C, m)
    print(f"  {d}s: EDDI-1 dry {pct(r1)} vs matched {pct(r0)}  {100 * (r1 - r0):+.2f} pts  x{r1 / r0:.2f}  n={n:,}  "
          f"(EDDI-1 dry share {pct(Ep[m].mean())})")
rows = []
for i in range(1, len(g) + 1):
    m = V & (prov == i)[None, :]
    if m.sum() == 0:
        continue
    r1, r0, n = stratified(T, Ep, C, m)
    rows.append((r1 - r0, r1 / r0, str(g["a1name"].iloc[i - 1]), n))
rows.sort()
d = np.array([x[0] for x in rows]) * 100
print(f"  by province ({len(rows)}): added points min {d.min():+.2f}, median {np.median(d):+.2f}, max {d.max():+.2f}; "
      f"positive in {int((d > 0).sum())} of {len(rows)}")
for x in rows[:3] + rows[-3:]:
    print(f"    {x[2]:28s} {100 * x[0]:+.2f} pts  x{x[1]:.2f}  n={x[3]:,}")
print(f"\ndone in {time.time() - t0:.0f}s")
