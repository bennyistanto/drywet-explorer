"""Do rain gauges show the TerraClimate drift (dry before 1991) and the Riau step (1970-1983)?

Gauges: wxgrid consolidated daily rainfall export, Indonesia 1950-2021
(F:/temp/station/compiled/export, read-only). TerraClimate v1.1 monthly ppt at
the cell holding each gauge. Both as annual totals, each divided by its own
mean over the SAME 1991-2020 years, so the two ratios are directly comparable.

A site-year counts when it has at least MIN_DAYS observed days; its total is
mean daily rain times days in the year. Days flagged above_max, below_min,
src_suspect, code_suspect or unharmonised_source are dropped. Unmeasurable
(trace) days count as observed with 0 mm.

Run: python analysis/gauges_vs_terraclimate.py
"""
import time

import numpy as np
import pandas as pd
import xarray as xr

EXP = r"F:\temp\station\compiled\export\idn_rr_daily_1950_2021_"
TC = r"G:\temp\terraclimate\nc\wld_cli_terraclimate_ppt_1950_2025.nc"
W, E, S, N = 94.5, 141.5, -11.5, 6.5
MIN_DAYS = 330
MIN_BASE_YEARS = 10
DROP = ("above_max", "below_min", "src_suspect", "code_suspect", "unharmonised_source")
BLOCK = (98.8, 103.8, -1.0, 3.7)   # lon_min, lon_max, lat_min, lat_max: the Riau block from long_runs_locate
PERIODS = ((1950, 1959), (1960, 1969), (1970, 1979), (1980, 1990), (1991, 2000), (2001, 2010), (2011, 2021))

t0 = time.time()
sites = pd.read_csv(EXP + "sites.csv").set_index("site_id")
df = pd.read_csv(EXP + "long.csv.gz", usecols=["site_id", "date", "rr_mm", "flag"], dtype={"flag": "string"})
print(f"gauge rows {len(df):,}, sites {df.site_id.nunique()}  [{time.time() - t0:.0f}s]")
flag = df["flag"].fillna("")
bad = np.zeros(len(df), bool)
for f in DROP:
    bad |= flag.str.contains(f, regex=False).to_numpy()
trace = flag.str.contains("unmeasurable", regex=False).to_numpy()
print(f"  dropped for flags: {int(bad.sum()):,}; unmeasurable days counted as 0 mm: {int(trace.sum()):,}")
df = df[~bad].copy()
df.loc[trace[~bad], "rr_mm"] = 0.0
df = df[df["rr_mm"].notna()]
df["year"] = df["date"].str.slice(0, 4).astype(int)
gy = df.groupby(["site_id", "year"])["rr_mm"].agg(["count", "mean"]).reset_index()
gy = gy[gy["count"] >= MIN_DAYS]
gy["days"] = np.where((gy["year"] % 4 == 0), 366, 365)
gy["gauge_mm"] = gy["mean"] * gy["days"]
print(f"  site-years with >= {MIN_DAYS} days: {len(gy):,} at {gy.site_id.nunique()} sites")

# ---- TerraClimate annual totals 1950-2021 for the window
ds = xr.open_dataset(TC)
lat = ds["lat"].values
lon = ds["lon"].values
li = np.where((lat >= S) & (lat <= N))[0]
lo = np.where((lon >= W) & (lon <= E))[0]
sub = ds["ppt"].isel(lat=slice(li.min(), li.max() + 1), lon=slice(lo.min(), lo.max() + 1))
slat = sub["lat"].values
slon = sub["lon"].values
tyr = ds["time"].values.astype("datetime64[Y]").astype(int) + 1970
years = np.arange(1950, 2022)
ann = np.full((len(years), len(slat), len(slon)), np.nan, np.float32)
for i, y in enumerate(years):
    idx = np.where(tyr == y)[0]
    ann[i] = sub.isel(time=slice(int(idx[0]), int(idx[-1]) + 1)).values.sum(axis=0)
ds.close()
land = np.isfinite(ann).all(axis=0)
print(f"TerraClimate annual totals {ann.shape}  [{time.time() - t0:.0f}s]")


def cell_of(la, lo_):
    iy = int(np.argmin(np.abs(slat - la)))
    ix = int(np.argmin(np.abs(slon - lo_)))
    if land[iy, ix]:
        return iy, ix, 0
    best = None
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            y, x = iy + dy, ix + dx
            if 0 <= y < len(slat) and 0 <= x < len(slon) and land[y, x]:
                d = dy * dy + dx * dx
                if best is None or d < best[2]:
                    best = (y, x, d)
    return best if best else (None, None, None)


rows = []
moved = nocell = 0
for sid, grp in gy.groupby("site_id"):
    if sid not in sites.index:
        continue
    la, lo_ = float(sites.at[sid, "lat"]), float(sites.at[sid, "lon"])
    if not (S <= la <= N and W <= lo_ <= E):
        continue
    iy, ix, d = cell_of(la, lo_)
    if iy is None:
        nocell += 1
        continue
    moved += int(d > 0)
    yrs = grp["year"].to_numpy()
    g = grp["gauge_mm"].to_numpy()
    t = ann[yrs - 1950, iy, ix].astype(float)
    b = (yrs >= 1991) & (yrs <= 2020)
    if b.sum() < MIN_BASE_YEARS:
        continue
    for y, gv, tv in zip(yrs, g / g[b].mean(), t / t[b].mean()):
        rows.append((sid, int(y), gv, tv, la, lo_))
r = pd.DataFrame(rows, columns=["site_id", "year", "gauge", "tc", "lat", "lon"])
print(f"sites with >= {MIN_BASE_YEARS} baseline years and a land cell: {r.site_id.nunique()} "
      f"({moved} matched to a neighbouring cell, {nocell} with no land cell within 2 cells); site-years {len(r):,}")
r["block"] = (r.lon >= BLOCK[0]) & (r.lon <= BLOCK[1]) & (r.lat >= BLOCK[2]) & (r.lat <= BLOCK[3])


def table(d, title):
    print(f"\n=== {title} ===")
    print("  period      sites  site-years   gauge ratio   TerraClimate ratio   TC minus gauge   (median of site means)")
    for a, b in PERIODS:
        k = d[(d.year >= a) & (d.year <= b)]
        if k.empty:
            print(f"  {a}-{b}      0")
            continue
        m = k.groupby("site_id")[["gauge", "tc"]].mean()
        print(f"  {a}-{b}   {len(m):5d}   {len(k):8,}   {m.gauge.median():10.3f}   {m.tc.median():14.3f}   "
              f"{(m.tc - m.gauge).median():+12.3f}")


table(r, "A. All Indonesia: ratio to own 1991-2020 mean")
table(r[~r.block], "A2. All Indonesia outside the Riau block")

# same sites in both eras, so the comparison is not a change of network
early = r[(r.year >= 1950) & (r.year <= 1980)].groupby("site_id").size()
keep = early[early >= 10].index
rk = r[r.site_id.isin(keep)]
table(rk, f"A3. Only the {len(keep)} sites with 10+ valid years in 1950-1980")

print("\n=== B. Riau block (lon %.1f..%.1f, lat %.1f..%.1f) ===" % BLOCK)
rb = r[r.block]
print(f"  sites in the block with a usable baseline: {rb.site_id.nunique()}")
print("  site     name                          lon      lat   yrs70-83  gauge70-83  TC70-83   yrs84-90  gauge84-90  TC84-90")
for sid, grp in rb.groupby("site_id"):
    a = grp[(grp.year >= 1970) & (grp.year <= 1983)]
    b = grp[(grp.year >= 1984) & (grp.year <= 1990)]
    if a.empty and b.empty:
        continue
    f = lambda d, c: f"{d[c].mean():8.3f}" if len(d) else "       -"  # noqa: E731
    print(f"  {sid}  {str(sites.at[sid, 'name'])[:28]:28s} {grp.lon.iloc[0]:7.2f}  {grp.lat.iloc[0]:6.2f}   "
          f"{len(a):5d}   {f(a, 'gauge')}  {f(a, 'tc')}   {len(b):5d}   {f(b, 'gauge')}  {f(b, 'tc')}")
print("  year: sites / gauge median / TerraClimate median")
for i in range(1966, 1991, 5):
    out = []
    for y in range(i, min(i + 5, 1991)):
        k = rb[rb.year == y]
        out.append(f"{y}: {len(k)} / {k.gauge.median():.2f} / {k.tc.median():.2f}" if len(k) else f"{y}: 0")
    print("    " + "   ".join(out))
table(rb, "B2. Riau block by period")

print("\n=== C. Do annual anomalies agree? Per-site correlation of gauge and TerraClimate ratios ===")
for a, b in ((1950, 1983), (1984, 2021)):
    cs = []
    for sid, grp in r[(r.year >= a) & (r.year <= b)].groupby("site_id"):
        if len(grp) >= 10:
            cs.append((np.corrcoef(grp.gauge, grp.tc)[0, 1], bool(grp.block.iloc[0])))
    c = np.array([x[0] for x in cs])
    blk = np.array([x[1] for x in cs])
    msg = f"  {a}-{b}: {len(c)} sites with 10+ years, median r {np.nanmedian(c):.3f}, p25 {np.nanpercentile(c, 25):.3f}"
    if blk.any():
        msg += f"; in the block {int(blk.sum())} sites, median r {np.nanmedian(c[blk]):.3f}"
    print(msg)
print(f"\ndone in {time.time() - t0:.0f}s")
