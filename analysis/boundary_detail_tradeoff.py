"""What does more boundary detail cost? Simplify each admin level at several tolerances and
report vertices and file size (raw, and gzip as a web server would send it).

Writes only to the scratch folder given as argument; the site's files are not touched.
Run from the repository root: python analysis/boundary_detail_tradeoff.py <scratch folder>
"""
import gzip
import sys
import time
from pathlib import Path

import geopandas as gpd
import shapely

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline import config as C  # noqa: E402

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
CURRENT = {1: 0.01, 2: 0.005, 3: 0.003}
TRY = [0.003, 0.0015, 0.00075]
t0 = time.time()
print("degrees to metres at the equator: 0.001 deg is about 111 m")
print("level  tolerance   about    vertices     raw MB   gzip MB   note")
for n in (1, 2, 3):
    g = gpd.read_file(C.BOUNDARY.format(n=n), engine="pyogrio", columns=[])
    nv0 = int(shapely.get_num_coordinates(g.geometry.values).sum())
    for tol in sorted(set([CURRENT[n]] + TRY), reverse=True):
        geom = gpd.GeoSeries(shapely.coverage_simplify(g.geometry.values, tol), crs=g.crs).make_valid()
        f = out / f"adm{n}_{tol}.geojson"
        gpd.GeoDataFrame(dict(id=range(len(geom))), geometry=geom, crs=g.crs).to_file(f, driver="GeoJSON", COORDINATE_PRECISION=5)
        raw = f.read_bytes()
        nv = int(shapely.get_num_coordinates(geom.values).sum())
        print(f"adm{n}   {tol:<9}  {tol * 111000:5.0f} m  {nv:9,}   {len(raw) / 1e6:7.2f}   {len(gzip.compress(raw, 6)) / 1e6:7.2f}   "
              f"{'current' if tol == CURRENT[n] else ''}  [{time.time() - t0:.0f}s]", flush=True)
        f.unlink()
    print(f"adm{n}   original              {nv0:9,}")
