"""Independent check of step 1 share tables and of the all-touched cell sets.

Part A: for sampled adm2 and adm3 units, rebuild the unit's cell set straight
  from the full-resolution polygon (cell box intersects polygon, one cell at a
  time) and compare with the rows of weights_adm{n}.npz.
Part B: for sampled (index, scale, level, unit, month), read that month from the
  source cube with netCDF4, classify with thresholds written out here (not
  imported from the pipeline), compute area shares and the mean, and compare
  with the stored tables.
Part C: stored maps against the source for sampled months.

Run from the repository root: python checks/check_step1_shares.py
"""
import gzip
import json
import sys
from pathlib import Path

import geopandas as gpd
import netCDF4
import numpy as np
import pandas as pd
import shapely
import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline import config as C  # noqa: E402

SEED = 4417
rng = np.random.default_rng(SEED)
print("seed", SEED)

grid = xr.open_dataset(C.STEP0 / "grid.nc")
lat, lon = grid["lat"].values, grid["lon"].values
land = grid["land"].values.astype(bool)
area = grid["cell_area_km2"].values.astype(np.float64)
idn = grid["idn_fraction"].values
ny, nx = land.shape
dy, dx = abs(lat[1] - lat[0]), abs(lon[1] - lon[0])
man = json.load(open(C.STEP1 / "manifest.json", encoding="utf-8"))
W = {n: np.load(C.STEP0 / f"weights_adm{n}.npz") for n in (1, 2, 3)}
U = {n: pd.read_csv(C.STEP0 / f"units_adm{n}.csv", dtype={"code": str}) for n in (1, 2, 3)}


def members(n, uid):
    w = W[n]
    c = w["cell"][w["unit"] == uid].astype(np.int64)
    return np.sort(c[land.ravel()[c]])


# ---------------------------------------------------------------- A
print("\n=== A. all-touched cell sets against the polygon ===")
print("  level code       name                     stored  rebuilt  only stored  only rebuilt")
bad_a = 0
for n, field in ((2, "KDPKAB"), (3, "KDCPUM")):
    u = U[n]
    pool = u[(u["n_cells"] > 0) & ~u["code"].str.startswith("U") & ~u["code"].str.contains("-")]
    small = pool.nsmallest(40, "n_cells")          # the 40 smallest coded units: where a touched-only cell matters most
    pick = pd.concat([small.sample(2, random_state=int(rng.integers(1e9))),
                      pool.drop(small.index).sample(2, random_state=int(rng.integers(1e9)))])
    g = gpd.read_file(C.BOUNDARY.format(n=n), engine="pyogrio", columns=[field])
    code = g[field].astype("string").str.replace(".", "", regex=False)
    for _, r in pick.iterrows():
        selg = (code == r["code"]).fillna(False).to_numpy(dtype=bool)
        geom = shapely.union_all(g.geometry.values[selg])
        x0, y0, x1, y1 = geom.bounds
        rebuilt = []
        for j in np.where((lat + dy / 2 >= y0) & (lat - dy / 2 <= y1))[0]:
            for i in np.where((lon + dx / 2 >= x0) & (lon - dx / 2 <= x1))[0]:
                if land[j, i] and geom.intersects(shapely.box(lon[i] - dx / 2, lat[j] - dy / 2, lon[i] + dx / 2, lat[j] + dy / 2)):
                    rebuilt.append(j * nx + i)
        st = set(members(n, int(r["id"])).tolist())
        rb = set(rebuilt)
        bad_a += len(st ^ rb)
        print(f"  adm{n}  {r['code']:10s} {str(r['name'])[:24]:24s} {len(st):6d}  {len(rb):7d}  {len(st - rb):11d}  {len(rb - st):12d}"
              f"   (csv n_cells {int(r['n_cells'])})")
print(f"  cells differing in total: {bad_a}")

# ---------------------------------------------------------------- B
print("\n=== B. shares and mean against the source cube ===")
SRC = {"spi": (C.SPI_FILE, C.SPI_VAR), "spei": (C.SPEI_FILE, C.SPEI_VAR), "eddi": (C.EDDI_FILE, C.EDDI_VAR)}
layers = sorted(man["layers"])
worst_share = worst_mean = 0.0
print("  layer   level unit  name                     month     cells valid  share diff (half-steps)  mean stored / rebuilt")
for _ in range(14):
    tag = layers[int(rng.integers(len(layers)))]
    L = man["layers"][tag]
    index, scale = L["index"], L["scale"]
    n = int(rng.choice([1, 2, 3]))
    u = U[n][U[n]["n_cells"] > 0]
    r = u.iloc[int(rng.integers(len(u)))]
    t = int(rng.integers(0, 912))
    cells = members(n, int(r["id"]))
    nc = netCDF4.Dataset(SRC[index][0].format(n=scale))
    flat, flon = nc["lat"][:], nc["lon"][:]
    j0 = int(np.argmin(np.abs(flat - lat[0])))
    i0 = int(np.argmin(np.abs(flon - lon[0])))
    v = np.ma.filled(nc[SRC[index][1].format(n=scale)][t, j0:j0 + ny, i0:i0 + nx].astype("float64"), np.nan).ravel()[cells]
    if index == "eddi":
        cat = np.ma.filled(nc[C.EDDI_CAT_VAR][t, j0:j0 + ny, i0:i0 + nx].astype("float64"), np.nan).ravel()[cells]
        cls = np.where(np.isfinite(cat), cat + 1, 0).astype(int)
        ncls = 11
    else:
        cls = np.zeros(len(v), int)
        f = np.isfinite(v)
        for code, lo_, hi_, lo_in, hi_in in ((1, -np.inf, -2.0, True, True), (2, -2.0, -1.5, False, True), (3, -1.5, -1.0, False, True),
                                             (4, -1.0, 1.0, False, False), (5, 1.0, 1.5, True, False), (6, 1.5, 2.0, True, False),
                                             (7, 2.0, np.inf, True, True)):
            a = (v >= lo_) if lo_in else (v > lo_)
            b = (v <= hi_) if hi_in else (v < hi_)
            cls[f & a & b] = code
        ncls = 7
    nc.close()
    w = area.ravel()[cells]
    ok = cls > 0
    tbl = np.load(C.STEP1 / "shares" / f"{tag}_adm{n}.npz")
    E = man["share_encoding"]["per_level"][f"adm{n}"]
    raw = tbl["share"][t, int(r["id"]) - 1]
    stored = raw.astype(float)
    rm = int(tbl["mean"][t, int(r["id"]) - 1])
    smean = float("nan") if rm == man["share_encoding"]["mean_missing"] else rm / E["mean_scale"]
    if ok.sum() == 0:
        res = "all missing: stored " + ("missing OK" if (raw == E["share_missing"]).all() and np.isnan(smean) else "NOT missing  <-- FAIL")
        print(f"  {tag:7s} adm{n} {int(r['id']):5d} {str(r['name'])[:24]:24s} t={t:3d}  {len(cells):5d}     0  {res}")
        continue
    mine = np.array([w[cls == c].sum() for c in range(1, ncls + 1)]) / w[ok].sum()
    d = float(np.abs(stored / E["share_scale"] - mine).max()) * (E["share_scale"] * 2)   # in units of half a storage step
    mm = float((w[ok] * v[ok]).sum() / w[ok].sum())
    worst_share = max(worst_share, d)
    worst_mean = max(worst_mean, abs(mm - smean) * E["mean_scale"] * 2)
    print(f"  {tag:7s} adm{n} {int(r['id']):5d} {str(r['name'])[:24]:24s} t={t:3d}  {len(cells):5d} {int(ok.sum()):5d}  {d:.6f}"
          f"          {smean:+.4f} / {mm:+.4f}")
print(f"  worst share difference {worst_share:.3f} and worst mean difference {worst_mean:.3f}, both in half storage steps: "
      f"at or below 1.0 means the stored value is the correct rounding")

# ---------------------------------------------------------------- C
print("\n=== C. stored maps against the source ===")
drawn = np.fromfile(C.STEP1 / "maps" / "cells.u32", dtype="<u4").astype(np.int64)
print(f"  drawn cells {len(drawn):,}; all land {bool(land.ravel()[drawn].all())}; all at least half inside {bool((idn.ravel()[drawn] >= 0.5).all())}")
for _ in range(4):
    tag = layers[int(rng.integers(len(layers)))]
    L = man["layers"][tag]
    t = int(rng.integers(0, 912))
    y, m = 1950 + t // 12, t % 12
    blk = np.frombuffer(gzip.open(C.STEP1 / "maps" / tag / f"{y}.u8.gz").read(), dtype=np.uint8).reshape(12, len(drawn))[m]
    nc = netCDF4.Dataset(SRC[L["index"]][0].format(n=L["scale"]))
    j0 = int(np.argmin(np.abs(nc["lat"][:] - lat[0])))
    i0 = int(np.argmin(np.abs(nc["lon"][:] - lon[0])))
    name = C.EDDI_CAT_VAR if L["index"] == "eddi" else SRC[L["index"]][1].format(n=L["scale"])
    v = np.ma.filled(nc[name][t, j0:j0 + ny, i0:i0 + nx].astype("float64"), np.nan).ravel()[drawn]
    nc.close()
    if L["index"] == "eddi":
        ref = np.where(np.isfinite(v), v + 1, 0).astype(int)
    else:
        ref = np.where(~np.isfinite(v), 0, np.where(v <= -2, 1, np.where(v <= -1.5, 2, np.where(v <= -1, 3, np.where(v < 1, 4, np.where(v < 1.5, 5, np.where(v < 2, 6, 7)))))))
    print(f"  {tag} {y}-{m + 1:02d}: cells differing {int((blk != ref).sum())} of {len(drawn):,}; no-data cells {int((blk == 0).sum()):,}")
