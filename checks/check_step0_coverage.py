"""Independent check of step 0 coverage fractions.

For randomly chosen units, recompute each cell's coverage as the exact area of
(polygon intersect cell box) / (cell box area) with shapely on the full-resolution
polygon, and compare with the sub-cell estimate stored in weights_adm{n}.npz.
Shares none of step0_grid's rasterisation code.

Run from the repository root: python checks/check_step0_coverage.py
"""
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline import config as C  # noqa: E402

SEED = 20261120
N_PER_LEVEL = 6

grid = xr.open_dataset(C.STEP0 / "grid.nc")
lat = grid["lat"].values
lon = grid["lon"].values
land = grid["land"].values.astype(bool)
ny, nx = land.shape
dy = abs(lat[1] - lat[0])
dx = abs(lon[1] - lon[0])
rng = np.random.default_rng(SEED)
print(f"seed {SEED}; grid {ny} x {nx}")

worst = 0.0
for n, field, want in ((2, "KDPKAB", 4), (3, "KDCPUM", 6)):
    units = pd.read_csv(C.STEP0 / f"units_adm{n}.csv", dtype={"code": str})
    w = np.load(C.STEP0 / f"weights_adm{n}.npz")
    k = int(w["supersample"])
    g = gpd.read_file(C.BOUNDARY.format(n=n), engine="pyogrio", columns=[field])
    code = g[field].astype("string").str.replace(".", "", regex=False)
    pool = units[(units["cell_equiv"] > 0) & ~units["code"].str.startswith("U")]
    small = pool[pool["cell_equiv"] < 5]
    pick = pd.concat([pool.sample(N_PER_LEVEL - 2, random_state=int(rng.integers(1e9))),
                      small.sample(2, random_state=int(rng.integers(1e9)))])
    print(f"\n=== adm{n} ===")
    print("  code      name                      cells   stored equiv   exact equiv   diff    max |cell diff|")
    for _, u in pick.iterrows():
        sel = (code == u["code"]).fillna(False).to_numpy(dtype=bool)
        geom = shapely.union_all(g.geometry.values[sel])
        x0, y0, x1, y1 = geom.bounds
        iy = np.where((lat + dy / 2 >= y0) & (lat - dy / 2 <= y1))[0]
        ix = np.where((lon + dx / 2 >= x0) & (lon - dx / 2 <= x1))[0]
        shapely.prepare(geom)
        exact = {}
        for j in iy:
            for i in ix:
                if not land[j, i]:
                    continue
                box = shapely.box(lon[i] - dx / 2, lat[j] - dy / 2, lon[i] + dx / 2, lat[j] + dy / 2)
                if geom.intersects(box):
                    f = geom.intersection(box).area / box.area
                    if f > 0:
                        exact[j * nx + i] = f
        m = w["unit"] == u["id"]
        stored = {int(c): s / (k * k) for c, s in zip(w["cell"][m], w["subcells"][m]) if land.ravel()[c]}
        keys = set(exact) | set(stored)
        cd = max((abs(exact.get(c, 0.0) - stored.get(c, 0.0)) for c in keys), default=0.0)
        es, ss = sum(exact.values()), sum(stored.values())
        worst = max(worst, abs(es - ss) / max(es, 1e-9))
        print(f"  {u['code']:8s}  {str(u['name'])[:24]:24s} {len(keys):5d}   {ss:10.3f}   {es:10.3f}   {ss - es:+7.3f}   {cd:.3f}"
              f"   (csv {u['cell_equiv']:.3f})")
print(f"\nworst relative difference in cell equivalents: {100 * worst:.2f}%")
