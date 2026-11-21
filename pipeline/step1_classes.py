"""Step 1: this month's STATE, and (in the same pass) step 2's EVENTS.

For each index (spi, spei, eddi) and scale (1, 3, 6, 12), reads the source cube
once and writes to data/step1/:

  shares/{index}{scale:02d}_adm{n}.npz
      share   [month, unit, class]  round(share * scale); dtype, scale and missing code per
                                    admin level in conventions.SHARE_ENCODING (also in the manifest)
      mean    int16 [month, unit]   round(area-weighted mean index * mean_scale); -32768 = no value
      valid   uint16 [month, unit]  round(10000 * area with a value / unit cell area)
      side    [month, unit, 2]      share of valued area in dry classes (0) and wet classes (1), same
                                    encoding as `share`, rounded once from the unrounded totals
      Unit axis: id 1..N is position 0..N-1 (ids from data/step0/units_adm{n}.csv).
      Class axis: position 0..C-1 is class code 1..C from conventions.class_scheme.
  maps/{index}{scale:02d}/{year}.u8.gz
      uint8 [12 months, drawn cell]  class code, 0 = no data. gzip, mtime 0.
  maps/cells.u32   flat grid index (row * nx + col) of each drawn cell, little-endian uint32
  manifest.json

and, through pipeline.step2_events, data/step2/ (events and summaries). Events
are found here because they need the unit mean before it is rounded for storage.

Method
  A cell's class comes from conventions (SPI and SPEI: classify_spi; EDDI: the
    file's own eddi_cat).
  Cells of a unit: ALL TOUCHED. Every land cell the unit's polygon intersects,
    from step 0, each at its full cell area w (owner's rule, 2026-11-20). A cell
    on a boundary therefore counts fully in each unit it touches.
  Share of class c in a unit, for a month = sum of w over its cells in class c
    / sum of w over its cells with a value. Cells without a value that month are
    left out of both sums, so shares add to 1 whenever the unit has any value.
  A unit with no valued cell in a month gets the level's missing code in `share`,
    -32768 in `mean` and 0 in `valid`: warm-up months and units with no land are
    missing, never zero or "normal".
  Each admin level is computed from its own weights. Nothing is rolled up.
  Drawn cells: the same cells the statistics use, every land cell an Indonesian unit touches.
  All sums are float64; values are rounded once, for storage.

Run from the repository root: python -m pipeline.step1_classes [index[,index] [scale[,scale]]]
"""
import gzip
import json
import sys
import time
from datetime import datetime

import numpy as np
import pandas as pd
import xarray as xr
from scipy import sparse

from . import config as C
from . import conventions as K
from . import step2_events
from .step0_grid import open_window, provenance, versions

T0 = time.time()


def log(msg):
    print(f"[{time.time() - T0:5.0f}s] {msg}", flush=True)


def source_of(index, scale):
    if index == "spi":
        return C.SPI_FILE.format(n=scale), C.SPI_VAR.format(n=scale), None
    if index == "spei":
        return C.SPEI_FILE.format(n=scale), C.SPEI_VAR.format(n=scale), None
    return C.EDDI_FILE.format(n=scale), C.EDDI_VAR, C.EDDI_CAT_VAR


def weights_matrix(cell, unit, pos_of_cell, cell_area, n_units):
    """Sparse units x cells matrix of weights (km2) under the ALL TOUCHED rule.

    cell, unit: the rows of a step 0 weights file. pos_of_cell: position of each
    grid cell among the cells in use, -1 for a cell that is not land. Every row
    on a land cell gets that cell's FULL area; the file's `subcells` is not read.
    n_units comes from the unit table, so a unit with no row keeps its place.
    """
    cell = np.asarray(cell, dtype=np.int64)
    unit = np.asarray(unit, dtype=np.int64)
    assert unit.min() >= 1 and unit.max() <= n_units, "weights file has a unit id outside the unit table"
    pos = pos_of_cell[cell]
    keep = pos >= 0
    n_sel = int(pos_of_cell.max()) + 1
    return sparse.csr_matrix((np.asarray(cell_area, dtype=np.float64)[cell[keep]], (unit[keep] - 1, pos[keep])),
                             shape=(n_units, n_sel))


def unit_stats(cls, value, W, codes):
    """Area per class, mean and valid area for every unit and month. All float64.

    cls: uint8 [month, cell] class code, 0 = no data. value: float [month, cell], NaN = no value.
    W: units x cells weights. codes: class codes in class-axis order.
    Returns area [month, unit, class], valid [month, unit] (area with a class),
    mean [month, unit] (NaN where no cell has a value).
    """
    nt = cls.shape[0]
    nu = W.shape[0]
    area = np.zeros((nt, nu, len(codes)), np.float64)
    for ci, code in enumerate(codes):
        area[:, :, ci] = (W @ (cls == code).T.astype(np.float64)).T
    valid = area.sum(axis=2)
    has = np.isfinite(value)
    wsum = (W @ np.where(has, value, 0.0).T.astype(np.float64)).T
    wval = (W @ has.T.astype(np.float64)).T
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = np.where(wval > 0, wsum / wval, np.nan)
    return area, valid, mean


def encode(area, valid, mean, total, level):
    """Round once, for storage, with the level's encoding. Returns share, mean, valid arrays."""
    E = K.SHARE_ENCODING[level]
    sdt = np.dtype(E["share_dtype"])
    ok = valid > 0
    s_enc = np.full(area.shape, E["share_missing"], sdt)
    with np.errstate(invalid="ignore", divide="ignore"):
        share = area / valid[:, :, None]
    s_enc[ok] = np.round(share[ok] * E["share_scale"]).astype(sdt)
    m_enc = np.full(mean.shape, K.MEAN_MISSING, np.int16)
    mok = np.isfinite(mean)
    m_enc[mok] = np.round(mean[mok] * E["mean_scale"]).astype(np.int16)
    with np.errstate(invalid="ignore", divide="ignore"):
        vfrac = np.where(total > 0, valid / total, 0.0)
    return s_enc, m_enc, np.round(vfrac * 10000).astype(np.uint16)


def encode_side(dry, wet, level):
    """Dry and wet side shares as [month, unit, 2], with the level's share encoding. Position 0 is dry, 1 is wet."""
    E = K.SHARE_ENCODING[level]
    sdt = np.dtype(E["share_dtype"])
    out = np.full(dry.shape + (2,), E["share_missing"], sdt)
    for k, a in enumerate((dry, wet)):
        ok = np.isfinite(a)
        out[..., k][ok] = np.round(a[ok] * E["share_scale"]).astype(sdt)
    return out


def side_share(area, valid, scheme, side):
    """Unrounded share of a unit's valued area in the classes on one side. NaN where no value."""
    pos = [i for i, (_, _, s) in enumerate(scheme) if s == side]
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(valid > 0, area[:, :, pos].sum(axis=2) / valid, np.nan)


def main():
    indices = sys.argv[1].split(",") if len(sys.argv) > 1 else ["spi", "spei", "eddi"]
    scales = [int(s) for s in sys.argv[2].split(",")] if len(sys.argv) > 2 else list(K.SCALES)
    (C.STEP1 / "shares").mkdir(parents=True, exist_ok=True)
    (C.STEP1 / "maps").mkdir(parents=True, exist_ok=True)

    grid = xr.open_dataset(C.STEP0 / "grid.nc")
    glat, glon = grid["lat"].values, grid["lon"].values
    ny, nx = len(glat), len(glon)
    land = grid["land"].values.astype(bool)
    idn = grid["idn_fraction"].values
    cell_area = grid["cell_area_km2"].values.astype(np.float64).ravel()
    grid.close()
    step0_created = json.load(open(C.STEP0 / "manifest.json", encoding="utf-8"))["created"]
    units = {n: pd.read_csv(C.STEP0 / f"units_adm{n}.csv", dtype={"code": str}) for n in (1, 2, 3)}
    wfile = {n: np.load(C.STEP0 / f"weights_adm{n}.npz") for n in (1, 2, 3)}
    # every cell any statistic uses: land cells touched by any unit at any level
    used = np.zeros(ny * nx, bool)
    for n in (1, 2, 3):
        used[wfile[n]["cell"]] = True
    sel = np.flatnonzero(used & land.ravel())
    # The map draws exactly the cells the statistics use: ALL TOUCHED (owner, 2026-11-21). It used to draw
    # only cells at least half inside Indonesia, which left 7,802 coastal and border cells off the map
    # (8.1% of the cells in use) while their values were still counted in every unit's figures.
    drawn = sel.copy()
    pos_of_cell = np.full(ny * nx, -1, np.int64)
    pos_of_cell[sel] = np.arange(len(sel))
    drawn_pos = pos_of_cell[drawn]
    assert (drawn_pos >= 0).all()
    drawn.astype("<u4").tofile(C.STEP1 / "maps" / "cells.u32")
    W, total = {}, {}
    for n in (1, 2, 3):
        u = units[n]
        assert (u["id"].to_numpy() == np.arange(1, len(u) + 1)).all(), f"adm{n} unit ids are not 1..N in order"
        W[n] = weights_matrix(wfile[n]["cell"], wfile[n]["unit"], pos_of_cell, cell_area, len(u))
        total[n] = np.asarray(W[n].sum(axis=1)).ravel()                  # unit cell area on the grid
        assert np.allclose(total[n], u["cells_km2"].to_numpy(), atol=0.01), f"adm{n} cell area differs from the unit table"
    log(f"cells used {len(sel):,}, drawn {len(drawn):,}; units " + ", ".join(f"adm{n} {W[n].shape[0]}" for n in W))

    man_path = C.STEP1 / "manifest.json"
    manifest = json.load(open(man_path, encoding="utf-8")) if man_path.exists() else dict(layers={})
    ev_stats, ev_sides = {}, {}
    for index in indices:
        for scale in scales:
            path, var, catvar = source_of(index, scale)
            ds, sub = open_window(path, var)
            assert np.array_equal(sub["lat"].values, glat) and np.array_equal(sub["lon"].values, glon), "grid differs from step 0"
            times = ds["time"].values
            assert len(times) == K.N_MONTHS and str(times[0])[:7] == K.PERIOD[0] and str(times[-1])[:7] == K.PERIOD[1]
            years = times.astype("datetime64[Y]").astype(int) + 1970
            v = K.to_float(sub.values.reshape(K.N_MONTHS, ny * nx)[:, sel])     # NaN where there is no value
            bound = None
            if catvar:
                lat0 = int(np.flatnonzero(ds["lat"].values == glat[0])[0])
                lon0 = int(np.flatnonzero(ds["lon"].values == glon[0])[0])
                cat = ds[catvar].isel(lat=slice(lat0, lat0 + ny), lon=slice(lon0, lon0 + nx))
                assert np.array_equal(cat["lat"].values, glat) and np.array_equal(cat["lon"].values, glon), "eddi_cat window differs"
                cls = K.classify_eddi_cat(cat.values.reshape(K.N_MONTHS, ny * nx)[:, sel])
                scheme = K.class_scheme(index, ds[catvar].attrs)
                baseline = ds.attrs.get("baseline_period")
                bound = K.eddi_bound(ds.attrs)
            else:
                cls = K.classify_spi(v)
                scheme = K.class_scheme(index)
                baseline = f"{ds.attrs.get('calibration_start_year')}-{ds.attrs.get('calibration_end_year')}"
            distribution = ds.attrs.get("distribution", "nonparametric rank" if index == "eddi" else None)
            ds.close()
            has = np.isfinite(v)
            n_mismatch = int(((cls > 0) != has).sum())      # a class without a value, or a value without a class
            assert n_mismatch == 0, f"{index}{scale}: {n_mismatch} cell-months have a class without a value or the reverse"
            codes = [c for c, _, _ in scheme]
            tag = f"{index}{scale:02d}"
            log(f"{tag}: read {v.shape}, finite {100 * has.mean():.2f}%")

            sizes, stats = {}, {}
            for n in (1, 2, 3):
                area, valid, mean = unit_stats(cls, v, W[n], codes)
                s_enc, m_enc, v_enc = encode(area, valid, mean, total[n], n)
                # dry and wet side totals, rounded once from the unrounded sums: adding stored class
                # shares instead would add their rounding errors (up to 3 steps)
                sdry = side_share(area, valid, scheme, "dry")
                swet = side_share(area, valid, scheme, "wet")
                side_enc = encode_side(sdry, swet, n)
                out = C.STEP1 / "shares" / f"{tag}_adm{n}.npz"
                np.savez_compressed(out, share=s_enc, mean=m_enc, valid=v_enc, side=side_enc)
                sizes[out.name] = out.stat().st_size
                ok = valid > 0
                tot = (area[ok] / valid[ok][:, None]).sum(axis=1)
                stats[f"adm{n}"] = dict(unit_months_with_value=int(ok.sum()), unit_months_missing=int((~ok).sum()),
                                        max_abs_share_sum_minus_1=float(np.abs(tot - 1).max()) if tot.size else None)
                # ---- step 2, on the unrounded mean and unrounded side shares
                ev_stats[f"{tag}_adm{n}"] = step2_events.build(tag, n, index, scale, mean, sdry, swet, units[n])
                del area, valid, mean, sdry, swet
            ev_sides[tag] = {side: [lab for _, lab, s in scheme if s == side] for side in ("dry", "wet")}

            # ---- class maps for drawn cells, one file per year
            mdir = C.STEP1 / "maps" / tag
            mdir.mkdir(exist_ok=True)
            cm = cls[:, drawn_pos]
            mbytes = 0
            for y in np.unique(years):
                blk = np.ascontiguousarray(cm[years == y])
                assert blk.shape[0] == 12
                p = mdir / f"{y}.u8.gz"
                with open(p, "wb") as fh, gzip.GzipFile(fileobj=fh, mode="wb", compresslevel=9, mtime=0) as gz:
                    gz.write(blk.tobytes())
                mbytes += p.stat().st_size
            counts = np.bincount(cm.ravel(), minlength=len(codes) + 1)
            first_valid = int(np.flatnonzero(has.any(axis=1))[0])
            manifest["layers"][tag] = dict(
                index=index, scale=scale, source=provenance(path), variable=var, class_variable=catvar,
                baseline=baseline, distribution=distribution, attainable_bound=bound,
                scheme=K.INDEX_SCHEME[index], scheme_status=K.SCHEME_STATUS[index],
                # `occurs` is measured over every drawn cell and month: a class that never occurs must not be
                # drawn in a legend as if it could
                classes=[dict(code=c, label=lab, side=s, drawn_cell_months=int(counts[c]), occurs=bool(counts[c] > 0))
                         for c, lab, s in scheme],
                no_data_drawn_cell_months=int(counts[0]),
                first_month_with_value=str(times[first_valid])[:7], finite_share_of_cell_months=float(has.mean()),
                class_value_mismatch=n_mismatch, share_files=sizes, map_bytes=mbytes, checks=stats,
                step0_manifest_created=step0_created, created=datetime.now().isoformat(timespec="seconds"))
            a = ev_stats[f"{tag}_adm2"]
            never = [c["label"] for c in manifest["layers"][tag]["classes"] if not c["occurs"]]
            log(f"{tag}: shares {sum(sizes.values()) / 1e6:.1f} MB, maps {mbytes / 1e6:.1f} MB; classes that never occur {never}; "
                f"adm2 events {a['events']:,} (dry {a['dry']:,}, wet {a['wet']:,}), longest {a['longest']} "
                f"(unflagged {a['longest_unflagged']}), max_share max {a['max_share_max']:.6f}")
            manifest.update(
                step="step1_classes", script="pipeline/step1_classes.py", period=K.PERIOD, months=K.N_MONTHS,
                first_month=K.PERIOD[0], cells_used=int(len(sel)), cells_drawn=int(len(drawn)), grid_shape=[ny, nx],
                share_encoding=dict(per_level={f"adm{n}": e for n, e in K.SHARE_ENCODING.items()},
                                    mean_dtype="int16", mean_missing=K.MEAN_MISSING,
                                    valid="uint16, round(10000 * area with a value / unit cell area)",
                                    axes="month, unit (id-1), class (code-1)",
                                    note="values are rounded once from float64; class shares rounded one by one "
                                         "need not sum to exactly the scale"),
                map_encoding=dict(dtype="uint8", shape="12 months x drawn cells", no_data=0, cells="maps/cells.u32",
                                  compression="gzip level 9, mtime 0"),
                zonal_rule="all_touched: every land cell a unit's polygon intersects, at full cell_area_km2 "
                           "(rows of data/step0/weights_adm{n}.npz); owner's rule, 2026-11-20",
                flags="none applied in step 1: see data/step0/manifest.json and data/step2/manifest.json",
                note="top-level fields describe the latest run; each layer carries its own created and step 0 stamp",
                versions=versions(), updated=datetime.now().isoformat(timespec="seconds"))
            with open(man_path, "w", encoding="utf-8") as fh:
                json.dump(manifest, fh, indent=2, default=str)
            step2_events.write_manifest(ev_stats, ev_sides)
    tot_sh = sum(p.stat().st_size for p in (C.STEP1 / "shares").glob("*.npz"))
    tot_mp = sum(p.stat().st_size for p in (C.STEP1 / "maps").rglob("*.gz"))
    tot_ev = sum(p.stat().st_size for p in C.STEP2.rglob("*") if p.is_file())
    log(f"done. data/step1: shares {tot_sh / 1e6:.1f} MB, maps {tot_mp / 1e6:.1f} MB; data/step2: {tot_ev / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
