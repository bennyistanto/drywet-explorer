"""Is the 1984 step in Riau, and the country-wide drift, also in CHIRPS?

Compares annual precipitation totals, 1981-2025, province means:
TerraClimate v1.1 monthly ppt against CHIRPS v3 dekadal precipitation.
Each dataset is expressed as a ratio to its own 1991-2020 mean, and the two
are divided year by year. Read-only on inputs.

If the step is a TerraClimate artefact: TerraClimate/CHIRPS in Riau should sit
well below 1 in 1981-1983 and near 1 from 1984, while control provinces stay flat.

Run: python analysis/chirps_vs_terraclimate_step.py
"""
import time

import geopandas as gpd
import numpy as np
import xarray as xr
from rasterio import features
from rasterio.transform import from_origin

W, E, S, N = 94.5, 141.5, -11.5, 6.5
TC = r"G:\temp\terraclimate\nc\wld_cli_terraclimate_ppt_1950_2025.nc"
CH = r"E:\temp\chirps\dekad\wld_cli_chirps3_dekad_1981_2025.nc"
ADM1 = r"E:\temp\idn-bnd\idn_bnd_adm1.shp"
PROV = ["Riau", "Sumatera Utara", "Kalimantan Barat", "Sumatera Selatan", "Kalimantan Tengah", "Jawa Tengah"]
Y0, Y1 = 1981, 2025


def open_window(path):
    ds = xr.open_dataset(path)
    var = [v for v in ds.data_vars if ds[v].ndim == 3][0]
    latn = "lat" if "lat" in ds.coords else "latitude"
    lonn = "lon" if "lon" in ds.coords else "longitude"
    lat = ds[latn].values
    lon = ds[lonn].values
    li = np.where((lat >= S) & (lat <= N))[0]
    lo = np.where((lon >= W) & (lon <= E))[0]
    sub = ds[var].isel({latn: slice(li.min(), li.max() + 1), lonn: slice(lo.min(), lo.max() + 1)})
    print(f"  {path.split(chr(92))[-1]}: var {var}, units {ds[var].attrs.get('units')}, "
          f"chunks {ds[var].encoding.get('chunksizes')}, window {sub.shape[1]} x {sub.shape[2]}, "
          f"time {str(ds['time'].values[0])[:10]}..{str(ds['time'].values[-1])[:10]} n={ds.sizes['time']}")
    return ds, sub, sub[latn].values, sub[lonn].values


def annual_totals(sub, per_year):
    """Sum each calendar year from contiguous slabs. Returns years and (year, lat, lon)."""
    t = sub["time"].values
    yrs = t.astype("datetime64[Y]").astype(int) + 1970
    out_y, out = [], []
    for y in range(Y0, Y1 + 1):
        idx = np.where(yrs == y)[0]
        if len(idx) != per_year:
            print(f"    year {y}: {len(idx)} steps, expected {per_year}; skipped")
            continue
        a = sub.isel(time=slice(int(idx[0]), int(idx[-1]) + 1)).values.astype(np.float64)
        out.append(np.where(np.isfinite(a).all(axis=0), a.sum(axis=0), np.nan))
        out_y.append(y)
    return np.array(out_y), np.stack(out)


def province_grid(g, lat, lon):
    dx = abs(float(lon[1] - lon[0]))
    dy = abs(float(lat[1] - lat[0]))
    north_first = lat[0] > lat[-1]
    top = float(lat.max()) + dy / 2
    tr = from_origin(float(lon.min()) - dx / 2, top, dx, dy)
    grid = features.rasterize(zip(g.geometry, range(1, len(g) + 1)), out_shape=(len(lat), len(lon)),
                              transform=tr, fill=0, dtype="int32")
    return grid if north_first else grid[::-1]


def series(ann, grid, lat, pid):
    """Area-weighted mean annual total over one province (pid) or all Indonesia (pid None)."""
    m = (grid > 0) if pid is None else (grid == pid)
    m = m & np.isfinite(ann).all(axis=0)
    w = np.cos(np.deg2rad(lat))[:, None] * np.ones(grid.shape)
    return (ann[:, m] * w[m]).sum(axis=1) / w[m].sum(), int(m.sum())


t0 = time.time()
g = gpd.read_file(ADM1, engine="pyogrio")
names = [str(x) for x in g["a1name"]]
print("inputs:")
ds1, s1, lat1, lon1 = open_window(TC)
ds2, s2, lat2, lon2 = open_window(CH)
y1, a1 = annual_totals(s1, 12)
print(f"  TerraClimate annual totals {a1.shape}  [{time.time() - t0:.0f}s]")
y2, a2 = annual_totals(s2, 36)
print(f"  CHIRPS annual totals {a2.shape}  [{time.time() - t0:.0f}s]")
ds1.close()
ds2.close()
assert (y1 == y2).all(), "year axes differ"
yy = y1
g1 = province_grid(g, lat1, lon1)
g2 = province_grid(g, lat2, lon2)
base = (yy >= 1991) & (yy <= 2020)
PERIODS = ((1981, 1983), (1984, 1990), (1991, 2000), (2001, 2010), (2011, 2020), (2021, 2025))

for nm in PROV + [None]:
    pid = None if nm is None else names.index(nm) + 1
    tc, n1 = series(a1, g1, lat1, pid)
    ch, n2 = series(a2, g2, lat2, pid)
    rt = tc / tc[base].mean()
    rc = ch / ch[base].mean()
    print(f"\n=== {nm or 'All Indonesia'}  (cells: TerraClimate {n1:,}, CHIRPS {n2:,}) ===")
    print(f"  1991-2020 mean annual total: TerraClimate {tc[base].mean():.0f} mm, CHIRPS {ch[base].mean():.0f} mm")
    print(f"  correlation of annual totals 1984-2025: {np.corrcoef(tc[yy >= 1984], ch[yy >= 1984])[0, 1]:.3f}")
    print("  period      TC ratio to own baseline   CHIRPS ratio to own baseline   TC mm / CHIRPS mm")
    for a, b in PERIODS:
        k = (yy >= a) & (yy <= b)
        print(f"  {a}-{b}   {rt[k].mean():14.3f}   {rc[k].mean():24.3f}   {(tc[k] / ch[k]).mean():18.3f}")
    if nm in ("Riau", "Sumatera Utara", "Sumatera Selatan", None):
        print("  year: TC ratio / CHIRPS ratio / TC over CHIRPS")
        for i in range(0, 12, 4):
            print("    " + "   ".join(f"{yy[j]}: {rt[j]:.2f} / {rc[j]:.2f} / {tc[j] / ch[j]:.2f}" for j in range(i, i + 4)))

print(f"\ndone in {time.time() - t0:.0f}s")
