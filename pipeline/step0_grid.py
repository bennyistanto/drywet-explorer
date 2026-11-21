"""Step 0: the fixed geometry everything else is computed on.

Writes to data/step0/:
  grid.nc             lat, lon, land, idn_fraction, cell_area_km2,
                      adm1_id / adm2_id / adm3_id (dominant unit per cell, 0 = none),
                      flag_step_1984, step_spi12, step_eddi12
  units_adm{1,2,3}.csv  one row per unit: id, code, name, parents, support
  weights_adm{1,2,3}.npz  membership rows: cell (flat index), unit id, subcells. Every row on a
                      land cell is a member at FULL cell area (all touched). `subcells` (of 64)
                      is a coverage estimate kept for reference; it is not a weight.
  manifest.json       sources (name, size, mtime), rules, counts, checks

Method
  Window: conventions.WINDOW on the TerraClimate 1/24 degree grid.
  Land: cells finite in the SPI-1 cube at the last time step.
  Coverage fraction: each cell is split into SUPERSAMPLE x SUPERSAMPLE sub-cells;
    a sub-cell belongs to the polygon holding its centre. Fractions are therefore
    in steps of 1/SUPERSAMPLE^2. This approximates exact polygon-cell overlap.
  Hierarchy: adm2 polygons are the reference. adm1 is the union of adm2 units by
    their province code (a1bps), so adm2 nests in adm1 exactly. adm3 comes from
    its own polygons and takes its parent from its code; how well that agrees
    with the adm2 polygons is measured and reported, not assumed.
  Cell area: exact on a sphere of radius EARTH_RADIUS_KM.
  step_1984: conventions.FLAG_STEP_1984, computed here from SPI-12 and EDDI-12.

Run from the repository root: python -m pipeline.step0_grid
"""
import json
import os
import time
from datetime import datetime

import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr
from rasterio import features
from rasterio.transform import from_origin

from . import config as C
from . import conventions as K
from .admin_codes import adm2_codes, adm3_codes, digits, prefix_code

T0 = time.time()


def log(msg):
    print(f"[{time.time() - T0:5.0f}s] {msg}", flush=True)


def provenance(path):
    """Name, folder, size and modified time. For a shapefile, the .dbf too: every code comes from it."""
    def one(p):
        st = os.stat(p)
        return dict(file=os.path.basename(p), folder=os.path.dirname(p), bytes=st.st_size,
                    modified=datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"))
    out = one(path)
    if str(path).lower().endswith(".shp"):
        dbf = str(path)[:-4] + ".dbf"
        if os.path.exists(dbf):
            out["dbf"] = one(dbf)
    return out


def versions():
    import geopandas
    import rasterio
    import shapely
    return dict(numpy=np.__version__, xarray=xr.__version__, pandas=pd.__version__, geopandas=geopandas.__version__,
                shapely=shapely.__version__, geos=shapely.geos_version_string, rasterio=rasterio.__version__,
                gdal=rasterio.__gdal_version__)


def open_window(path, var):
    ds = xr.open_dataset(path)
    lat = ds["lat"].values
    lon = ds["lon"].values
    w = K.WINDOW
    li = np.where((lat >= w["south"]) & (lat <= w["north"]))[0]
    lo = np.where((lon >= w["west"]) & (lon <= w["east"]))[0]
    sub = ds[var].isel(lat=slice(int(li.min()), int(li.max()) + 1), lon=slice(int(lo.min()), int(lo.max()) + 1))
    return ds, sub


def coverage(geoms, ids, n_units, slat, slon, k):
    """Sparse coverage table from a k x k sub-grid.

    Returns cell (flat index into the ny x nx grid), unit id, and the number of
    sub-cells of that cell whose centre falls in that unit.
    """
    ny, nx = len(slat), len(slon)
    dx = abs(float(slon[1] - slon[0]))
    dy = abs(float(slat[1] - slat[0]))
    assert slat[0] > slat[-1], "expects latitude north to south"
    tr = from_origin(float(slon[0]) - dx / 2, float(slat[0]) + dy / 2, dx / k, dy / k)
    fine = features.rasterize(zip(geoms, ids), out_shape=(ny * k, nx * k), transform=tr, fill=0,
                              dtype="int32", all_touched=False)
    fine = fine.reshape(ny, k, nx, k).transpose(0, 2, 1, 3).reshape(ny * nx, k * k)
    cell = np.repeat(np.arange(ny * nx, dtype=np.int64), k * k)
    key = cell * (n_units + 1) + fine.ravel()
    key = key[fine.ravel() > 0]
    uk, cnt = np.unique(key, return_counts=True)
    return (uk // (n_units + 1)).astype(np.int64), (uk % (n_units + 1)).astype(np.int32), cnt.astype(np.int32)


def touched_pairs(geoms, ids, land_idx, slat, slon):
    """Every (land cell, unit) pair where the polygon touches the cell at all.

    Exact: the cell's box is tested against the full-resolution polygon. This is
    the "all touched" rule the owner asked for (2026-11-20): a cell belongs to
    every unit whose polygon intersects it, however small the overlap.
    """
    import shapely

    nx = len(slon)
    dx = abs(float(slon[1] - slon[0]))
    dy = abs(float(slat[1] - slat[0]))
    r, c = np.divmod(land_idx, nx)
    boxes = shapely.box(slon[c] - dx / 2, slat[r] - dy / 2, slon[c] + dx / 2, slat[r] + dy / 2)
    garr = np.asarray(geoms.values)
    try:
        bi, gi = shapely.STRtree(garr).query(boxes, predicate="intersects")
    except Exception as e:  # noqa: BLE001  invalid input geometry
        log(f"  intersects failed on raw geometry ({type(e).__name__}); retrying on make_valid")
        bi, gi = shapely.STRtree(shapely.make_valid(garr)).query(boxes, predicate="intersects")
    return land_idx[bi].astype(np.int64), np.asarray(ids)[gi].astype(np.int32)


def add_touched(cell, unit, cnt, tcell, tunit, n_units):
    """Union of the coverage pairs and the touched pairs. A pair that is only touched has 0 sub-cells."""
    base = n_units + 1
    key = cell * base + unit
    allk = np.union1d(key, tcell * base + tunit)
    sub = np.zeros(len(allk), np.int32)
    sub[np.searchsorted(allk, key)] = cnt
    return (allk // base).astype(np.int64), (allk % base).astype(np.int32), sub, int(len(allk) - len(key))


def dominant(cell, unit, cnt, n_cells):
    """Unit with the most sub-cells in each cell; ties go to the lower id. 0 where none."""
    order = np.lexsort((unit, -cnt, cell))
    c = cell[order]
    first = np.ones(len(c), bool)
    first[1:] = c[1:] != c[:-1]
    out = np.zeros(n_cells, np.int32)
    out[c[first]] = unit[order][first]
    return out


def main():
    k = K.SUPERSAMPLE
    C.STEP0.mkdir(parents=True, exist_ok=True)
    src = {}

    # ---------------------------------------------------------------- grid
    f_spi1 = C.SPI_FILE.format(n=1)
    ds, sub = open_window(f_spi1, C.SPI_VAR.format(n=1))
    slat = sub["lat"].values.astype(np.float64)
    slon = sub["lon"].values.astype(np.float64)
    times = ds["time"].values
    assert len(times) == K.N_MONTHS, f"expected {K.N_MONTHS} months, found {len(times)}"
    assert str(times[0])[:7] == K.PERIOD[0] and str(times[-1])[:7] == K.PERIOD[1], "period differs from conventions"
    land = np.isfinite(sub.isel(time=-1).values)
    ds.close()
    src["spi_1"] = provenance(f_spi1)
    ny, nx = len(slat), len(slon)
    dx = abs(slon[1] - slon[0])
    dy = abs(slat[1] - slat[0])
    log(f"grid {ny} x {nx}, cell {dy:.6f} x {dx:.6f} deg, land cells in window {int(land.sum()):,}")

    lat_top = np.deg2rad(slat + dy / 2)
    lat_bot = np.deg2rad(slat - dy / 2)
    area_row = (K.EARTH_RADIUS_KM ** 2) * np.deg2rad(dx) * (np.sin(lat_top) - np.sin(lat_bot))
    cell_area = np.repeat(area_row[:, None], nx, axis=1)
    log(f"cell area {area_row.min():.2f} to {area_row.max():.2f} km2")

    # ---------------------------------------------------------------- adm2 (reference layer)
    f2 = C.BOUNDARY.format(n=2)
    g2 = gpd.read_file(f2, engine="pyogrio")
    src["adm2"] = provenance(f2)
    g2["code"] = adm2_codes(g2["KDPKAB"])
    n_unassigned = int(g2["code"].str.startswith("U").sum())
    assert g2["code"].is_unique, "adm2 codes are not unique"
    g2["bps"] = [digits(v) for v in g2["a2bps"]]
    g2 = g2.sort_values("code").reset_index(drop=True)
    g2["id"] = np.arange(1, len(g2) + 1)
    g2["assigned"] = ~g2["code"].str.startswith("U")
    g2["a1code"] = [digits(v) for v in g2["a1bps"]]
    log(f"adm2: {len(g2)} features, {int(g2.assigned.sum())} with a kabupaten/kota code, {n_unassigned} without")

    # ---------------------------------------------------------------- adm1 (attributes only here)
    f1 = C.BOUNDARY.format(n=1)
    g1 = gpd.read_file(f1, engine="pyogrio")
    src["adm1"] = provenance(f1)
    g1["code"] = [digits(v) for v in g1["a1bps"]]
    assert g1["code"].notna().all() and g1["code"].is_unique, "adm1 a1bps codes missing or duplicated"
    g1 = g1.sort_values("code").reset_index(drop=True)
    g1["id"] = np.arange(1, len(g1) + 1)
    id1_of = dict(zip(g1["code"], g1["id"]))
    name1_of = dict(zip(g1["a1name"].str.lower(), g1["id"]))
    alias = {"dki jakarta": "daerah khusus ibukota jakarta"}
    p1 = []
    for c, nm in zip(g2["a1code"], g2["WADMPR"]):
        pid = id1_of.get(c, 0)
        if pid == 0 and isinstance(nm, str):
            key = alias.get(nm.lower(), nm.lower())
            pid = int(name1_of.get(key, 0))
        p1.append(int(pid))
    g2["adm1_id"] = p1
    orphans = g2[g2["adm1_id"] == 0]
    log(f"adm2 -> adm1 parent found for {int((g2.adm1_id > 0).sum())} of {len(g2)} features; "
        f"without a province: {orphans['code'].tolist()}")

    land_idx = np.flatnonzero(land.ravel())
    cell2, unit2, cnt2 = coverage(g2.geometry, g2["id"], len(g2), slat, slon, k)
    n_cov2 = len(cell2)
    tc, tu = touched_pairs(g2.geometry, g2["id"].to_numpy(), land_idx, slat, slon)
    cell2, unit2, cnt2, added2 = add_touched(cell2, unit2, cnt2, tc, tu, len(g2))
    log(f"adm2: {n_cov2:,} coverage pairs, {len(tc):,} touched land pairs, {added2:,} touched with no sub-cell centre inside")

    # adm1 by union of adm2
    par = np.zeros(len(g2) + 1, np.int32)
    par[g2["id"].to_numpy()] = g2["adm1_id"].to_numpy()
    u1 = par[unit2]
    keep = u1 > 0
    key = cell2[keep] * (len(g1) + 1) + u1[keep]
    uk, inv = np.unique(key, return_inverse=True)
    cnt1 = np.bincount(inv, weights=cnt2[keep]).astype(np.int32)
    cell1 = (uk // (len(g1) + 1)).astype(np.int64)
    unit1 = (uk % (len(g1) + 1)).astype(np.int32)

    # check the derived adm1 against the adm1 file's own polygons
    c1f, u1f, n1f = coverage(g1.geometry, g1["id"], len(g1), slat, slon, k)
    dom1 = dominant(cell1, unit1, cnt1, ny * nx)
    dom1_file = dominant(c1f, u1f, n1f, ny * nx)
    both = (dom1 > 0) & (dom1_file > 0) & land.ravel()
    adm1_disagree = int((dom1[both] != dom1_file[both]).sum())
    only_file = int(((dom1 == 0) & (dom1_file > 0) & land.ravel()).sum())
    only_adm2 = int(((dom1 > 0) & (dom1_file == 0) & land.ravel()).sum())
    log(f"adm1 from adm2 vs adm1 file, land cells: {adm1_disagree:,} disagree of {int(both.sum()):,}; "
        f"in file only {only_file:,}; in adm2 only {only_adm2:,}")

    # ---------------------------------------------------------------- adm3
    f3 = C.BOUNDARY.format(n=3)
    g3 = gpd.read_file(f3, engine="pyogrio")
    src["adm3"] = provenance(f3)
    code3, name3, shared3 = adm3_codes(g3["KDCPUM"], g3["WADMKC"], g3["NAMOBJ"])
    g3["code"], g3["name"], g3["code_shared"] = code3, name3, shared3
    nu = len({c for c in code3 if c.startswith("U")})
    codes_sorted = sorted(set(code3))
    id3_of = {c: i + 1 for i, c in enumerate(codes_sorted)}
    g3["id"] = g3["code"].map(id3_of)
    # Parent: the Kemendagri prefix of the feature's own code, looked up among Kemendagri
    # adm2 codes. Only if that fails, the BPS code, looked up among BPS adm2 codes.
    id2_kd = {c: i for c, i in zip(g2["code"], g2["id"]) if not c.startswith("U")}
    bps_counts = g2["bps"].value_counts()
    id2_bps = {b: i for b, i in zip(g2["bps"], g2["id"]) if b and b != "0" and bps_counts[b] == 1}
    p2, how = [], []
    for raw, alt in zip(g3["KDCPUM"], g3["a2bps"]):
        pre = prefix_code(raw, 4)
        pid = id2_kd.get(pre, 0) if pre else 0
        src_ = "code_prefix" if pid else ""
        if pid == 0:
            pid = id2_bps.get(digits(alt), 0)
            src_ = "bps" if pid else "none"
        p2.append(int(pid))
        how.append(src_)
    g3["adm2_id"] = p2
    g3["parent_from"] = how
    assert g3.groupby("id")["adm2_id"].nunique().max() == 1, "features of one adm3 unit have different parents"
    split = sorted({c.split("-")[0] for c in code3 if "-" in c})
    log(f"adm3: {len(g3)} features, {len(codes_sorted)} units ({nu} without a code; {len(split)} shared codes split "
        f"by name: {split}); parent from code prefix {how.count('code_prefix')}, from BPS {how.count('bps')}, "
        f"none {how.count('none')}")
    cell3, unit3, cnt3 = coverage(g3.geometry, g3["id"], len(codes_sorted), slat, slon, k)
    n_cov3 = len(cell3)
    tc, tu = touched_pairs(g3.geometry, g3["id"].to_numpy(), land_idx, slat, slon)
    cell3, unit3, cnt3, added3 = add_touched(cell3, unit3, cnt3, tc, tu, len(codes_sorted))
    log(f"adm3: {n_cov3:,} coverage pairs, {len(tc):,} touched land pairs, {added3:,} touched with no sub-cell centre inside")

    dom2 = dominant(cell2, unit2, cnt2, ny * nx)
    dom3 = dominant(cell3, unit3, cnt3, ny * nx)
    par3 = np.zeros(len(codes_sorted) + 1, np.int32)
    first3 = g3.drop_duplicates("id")
    par3[first3["id"].to_numpy()] = first3["adm2_id"].to_numpy()
    lm = land.ravel()
    have = (dom2 > 0) & (dom3 > 0) & lm
    nest_bad = int((par3[dom3[have]] != dom2[have]).sum())
    log(f"adm3 parent vs adm2 polygon, land cells with both: {nest_bad:,} disagree of {int(have.sum()):,} "
        f"({100 * nest_bad / max(int(have.sum()), 1):.2f}%); adm3 but no adm2: {int(((dom3 > 0) & (dom2 == 0) & lm).sum()):,}; "
        f"adm2 but no adm3: {int(((dom2 > 0) & (dom3 == 0) & lm).sum()):,}")

    # ---------------------------------------------------------------- Indonesia fraction
    idn = np.bincount(cell2, weights=cnt2, minlength=ny * nx) / (k * k)
    assert idn.max() <= 1.0 + 1e-9, "coverage fraction above 1"
    idn = idn.reshape(ny, nx)
    drawn = land & (idn >= K.MAP_MIN_FRACTION)
    log(f"Indonesian land cells: any coverage {int((land & (idn > 0)).sum()):,}; drawn (>= {K.MAP_MIN_FRACTION}) "
        f"{int(drawn.sum()):,}; cell equivalents {float((idn * land).sum()):,.0f}; "
        f"area {float((idn * land * cell_area).sum()):,.0f} km2")

    # ---------------------------------------------------------------- step_1984 flag
    R = K.FLAG_STEP_1984
    stepc = np.zeros((ny, nx), bool)
    step_diff = {}
    step_counts = {}
    for index, scale in R["layers"]:
        fpath = (C.SPI_FILE if index == "spi" else C.EDDI_FILE).format(n=scale)
        fvar = C.SPI_VAR.format(n=scale) if index == "spi" else C.EDDI_VAR
        ds, sub = open_window(fpath, fvar)
        assert np.allclose(sub["lat"].values, slat) and np.allclose(sub["lon"].values, slon), f"{index}-{scale} grid differs"
        m_, before, after = K.step_1984_cells(sub.values * K.DRY_SIGN[index])     # dry-positive
        ds.close()
        src[f"{index}_{scale}"] = provenance(fpath)
        m_ &= land
        stepc |= m_
        step_diff[f"{index}{scale}"] = (before - after).astype(np.float32)
        step_counts[f"{index}{scale}"] = dict(window=int(m_.sum()), drawn=int((m_ & drawn).sum()))
    log(f"step_1984: {int(stepc.sum()):,} land cells in the window, {int((stepc & (idn > 0)).sum()):,} with Indonesian "
        f"coverage, {int((stepc & drawn).sum()):,} drawn; by layer {step_counts}")

    # ---------------------------------------------------------------- unit tables
    w_cell = (land * cell_area).ravel()            # km2 of valid land per cell, before the unit fraction

    def unit_table(cell, unit, cnt, n_units):
        """Statistics use ALL TOUCHED land cells at full cell area. Coverage figures are kept for reference."""
        frac = cnt / (k * k)
        lc = lm[cell]
        ca = cell_area.ravel()
        n_cells = np.bincount(unit[lc], minlength=n_units + 1)
        cells_km2 = np.bincount(unit[lc], weights=ca[cell[lc]], minlength=n_units + 1)
        flagged = np.bincount(unit[lc], weights=ca[cell[lc]] * stepc.ravel()[cell[lc]], minlength=n_units + 1)
        cov_equiv = np.bincount(unit[lc], weights=frac[lc], minlength=n_units + 1)
        cov_km2 = np.bincount(unit, weights=frac * w_cell[cell], minlength=n_units + 1)
        return n_cells, cells_km2, flagged, cov_equiv, cov_km2

    out_units = {}
    t, e, a, fl, al = unit_table(cell1, unit1, cnt1, len(g1))
    u = pd.DataFrame(dict(id=g1["id"], code=g1["code"], name=g1["a1name"], iso=g1["iso"], island_group=g1["geoareas"]))
    out_units[1] = (u, t, e, a, fl, al)
    t, e, a, fl, al = unit_table(cell2, unit2, cnt2, len(g2))
    u = pd.DataFrame(dict(id=g2["id"], code=g2["code"], name=g2["WADMKK"].fillna(g2["NAMOBJ"]), type=g2["type"],
                          assigned=g2["assigned"], adm1_id=g2["adm1_id"], remark=g2["REMARK"]))
    out_units[2] = (u, t, e, a, fl, al)
    t, e, a, fl, al = unit_table(cell3, unit3, cnt3, len(codes_sorted))
    u = first3.sort_values("id")
    u = pd.DataFrame(dict(id=u["id"].to_numpy(), code=u["code"].to_numpy(), name=u["name"].to_numpy(),
                          code_shared=u["code_shared"].to_numpy(), adm2_id=u["adm2_id"].to_numpy(),
                          parent_from=u["parent_from"].to_numpy()))
    u["adm1_id"] = par[u["adm2_id"].to_numpy()]
    out_units[3] = (u, t, e, a, fl, al)

    summary = {}
    for n, (u, nc_, ck, fl, ce_, cv) in out_units.items():
        ids = u["id"].to_numpy()
        u["n_cells"] = nc_[ids]                               # all touched land cells: what statistics use
        u["cells_km2"] = np.round(ck[ids], 2)                 # their full area; larger than the polygon
        u["coverage_equiv"] = np.round(ce_[ids], 3)           # reference: cells weighted by fraction inside
        u["coverage_km2"] = np.round(cv[ids], 2)              # reference: land area inside the polygon
        # missing, not 0.0, where the unit has no land cell
        exact_share = np.divide(fl[ids], ck[ids], out=np.full(len(ids), np.nan), where=ck[ids] > 0)
        u["step_1984_share"] = np.round(exact_share, 4)
        # the majority test is made here, on the unrounded share: a unit at 0.50001 must not round to "not over half"
        u["step_1984_majority"] = np.nan_to_num(exact_share, nan=0.0) > K.UNIT_FLAG_MAJORITY
        u["supported"] = u["n_cells"] >= K.MIN_CELL_EQUIV
        u["has_data"] = u["n_cells"] > 0
        u.to_csv(C.STEP0 / f"units_adm{n}.csv", index=False, encoding="utf-8")
        ce = u["n_cells"].to_numpy()
        summary[f"adm{n}"] = dict(
            units=int(len(u)), with_data=int((ce > 0).sum()), supported=int(u["supported"].sum()),
            n_cells_median=float(np.median(ce)), n_cells_p10=float(np.percentile(ce, 10)),
            below_5=int((ce < 5).sum()), exactly_1=int((ce == 1).sum()),
            touched_over_coverage=float(ce.sum() / max(u["coverage_equiv"].sum(), 1e-9)),
            step_1984_majority=int(u["step_1984_majority"].sum()))
        log(f"adm{n}: {len(u)} units, {summary[f'adm{n}']['with_data']} with data, "
            f"{summary[f'adm{n}']['supported']} with >= {K.MIN_CELL_EQUIV} touched cells; median "
            f"{summary[f'adm{n}']['n_cells_median']:.0f}; below 5: {summary[f'adm{n}']['below_5']}; "
            f"touched cells / coverage equivalents {summary[f'adm{n}']['touched_over_coverage']:.2f}; "
            f"majority step_1984: {summary[f'adm{n}']['step_1984_majority']}")

    for n, (cell, unit, cnt) in {1: (cell1, unit1, cnt1), 2: (cell2, unit2, cnt2), 3: (cell3, unit3, cnt3)}.items():
        np.savez_compressed(C.STEP0 / f"weights_adm{n}.npz", cell=cell.astype(np.int32), unit=unit,
                            subcells=cnt.astype(np.int16), supersample=np.int32(k), shape=np.array([ny, nx], np.int32))

    # ---------------------------------------------------------------- invariants
    checks = {}
    # adm1 here is built from adm2. The independent witness is the adm1 file's own polygons,
    # rasterised separately above: compare the two per (cell, province), in sub-cells.
    n1 = len(g1) + 1
    derived = dict(zip((cell1 * n1 + unit1).tolist(), cnt1.tolist()))
    from_file = dict(zip((c1f * n1 + u1f).tolist(), n1f.tolist()))
    diff_sub = sum(abs(derived.get(key_, 0) - from_file.get(key_, 0)) for key_ in set(derived) | set(from_file))
    checks["adm1_derived_vs_file_subcells_differing"] = int(diff_sub)
    checks["adm1_derived_vs_file_subcells_total"] = int(sum(from_file.values()))
    assert diff_sub <= 0.001 * sum(from_file.values()), "adm1 built from adm2 departs from the adm1 file by over 0.1%"
    a1 = out_units[1][0]["coverage_km2"].sum()
    a2 = out_units[2][0].loc[out_units[2][0]["adm1_id"] > 0, "coverage_km2"].sum()
    checks["adm1_km2"] = float(a1)
    checks["adm2_km2_with_province"] = float(a2)
    checks["adm3_km2"] = float(out_units[3][0]["coverage_km2"].sum())
    checks["touched_pairs_without_subcell"] = dict(adm2=added2, adm3=added3)
    checks["adm1_file_vs_derived_disagree_cells"] = adm1_disagree
    checks["adm3_parent_vs_adm2_polygon_disagree_cells"] = nest_bad
    # every adm3 unit has one name; no unit may be nameless unless it is uncoded
    u3 = out_units[3][0]
    checks["adm3_named_units_without_name"] = int((u3["name"].isna() & ~u3["code"].str.startswith("U")).sum())
    checks["adm3_units_without_parent"] = u3.loc[u3["adm2_id"] == 0, "code"].tolist()
    # EDDI's attainable bound comes from the file; the constant in conventions must agree with it
    f_e = C.EDDI_FILE.format(n=1)
    with xr.open_dataset(f_e) as de:
        bound = K.eddi_bound(de.attrs)
    src["eddi_1"] = provenance(f_e)
    checks["eddi_bound_from_file"] = bound
    assert abs(bound - K.INDEX_BOUND["eddi"]) < 1e-3, f"EDDI bound in file ({bound}) differs from conventions"
    log(f"checks: {checks}")

    # ---------------------------------------------------------------- grid.nc
    enc = dict(zlib=True, complevel=5)
    out = xr.Dataset(
        dict(
            land=(("lat", "lon"), land.astype(np.uint8), dict(long_name="TerraClimate land cell (finite SPI-1 in the last month)")),
            idn_fraction=(("lat", "lon"), idn.astype(np.float32), dict(long_name="fraction of the cell inside Indonesia (adm2 polygons)", units="1")),
            cell_area_km2=(("lat", "lon"), cell_area.astype(np.float32), dict(long_name="cell area on a sphere", units="km2")),
            adm1_id=(("lat", "lon"), dom1.reshape(ny, nx), dict(long_name="dominant adm1 unit id, 0 = none")),
            adm2_id=(("lat", "lon"), dom2.reshape(ny, nx), dict(long_name="dominant adm2 unit id, 0 = none")),
            adm3_id=(("lat", "lon"), dom3.reshape(ny, nx), dict(long_name="dominant adm3 unit id, 0 = none")),
            flag_step_1984=(("lat", "lon"), stepc.astype(np.uint8), dict(long_name="step_1984 quality flag; end month depends on the index scale")),
            step_spi12=(("lat", "lon"), step_diff["spi12"], dict(long_name="SPI-12 dry-positive mean 1975-1983 minus 1985-1993")),
            step_eddi12=(("lat", "lon"), step_diff["eddi12"], dict(long_name="EDDI-12 dry-positive mean 1975-1983 minus 1985-1993")),
        ),
        coords=dict(lat=("lat", slat, dict(units="degrees_north")), lon=("lon", slon, dict(units="degrees_east"))),
        attrs=dict(title="drywet-explorer step 0 grid", Conventions="CF-1.8",
                   source="TerraClimate v1.1 grid; Indonesian admin boundaries (BIG, via idn_bnd_adm*.shp)",
                   supersample=k, created=datetime.now().isoformat(timespec="seconds")),
    )
    out.to_netcdf(C.STEP0 / "grid.nc", encoding={v: enc for v in out.data_vars})

    manifest = dict(
        step="step0_grid", created=datetime.now().isoformat(timespec="seconds"), script="pipeline/step0_grid.py",
        period=K.PERIOD, months=K.N_MONTHS, baseline=K.BASELINE, window=K.WINDOW,
        grid=dict(shape=[ny, nx], lat_first=float(slat[0]), lon_first=float(slon[0]), dlat=-float(dy), dlon=float(dx),
                  lat_order="north_to_south", cell_area_km2=[float(area_row.min()), float(area_row.max())]),
        zonal_rule=dict(
            rule="all_touched", decided="owner, 2026-11-20",
            meaning="a unit's statistics use every land cell its polygon intersects, each at full cell area",
            test="exact: cell box intersects the full-resolution polygon (shapely STRtree, predicate intersects)",
            consequence="a cell on a boundary counts fully in every unit it touches; unit areas overlap",
            weights_file="rows are (cell, unit) pairs; every row on a land cell is a member. `subcells` is the "
                         "coverage estimate, kept for reference and for the click lookup, and is 0 for a pair "
                         "that is touched without containing a sub-cell centre"),
        coverage=dict(method="sub-cell centres", supersample=k, fraction_step=1 / (k * k),
                      use="reference only: idn_fraction, dominant unit per cell, coverage_equiv, coverage_km2",
                      hierarchy="adm1 = union of adm2 by a1bps; adm3 parent from its own code prefix, else BPS code",
                      overlap_rule="where polygons overlap, a sub-cell goes to the later feature (not tested layer-wide)"),
        rules=dict(land="finite SPI-1 in the last month", earth_radius_km=K.EARTH_RADIUS_KM,
                   map_min_fraction=K.MAP_MIN_FRACTION,
                   adm1_code="a1bps", adm2_code="KDPKAB as 4 digits; otherwise U01.. in file order",
                   adm3_code="KDCPUM as 6 digits; otherwise U001.. in file order; a code shared by clearly "
                             "different names is split as code-1, code-2",
                   step_1984_count_note="flag_step_1984 covers every land cell in the window meeting the rule, "
                                         "inside Indonesia or not"),
        versions=versions(),
        counts=dict(land_cells_window=int(land.sum()), idn_cells_any=int((land & (idn > 0)).sum()),
                    idn_cells_drawn=int(drawn.sum()), idn_cell_equiv=float((idn * land).sum()),
                    idn_land_km2=float((idn * land * cell_area).sum()),
                    adm2_unassigned_features=int(n_unassigned), adm2_without_province=orphans["code"].tolist(),
                    step_1984_cells=int(stepc.sum()), step_1984_cells_drawn=int((stepc & drawn).sum()),
                    step_1984_by_layer=step_counts),
        units=summary, checks=checks,
        flags=dict(early_record=K.FLAG_EARLY_RECORD, step_1984=K.FLAG_STEP_1984,
                   step_1984_last_position={str(sc): K.step_1984_last_position(sc) for sc in K.SCALES},
                   unit_flag_majority=dict(value=K.UNIT_FLAG_MAJORITY, status="proposed")),
        min_cell_equiv=dict(value=K.MIN_CELL_EQUIV, status="proposed"),
        sources=src,
    )
    mine = ["grid.nc"] + [f"units_adm{n}.csv" for n in (1, 2, 3)] + [f"weights_adm{n}.npz" for n in (1, 2, 3)]
    manifest["outputs"] = {n: (C.STEP0 / n).stat().st_size for n in mine}
    with open(C.STEP0 / "manifest.json", "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, default=str)
    sizes = {p.name: p.stat().st_size for p in sorted(C.STEP0.iterdir())}
    log(f"written to {C.STEP0}: " + ", ".join(f"{n} {s / 1e6:.2f} MB" for n, s in sizes.items()))


if __name__ == "__main__":
    main()
