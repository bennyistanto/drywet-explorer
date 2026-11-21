"""Step 0b: small display boundaries from the 340 to 770 MB originals.

Writes data/step0/admin{1,2,3}.geojson with the same ids and codes as
units_adm{n}.csv from step0_grid, so a drawn outline and a statistics row
refer to the same unit.

Simplification uses shapely.coverage_simplify, which keeps shared edges shared
(no slivers or gaps between neighbours) when the input is a valid polygon
coverage. If the input is not, it falls back to per-polygon simplification and
says so. Display only: no statistic is computed from these geometries.

Run from the repository root, after step0_grid: python -m pipeline.step0_boundaries
"""
import json
import time

import geopandas as gpd
import pandas as pd
import shapely

from datetime import datetime

from . import config as C
from .admin_codes import adm2_codes, adm3_codes, digits
from .step0_grid import provenance, versions

# One tolerance for all three levels (owner, 2026-11-21), about 333 m at the equator. Two reasons:
#   - at the map's maximum zoom (16 times) one screen pixel is about 360 m, so this is as sharp as can be seen;
#   - with one tolerance a border shared by a province, a kabupaten and a kecamatan is simplified the same way
#     in each file, so the three outlines lie on top of each other instead of side by side.
# Measured cost against the earlier 1.1 km / 550 m / 330 m: adm1 3.1 -> 5.0 MB, adm2 5.5 -> 7.5 MB, adm3 unchanged
# (temp/script/analysis/boundary_detail_tradeoff.py). Halve it only together with a higher zoom limit.
TOLERANCE_DEG = {1: 0.003, 2: 0.003, 3: 0.003}
T0 = time.time()


def log(msg):
    print(f"[{time.time() - T0:5.0f}s] {msg}", flush=True)


def simplify(geoms, tol):
    try:
        out = shapely.coverage_simplify(geoms.values, tol)
        return gpd.GeoSeries(out, index=geoms.index, crs=geoms.crs), "coverage_simplify"
    except Exception as e:  # noqa: BLE001
        log(f"  coverage_simplify failed ({type(e).__name__}: {str(e)[:80]}); per-polygon fallback")
        return geoms.simplify(tol, preserve_topology=True), "per_polygon"


def main():
    report = {}
    for n in (1, 2, 3):
        units = pd.read_csv(C.STEP0 / f"units_adm{n}.csv", dtype={"code": str})
        g = gpd.read_file(C.BOUNDARY.format(n=n), engine="pyogrio")
        nv0 = int(shapely.get_num_coordinates(g.geometry.values).sum())
        if n == 1:
            g["code"] = [digits(v) for v in g["a1bps"]]
        elif n == 2:
            g["code"] = adm2_codes(g["KDPKAB"])
        else:
            g["code"] = adm3_codes(g["KDCPUM"], g["WADMKC"], g["NAMOBJ"])[0]
        g = g.merge(units[["id", "code", "name"]], on="code", how="left", validate="many_to_one")
        assert g["id"].notna().all(), f"adm{n}: boundary features without a unit row"
        geom, how = simplify(g.geometry, TOLERANCE_DEG[n])
        geom = geom.make_valid()
        out = gpd.GeoDataFrame(dict(id=g["id"].astype(int), code=g["code"], name=g["name"]), geometry=geom, crs=g.crs)
        empty = int(out.geometry.is_empty.sum())
        out = out[~out.geometry.is_empty]
        path = C.STEP0 / f"admin{n}.geojson"
        out.to_file(path, driver="GeoJSON", COORDINATE_PRECISION=4)
        nv1 = int(shapely.get_num_coordinates(out.geometry.values).sum())
        report[f"adm{n}"] = dict(output=path.name, features=int(len(out)), dropped_empty=empty, vertices_in=nv0,
                                 vertices_out=nv1, tolerance_deg=TOLERANCE_DEG[n], method=how,
                                 invalid_after_rounding=int((~gpd.read_file(path).geometry.is_valid).sum()),
                                 bytes=path.stat().st_size, source=provenance(C.BOUNDARY.format(n=n)))
        log(f"adm{n}: {len(out)} features ({empty} emptied), vertices {nv0:,} -> {nv1:,}, {how}, "
            f"{path.stat().st_size / 1e6:.2f} MB")
    report = dict(step="step0_boundaries", script="pipeline/step0_boundaries.py",
                  created=datetime.now().isoformat(timespec="seconds"), use="display only; no statistic reads these",
                  ids_from="units_adm{n}.csv written by step0_grid", coordinate_precision=4, versions=versions(),
                  layers=report)
    with open(C.STEP0 / "boundaries_report.json", "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)


if __name__ == "__main__":
    main()
