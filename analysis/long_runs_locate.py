"""Where and when are the implausibly long SPI-12 dry runs, and what is behind them?

A run = consecutive months with SPI-12 < -1.0 (strict), per cell.
Reports: how many cells, which provinces, which years, whether they cluster,
and what the underlying precipitation did relative to the 1991-2020 baseline.
Writes one map to temp/fig/. Read-only on inputs.

Run: python analysis/long_runs_locate.py
"""
import os
import time

import geopandas as gpd
import numpy as np
import xarray as xr
from rasterio import features
from rasterio.transform import from_origin
from scipy import ndimage

W, E, S, N = 94.5, 141.5, -11.5, 6.5
THR = -1.0
LONG = 100   # months: the "implausible" bar
MID = 48
SPI12 = r"G:\temp\terraclimate\spi\wld_cli_terraclimate_spi_gamma_12_month.nc"
PPT = r"G:\temp\terraclimate\nc\wld_cli_terraclimate_ppt_1950_2025.nc"
ADM1 = r"E:\temp\idn-bnd\idn_bnd_adm1.shp"
FIG = os.path.join(os.path.dirname(__file__), "..", "..", "fig")


def load_window(path, var=None):
    ds = xr.open_dataset(path)
    if var is None:
        var = [v for v in ds.data_vars if ds[v].ndim == 3][0]
    lat = ds["lat"].values
    lon = ds["lon"].values
    li = np.where((lat >= S) & (lat <= N))[0]
    lo = np.where((lon >= W) & (lon <= E))[0]
    sub = ds[var].isel(lat=slice(li.min(), li.max() + 1), lon=slice(lo.min(), lo.max() + 1))
    out = (sub.values.astype(np.float32), sub["lat"].values, sub["lon"].values, ds["time"].values, var,
           dict(ds[var].attrs))
    ds.close()
    return out


t0 = time.time()
spi, slat, slon, tt, _, _ = load_window(SPI12, "spi_gamma_12_month")
nt = spi.shape[0]
years = tt.astype("datetime64[Y]").astype(int) + 1970
ym = np.array([str(x)[:7] for x in tt])
print(f"SPI-12 window {spi.shape}  [{time.time() - t0:.0f}s]")

dx = abs(float(slon[1] - slon[0]))
dy = abs(float(slat[1] - slat[0]))
tr = from_origin(float(slon[0]) - dx / 2, float(slat[0]) + dy / 2, dx, dy)
g = gpd.read_file(ADM1, engine="pyogrio")
names = [str(x) for x in g["a1name"]]
grid = features.rasterize(zip(g.geometry, range(1, len(g) + 1)), out_shape=(len(slat), len(slon)),
                          transform=tr, fill=0, dtype="int32")
mask = (grid > 0) & np.isfinite(spi).any(axis=0)
nc = int(mask.sum())
x = spi[:, mask]
prov = grid[mask]
print(f"Indonesian land cells: {nc:,}")

# ---- longest run below THR per cell, with its end index
cur = np.zeros(nc, np.int32)
best = np.zeros(nc, np.int32)
best_end = np.zeros(nc, np.int32)
for t in range(nt):
    v = x[t]
    b = np.isfinite(v) & (v < THR)
    cur = np.where(b, cur + 1, 0)
    up = cur > best
    best[up] = cur[up]
    best_end[up] = t
best_start = best_end - best + 1

print("\n=== 1. How many cells ===")
for k in (24, 36, MID, 60, LONG, 150, 200):
    n = int((best >= k).sum())
    print(f"  longest run >= {k:3d} months: {n:7,} cells ({100 * n / nc:5.2f}%)")
print(f"  percentiles of longest run: p50 {np.percentile(best, 50):.0f}, p90 {np.percentile(best, 90):.0f}, "
      f"p99 {np.percentile(best, 99):.0f}, max {best.max()}")

sel = best >= LONG
print(f"\n=== 2. When: the {int(sel.sum()):,} cells with a run of {LONG}+ months ===")
sy = years[best_start[sel]]
ey = years[best_end[sel]]
print(f"  start year: min {sy.min()}, p25 {np.percentile(sy, 25):.0f}, median {np.median(sy):.0f}, "
      f"p75 {np.percentile(sy, 75):.0f}, max {sy.max()}")
print(f"  end year:   min {ey.min()}, p25 {np.percentile(ey, 25):.0f}, median {np.median(ey):.0f}, "
      f"p75 {np.percentile(ey, 75):.0f}, max {ey.max()}")
for d in range(1950, 2030, 10):
    print(f"    runs starting in the {d}s: {int(((sy // 10) * 10 == d).sum()):6,}   ending: {int(((ey // 10) * 10 == d).sum()):6,}")
print(f"  runs lying entirely before 1991: {int((ey < 1991).sum()):,}; overlapping the 1991-2020 baseline: "
      f"{int(((ey >= 1991) & (sy <= 2020)).sum()):,}; entirely after 2020: {int((sy > 2020).sum()):,}")

print("\n=== 3. Where: by province ===")
rows = []
for i, nm in enumerate(names, start=1):
    m = prov == i
    if m.sum() == 0:
        continue
    rows.append((int((sel & m).sum()), int(m.sum()), nm, int(np.median(best[m])), int(best[m].max())))
rows.sort(reverse=True)
print("  province                        cells 100+   of cells    share   median longest   max")
for n100, n, nm, med, mx in rows[:14]:
    print(f"  {nm:30s} {n100:8,}   {n:8,}   {100 * n100 / n:6.2f}%   {med:8d}   {mx:8d}")
print(f"  provinces with none: {sum(1 for r in rows if r[0] == 0)} of {len(rows)}")

print("\n=== 4. Do they cluster ===")
m2 = np.zeros(mask.shape, bool)
m2[mask] = sel
lab, nlab = ndimage.label(m2, structure=np.ones((3, 3)))
sizes = ndimage.sum(m2, lab, range(1, nlab + 1)).astype(int)
order = np.argsort(sizes)[::-1]
print(f"  {nlab} connected groups; the largest 5 hold {100 * sizes[order[:5]].sum() / sel.sum():.1f}% of the cells; "
      f"{int((sizes == 1).sum())} are single cells")
full_start = np.full(mask.shape, -1)
full_start[mask] = best_start
full_best = np.zeros(mask.shape, np.int32)
full_best[mask] = best
for k in order[:8]:
    yy, xx = np.where(lab == k + 1)
    pid = np.bincount(grid[yy, xx]).argmax()
    st = full_start[yy, xx]
    print(f"    {sizes[k]:5d} cells  lon {slon[xx].min():.2f}..{slon[xx].max():.2f}  lat {slat[yy].min():.2f}..{slat[yy].max():.2f}  "
          f"{names[pid - 1]:24s} start {ym[st.min()]}..{ym[st.max()]}  longest {full_best[yy, xx].max()}")

print("\n=== 5. Is the whole record shifted against the baseline? All Indonesian cells, SPI-12 ===")
print("  period       mean SPI-12   share < -1.0   share > +1.0")
for a, b in ((1950, 1959), (1960, 1969), (1970, 1979), (1980, 1990), (1991, 2000), (2001, 2010), (2011, 2020), (2021, 2025)):
    seg = x[(years >= a) & (years <= b)]
    f = np.isfinite(seg)
    print(f"  {a}-{b}   {np.nanmean(seg):+10.3f}   {100 * (seg[f] < -1).mean():10.2f}%   {100 * (seg[f] > 1).mean():10.2f}%")
seg = x[(years >= 1991) & (years <= 2020)]
print(f"  inside baseline 1991-2020: mean {np.nanmean(seg):+.3f}, sd {np.nanstd(seg):.3f}")
seg = x[years < 1991]
print(f"  before baseline 1950-1990: mean {np.nanmean(seg):+.3f}, sd {np.nanstd(seg):.3f}")

# ---- precipitation behind it
del spi
ppt, _, _, tp, pvar, pattrs = load_window(PPT)
print(f"\n=== 6. Precipitation behind it ({pvar}, units {pattrs.get('units')})  [{time.time() - t0:.0f}s] ===")
assert len(tp) == nt and (tp == tt).all(), "ppt and SPI time axes differ"
p = ppt[:, mask]
del ppt
ny = nt // 12
ann = p.reshape(ny, 12, nc).sum(axis=1)          # annual total per cell
yy = years.reshape(ny, 12)[:, 0]
base = ann[(yy >= 1991) & (yy <= 2020)].mean(axis=0)
rel = ann / base                                  # ratio to the cell's own baseline mean
print("  annual precipitation as a ratio to each cell's own 1991-2020 mean, median across cells")
print(f"  period       cells with {LONG}+ run   all other cells")
for a, b in ((1950, 1954), (1955, 1959), (1960, 1964), (1965, 1969), (1970, 1974), (1975, 1979), (1980, 1984),
             (1985, 1990), (1991, 2000), (2001, 2010), (2011, 2020), (2021, 2025)):
    k = (yy >= a) & (yy <= b)
    print(f"  {a}-{b}   {np.nanmedian(rel[k][:, sel]):12.3f}   {np.nanmedian(rel[k][:, ~sel]):14.3f}")
# interannual variability: is the early record smoother or rougher?
cv_early = np.nanstd(ann[yy < 1991], axis=0) / np.nanmean(ann[yy < 1991], axis=0)
cv_base = np.nanstd(ann[(yy >= 1991) & (yy <= 2020)], axis=0) / base
print(f"  interannual CV of annual precipitation, median across cells: 1950-1990 {np.nanmedian(cv_early):.3f}, "
      f"1991-2020 {np.nanmedian(cv_base):.3f}")
print(f"    same, cells with {LONG}+ run: 1950-1990 {np.nanmedian(cv_early[sel]):.3f}, 1991-2020 {np.nanmedian(cv_base[sel]):.3f}")
# biggest year-to-year step in the median ratio of affected cells
series = np.nanmedian(rel[:, sel], axis=1)
other = np.nanmedian(rel[:, ~sel], axis=1)
print("  yearly median ratio, affected cells (other cells):")
for i in range(0, ny, 6):
    print("    " + "  ".join(f"{yy[j]}:{series[j]:.2f}({other[j]:.2f})" for j in range(i, min(i + 6, ny))))

# ---- map
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    os.makedirs(FIG, exist_ok=True)
    fig, axes = plt.subplots(2, 1, figsize=(13, 9), constrained_layout=True)
    a = np.where(mask, full_best, np.nan).astype(float)
    im = axes[0].pcolormesh(slon, slat, a, cmap="magma_r", vmin=0, vmax=120, shading="auto")
    axes[0].set_title("Longest run of months with SPI-12 below -1.0, per cell (TerraClimate v1.1, 1950-2025, baseline 1991-2020)")
    fig.colorbar(im, ax=axes[0], label="months (capped at 120)", shrink=0.8)
    s = np.where(mask & (full_best >= MID), years[np.clip(full_start, 0, nt - 1)], np.nan).astype(float)
    im2 = axes[1].pcolormesh(slon, slat, np.where(mask, 0.0, np.nan), cmap="Greys", vmin=0, vmax=4, shading="auto")
    im2 = axes[1].pcolormesh(slon, slat, s, cmap="viridis", vmin=1950, vmax=2025, shading="auto")
    axes[1].set_title(f"Start year of that run, cells where it lasts {MID} months or more")
    fig.colorbar(im2, ax=axes[1], label="start year", shrink=0.8)
    for ax in axes:
        ax.set_aspect("equal")
        ax.set_xlabel("longitude")
        ax.set_ylabel("latitude")
    out = os.path.abspath(os.path.join(FIG, "spi12_longest_dry_run.png"))
    fig.savefig(out, dpi=130)
    print(f"\nmap written: {out}")
except Exception as e:  # noqa: BLE001
    print("map not written:", repr(e)[:200])

print(f"done in {time.time() - t0:.0f}s")
