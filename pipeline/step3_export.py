"""Step 3: export what the browser loads, for the province (adm1) page.

Reads data/step0..2 only and writes site/data/:

  meta.json                 grid, period, flags, layers (classes with side, rank, occurs), encodings
  units_adm1.json           one record per province
  admin1.geojson            display outlines (copied from step 0)
  cells.u32.gz              flat grid index of each drawn cell
  cell_adm1.u8.gz           province id of each drawn cell (dominant; for click lookup), 0 = none
  cell_step.u8.gz           1 where the drawn cell carries the step_1984 flag
  adm1/{layer}_share.u16.gz share [month, province, class], as in step 1
  adm1/{layer}_mean.i16.gz  mean [month, province]
  adm1/{layer}_events.json  events, columnar
  adm1/{layer}_summary.json per province and side
  maps/{layer}/{decade}.u8.gz  class per drawn cell, [months in the decade, drawn cell]
  units_adm2.json, admin2.geojson, cell_adm2.u16.gz   the same three things for kabupaten and kota
  adm2/{layer}/{province id}_share.u16.gz, _mean.i16.gz, _events.json, _summary.json
                            kabupaten tables, one bundle per province: [month, child, class], where
                            child is the position in meta.children[province id]. The browser loads
                            only the bundle of the province the reader has opened.
  units_adm3.json, cell_adm3.u16.gz, admin3/{province id}.geojson   kecamatan units, lookup and outlines
  adm3/{layer}/{province id}_side.u8.gz    [month, child, 2]: share of area in dry classes, in wet classes
  adm3/{layer}/{province id}_mean.i16.gz   [month, child]
  adm3/{layer}/{province id}_events.bin.gz events, packed (layout in EVENTS_BIN below and in meta.json)
  adm3/{layer}/{province id}_summary.json  columnar, the columns the page reads
                            Kecamatan are bundled by province like kabupaten, but kept smaller: 7,298
                            units would otherwise be several hundred MB. Only the dry and wet totals
                            are shipped, not every class: a kecamatan holds about a dozen cells.
  files.js                  generated: one literal FileAttachment per file above

Why files.js: Observable Framework publishes only files named by a string
literal in a FileAttachment call ("Only the files you reference statically are
copied to the output root", docs/files.md). So the list is generated here.

Binary files are little-endian and gzip-compressed (mtime 0, so reruns are
byte-identical). Nothing is recomputed here: values are the step 1 and 2
values, re-packed.

Run from the repository root, after step 1: python -m pipeline.step3_export
"""
import gzip
import json
import shutil
import time
from datetime import datetime

import numpy as np
import pandas as pd
import xarray as xr

from . import config as C
from . import conventions as K

T0 = time.time()
LEVEL = 1
INDEX_LABEL = {"spi": "SPI", "spei": "SPEI", "eddi": "EDDI"}
INDEX_MEASURES = {"spi": "rainfall", "spei": "rainfall minus evaporative demand", "eddi": "evaporative demand"}


def log(msg):
    print(f"[{time.time() - T0:5.0f}s] {msg}", flush=True)


def gz_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as fh, gzip.GzipFile(fileobj=fh, mode="wb", compresslevel=9, mtime=0) as gz:
        gz.write(data)
    return path.stat().st_size


def js_key(s):
    return json.dumps(str(s))


ADM2_EVENT_COLUMNS = ("unit", "side", "start", "end", "duration", "magnitude", "peak", "n_onset", "max_share", "open", "flagged")


def events_json(ev, mask=None, columns=None):
    """Columnar events as plain lists. Floats rounded; booleans as 0/1."""
    cols = {}
    for k in (columns or ev.files):
        a = ev[k] if mask is None else ev[k][mask]
        if a.dtype == bool:
            cols[k] = a.astype(int).tolist()
        elif a.dtype.kind == "f":
            dec = 4 if k == "max_share" else 3
            cols[k] = [None if not np.isfinite(v) else round(float(v), dec) for v in a]
        else:
            cols[k] = a.astype(int).tolist()
    return json.dumps(cols, separators=(",", ":"))


EVENTS_BIN = dict(
    layout="uint32 n, then per-event columns in this order, each of length n",
    columns=[["unit", "uint16", 1], ["start", "uint16", 1], ["end", "uint16", 1], ["magnitude", "uint16", 100],
             ["peak", "uint16", 1000], ["max_share", "uint8", 200], ["flags", "uint8", 1]],
    flags="bit 0: side (0 dry, 1 wet); bit 1: open; bit 2: flagged", max_share_missing=255, endian="little",
    note="magnitude is capped at 655.35; duration is end - start + 1")
ADM3_SUMMARY_COLUMNS = ("id", "side", "n_events", "n_events_unflagged", "longest_months", "longest_start", "longest_is_open",
                        "longest_unflagged_months", "longest_unflagged_start", "longest_unflagged_is_open",
                        "share_of_months_in_events")


def events_bin(ev, mask):
    """Events packed as in EVENTS_BIN."""
    n = int(mask.sum())
    mag = np.clip(np.round(ev["magnitude"][mask].astype(np.float64) * 100), 0, 65535).astype("<u2")
    peak = np.clip(np.round(ev["peak"][mask].astype(np.float64) * 1000), 0, 65535).astype("<u2")
    ms = ev["max_share"][mask].astype(np.float64)
    share = np.where(np.isfinite(ms), np.clip(np.round(ms * 200), 0, 200), 255).astype(np.uint8)
    flags = (ev["side"][mask].astype(np.uint8) | (ev["open"][mask].astype(np.uint8) << 1)
             | (ev["flagged"][mask].astype(np.uint8) << 2))
    return b"".join([np.uint32(n).astype("<u4").tobytes(), ev["unit"][mask].astype("<u2").tobytes(),
                     ev["start"][mask].astype("<u2").tobytes(), ev["end"][mask].astype("<u2").tobytes(),
                     mag.tobytes(), peak.tobytes(), share.tobytes(), flags.tobytes()])


def summary_columns_json(sm, columns):
    out = {}
    for c in columns:
        out[c] = [v.item() if hasattr(v, "item") else v for v in sm[c].tolist()]
    return json.dumps(out, separators=(",", ":"))


def read_summary(path):
    sm = pd.read_csv(path, dtype={"code": str, "longest_start": str, "longest_unflagged_start": str,
                                  "current_start": str, "last_closed_end": str})
    return sm.astype(object).where(sm.notna(), None)


def summary_json(sm):
    return json.dumps(sm.to_dict("records"), separators=(",", ":"), default=lambda o: o.item())


def unit_record(r, extra):
    rec = dict(id=int(r["id"]), code=r["code"], name=None if pd.isna(r["name"]) else r["name"],
               n_cells=int(r["n_cells"]), cells_km2=float(r["cells_km2"]), coverage_km2=float(r["coverage_km2"]),
               step_1984_share=None if pd.isna(r["step_1984_share"]) else float(r["step_1984_share"]),
               step_1984_majority=bool(r["step_1984_majority"]), supported=bool(r["supported"]))
    rec.update(extra)
    return rec


def main():
    out = C.SITE_DATA
    out.mkdir(parents=True, exist_ok=True)
    m0 = json.load(open(C.STEP0 / "manifest.json", encoding="utf-8"))
    m1 = json.load(open(C.STEP1 / "manifest.json", encoding="utf-8"))
    m2 = json.load(open(C.STEP2 / "manifest.json", encoding="utf-8"))
    sizes = {}

    # ---------------------------------------------------------------- grid and cell lookups
    grid = xr.open_dataset(C.STEP0 / "grid.nc")
    lat, lon = grid["lat"].values, grid["lon"].values
    ny, nx = len(lat), len(lon)
    drawn = np.fromfile(C.STEP1 / "maps" / "cells.u32", dtype="<u4")
    adm = grid[f"adm{LEVEL}_id"].values.ravel()[drawn]
    stepc = grid["flag_step_1984"].values.ravel()[drawn]
    grid.close()
    units = pd.read_csv(C.STEP0 / f"units_adm{LEVEL}.csv", dtype={"code": str})
    assert adm.max() <= 255 and len(units) <= 255
    sizes["cells.u32.gz"] = gz_write(out / "cells.u32.gz", drawn.astype("<u4").tobytes())
    sizes["cell_adm1.u8.gz"] = gz_write(out / "cell_adm1.u8.gz", adm.astype(np.uint8).tobytes())
    sizes["cell_step.u8.gz"] = gz_write(out / "cell_step.u8.gz", stepc.astype(np.uint8).tobytes())
    shutil.copyfile(C.STEP0 / "admin1.geojson", out / "admin1.geojson")
    sizes["admin1.geojson"] = (out / "admin1.geojson").stat().st_size

    recs = []
    for _, r in units.iterrows():
        recs.append(dict(id=int(r["id"]), code=r["code"], name=r["name"], iso=r["iso"], island_group=r["island_group"],
                         n_cells=int(r["n_cells"]), cells_km2=float(r["cells_km2"]),
                         coverage_km2=float(r["coverage_km2"]),
                         step_1984_share=None if pd.isna(r["step_1984_share"]) else float(r["step_1984_share"]),
                         step_1984_majority=bool(r["step_1984_majority"]), supported=bool(r["supported"])))
    (out / "units_adm1.json").write_text(json.dumps(recs, ensure_ascii=False), encoding="utf-8")
    sizes["units_adm1.json"] = (out / "units_adm1.json").stat().st_size

    # ---------------------------------------------------------------- kabupaten and kota (adm2)
    g2 = xr.open_dataset(C.STEP0 / "grid.nc")
    adm2 = g2["adm2_id"].values.ravel()[drawn]
    g2.close()
    units2 = pd.read_csv(C.STEP0 / "units_adm2.csv", dtype={"code": str})
    assert adm2.max() <= 65535
    sizes["cell_adm2.u16.gz"] = gz_write(out / "cell_adm2.u16.gz", adm2.astype("<u2").tobytes())
    shutil.copyfile(C.STEP0 / "admin2.geojson", out / "admin2.geojson")
    sizes["admin2.geojson"] = (out / "admin2.geojson").stat().st_size
    recs2 = [unit_record(r, dict(type=None if pd.isna(r["type"]) else r["type"], assigned=bool(r["assigned"]),
                                 adm1_id=int(r["adm1_id"]))) for _, r in units2.iterrows()]
    (out / "units_adm2.json").write_text(json.dumps(recs2, ensure_ascii=False), encoding="utf-8")
    sizes["units_adm2.json"] = (out / "units_adm2.json").stat().st_size
    # children of each province, in id order: the child axis of every adm2 bundle
    children = {int(pid): grp["id"].astype(int).tolist() for pid, grp in units2[units2["adm1_id"] > 0].groupby("adm1_id")}
    orphans2 = units2.loc[units2["adm1_id"] == 0, "code"].tolist()
    enc2 = m1["share_encoding"]["per_level"]["adm2"]
    files2 = {}

    # ---------------------------------------------------------------- kecamatan (adm3)
    g3 = xr.open_dataset(C.STEP0 / "grid.nc")
    adm3 = g3["adm3_id"].values.ravel()[drawn]
    g3.close()
    units3 = pd.read_csv(C.STEP0 / "units_adm3.csv", dtype={"code": str})
    assert adm3.max() <= 65535 and len(units3) <= 65535
    sizes["cell_adm3.u16.gz"] = gz_write(out / "cell_adm3.u16.gz", adm3.astype("<u2").tobytes())
    recs3 = []
    for _, r in units3.iterrows():
        coded = not str(r["code"]).startswith("U")
        recs3.append(dict(id=int(r["id"]), name=None if pd.isna(r["name"]) else r["name"], adm2_id=int(r["adm2_id"]),
                          adm1_id=int(r["adm1_id"]), n_cells=int(r["n_cells"]),
                          step_1984_share=None if pd.isna(r["step_1984_share"]) else float(r["step_1984_share"]),
                          step_1984_majority=bool(r["step_1984_majority"]),
                          assigned=bool(coded and r["adm2_id"] > 0 and not pd.isna(r["name"]))))
    (out / "units_adm3.json").write_text(json.dumps(recs3, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    sizes["units_adm3.json"] = (out / "units_adm3.json").stat().st_size
    # children of each province at kecamatan level, in id order: the child axis of every adm3 bundle
    children3 = {int(pid): grp["id"].astype(int).tolist() for pid, grp in units3[units3["adm1_id"] > 0].groupby("adm1_id")}
    enc3 = m1["share_encoding"]["per_level"]["adm3"]
    files3 = {}
    # outlines, one file per province, so the browser loads only the open province's kecamatan
    import geopandas as gpd
    o3 = gpd.read_file(C.STEP0 / "admin3.geojson")
    o3["adm1_id"] = o3["id"].map(dict(zip(units3["id"], units3["adm1_id"])))
    (out / "admin3").mkdir(exist_ok=True)
    for pid in children3:
        part = o3.loc[o3["adm1_id"] == pid, ["id", "geometry"]]
        f = out / "admin3" / f"{pid}.geojson"
        part.to_file(f, driver="GeoJSON", COORDINATE_PRECISION=4)
        sizes[f"admin3/{pid}.geojson"] = f.stat().st_size

    # ---------------------------------------------------------------- layers
    enc = m1["share_encoding"]["per_level"][f"adm{LEVEL}"]
    layers_meta, files = {}, {}
    years = np.arange(int(K.PERIOD[0][:4]), int(K.PERIOD[1][:4]) + 1)
    decades = sorted({int(y // 10 * 10) for y in years})
    n_drawn = len(drawn)
    for tag in sorted(m1["layers"]):
        L = m1["layers"][tag]
        z = np.load(C.STEP1 / "shares" / f"{tag}_adm{LEVEL}.npz")
        share, mean = z["share"], z["mean"]
        assert share.shape[:2] == (K.N_MONTHS, len(units)) and share.dtype == np.dtype(enc["share_dtype"])
        sizes[f"adm1/{tag}_share.u16.gz"] = gz_write(out / "adm1" / f"{tag}_share.u16.gz", share.astype("<u2").tobytes())
        sizes[f"adm1/{tag}_mean.i16.gz"] = gz_write(out / "adm1" / f"{tag}_mean.i16.gz", mean.astype("<i2").tobytes())

        ev = np.load(C.STEP2 / "events" / f"{tag}_adm{LEVEL}.npz")
        p = out / "adm1" / f"{tag}_events.json"
        p.write_text(events_json(ev), encoding="utf-8")
        sizes[f"adm1/{tag}_events.json"] = p.stat().st_size
        p = out / "adm1" / f"{tag}_summary.json"
        p.write_text(summary_json(read_summary(C.STEP2 / "summary" / f"{tag}_adm{LEVEL}.csv")), encoding="utf-8")
        sizes[f"adm1/{tag}_summary.json"] = p.stat().st_size

        # kabupaten bundles, one per province
        z2 = np.load(C.STEP1 / "shares" / f"{tag}_adm2.npz")
        share2, mean2 = z2["share"], z2["mean"]
        assert share2.shape[:2] == (K.N_MONTHS, len(units2)) and share2.dtype == np.dtype(enc2["share_dtype"])
        ev2 = np.load(C.STEP2 / "events" / f"{tag}_adm2.npz")
        sm2 = read_summary(C.STEP2 / "summary" / f"{tag}_adm2.csv")
        files2[tag] = {}
        for pid, ids in children.items():
            pos = np.asarray(ids) - 1
            base = f"adm2/{tag}/{pid}"
            (out / "adm2" / tag).mkdir(parents=True, exist_ok=True)
            sizes[f"{base}_share.u16.gz"] = gz_write(out / f"{base}_share.u16.gz", np.ascontiguousarray(share2[:, pos, :]).astype("<u2").tobytes())
            sizes[f"{base}_mean.i16.gz"] = gz_write(out / f"{base}_mean.i16.gz", np.ascontiguousarray(mean2[:, pos]).astype("<i2").tobytes())
            pe = out / f"{base}_events.json"
            pe.write_text(events_json(ev2, np.isin(ev2["unit"], ids), ADM2_EVENT_COLUMNS), encoding="utf-8")
            sizes[f"{base}_events.json"] = pe.stat().st_size
            ps = out / f"{base}_summary.json"
            ps.write_text(summary_json(sm2[sm2["id"].isin(ids)]), encoding="utf-8")
            sizes[f"{base}_summary.json"] = ps.stat().st_size
            files2[tag][pid] = base

        # kecamatan bundles, one per province: side totals, mean, packed events, compact summary
        z3 = np.load(C.STEP1 / "shares" / f"{tag}_adm3.npz")
        side3, mean3, share3 = z3["side"], z3["mean"], z3["share"]
        assert side3.shape == (K.N_MONTHS, len(units3), 2) and side3.dtype == np.dtype(enc3["share_dtype"])
        ev3 = np.load(C.STEP2 / "events" / f"{tag}_adm3.npz")
        sm3 = read_summary(C.STEP2 / "summary" / f"{tag}_adm3.csv")
        prov_of_unit = np.zeros(len(units3) + 1, np.int32)
        prov_of_unit[units3["id"].to_numpy()] = units3["adm1_id"].to_numpy()
        ev_prov = prov_of_unit[ev3["unit"]]
        sm_prov = prov_of_unit[sm3["id"].to_numpy(dtype=int)]
        files3[tag] = {}
        (out / "adm3" / tag).mkdir(parents=True, exist_ok=True)
        for pid, ids in children3.items():
            pos = np.asarray(ids) - 1
            base = f"adm3/{tag}/{pid}"
            sizes[f"{base}_side.u8.gz"] = gz_write(out / f"{base}_side.u8.gz", np.ascontiguousarray(side3[:, pos, :]).astype(np.uint8).tobytes())
            # every class too (owner, 2026-11-21: the share chart shows the full class breakdown at every level)
            sizes[f"{base}_share.u8.gz"] = gz_write(out / f"{base}_share.u8.gz", np.ascontiguousarray(share3[:, pos, :]).astype(np.uint8).tobytes())
            sizes[f"{base}_mean.i16.gz"] = gz_write(out / f"{base}_mean.i16.gz", np.ascontiguousarray(mean3[:, pos]).astype("<i2").tobytes())
            sizes[f"{base}_events.bin.gz"] = gz_write(out / f"{base}_events.bin.gz", events_bin(ev3, ev_prov == pid))
            ps = out / f"{base}_summary.json"
            ps.write_text(summary_columns_json(sm3[sm_prov == pid], ADM3_SUMMARY_COLUMNS), encoding="utf-8")
            sizes[f"{base}_summary.json"] = ps.stat().st_size
            files3[tag][pid] = base

        # maps: yearly files from step 1, re-packed by decade
        mfiles = {}
        for d in decades:
            blocks, first = [], None
            for y in range(d, d + 10):
                f = C.STEP1 / "maps" / tag / f"{y}.u8.gz"
                if f.exists():
                    blocks.append(gzip.open(f).read())
                    first = y if first is None else first
            raw = b"".join(blocks)
            assert len(raw) % (12 * n_drawn) == 0
            name = f"maps/{tag}/{d}.u8.gz"
            sizes[name] = gz_write(out / "maps" / tag / f"{d}.u8.gz", raw)
            mfiles[d] = dict(file=name, first_month=(first - years[0]) * 12, months=len(raw) // n_drawn)

        normal = [c["code"] for c in L["classes"] if c["side"] == "normal"]
        assert len(normal) == 1
        classes = [dict(c, rank=abs(c["code"] - normal[0])) for c in L["classes"]]
        layers_meta[tag] = dict(
            tag=tag, index=L["index"], scale=L["scale"], label=f"{INDEX_LABEL[L['index']]}-{L['scale']}",
            measures=INDEX_MEASURES[L["index"]], dry_sign=K.DRY_SIGN[L["index"]],
            baseline=str(L["baseline"]).split(" ")[0],        # EDDI files say "1991-2020 (30 years, mode=wmo)"
            distribution=L["distribution"], attainable_bound=L.get("attainable_bound"),
            scheme=L["scheme"], scheme_status=L["scheme_status"], classes=classes,
            first_month_with_value=K.month_position(L["first_month_with_value"]),
            step_1984_last_position=K.step_1984_last_position(L["scale"]), maps=mfiles,
            source_file=L["source"]["file"], source_modified=L["source"]["modified"])
        files[tag] = mfiles
        log(f"{tag}: exported")

    meta = dict(
        created=datetime.now().isoformat(timespec="seconds"), script="pipeline/step3_export.py", levels=["adm1", "adm2", "adm3"],
        period=K.PERIOD, months=K.N_MONTHS,
        grid=dict(ny=ny, nx=nx, lat_first=float(lat[0]), lon_first=float(lon[0]), dlat=float(lat[1] - lat[0]),
                  dlon=float(lon[1] - lon[0]), n_drawn=int(n_drawn)),
        children=children, adm2_without_province=orphans2, children3=children3,
        encoding_adm3=dict(share_scale=enc3["share_scale"], share_missing=enc3["share_missing"],
                           mean_scale=enc3["mean_scale"], mean_missing=K.MEAN_MISSING,
                           axes="side file: month, child (position in children3[province id]), side (0 dry, 1 wet); "
                                "share file: month, child, class (code - 1)",
                           events=EVENTS_BIN, summary_columns=list(ADM3_SUMMARY_COLUMNS)),
        encoding_adm2=dict(share_scale=enc2["share_scale"], share_missing=enc2["share_missing"],
                           mean_scale=enc2["mean_scale"], mean_missing=K.MEAN_MISSING,
                           axes="month, child (position in children[province id]), class (code - 1)"),
        min_cells_note=dict(value=K.MIN_CELL_EQUIV, status="proposed",
                            meaning="units touching fewer grid cells are shown with a caution, not hidden"),
        encoding=dict(share_scale=enc["share_scale"], share_missing=enc["share_missing"], mean_scale=enc["mean_scale"],
                      mean_missing=K.MEAN_MISSING, n_units=int(len(units)), endian="little"),
        zonal_rule="all touched: a province's figures use every land cell its boundary touches, at full cell area",
        event_rule=K.EVENT_RULE, onset=K.EVENT_ONSET,
        event_series=m2["series"],
        flags=dict(early_record=dict(K.FLAG_EARLY_RECORD, last_position=K.month_position(K.FLAG_EARLY_RECORD["end"])),
                   step_1984=dict(name="step_1984", reason=K.FLAG_STEP_1984["reason"], limits=K.FLAG_STEP_1984["limits"],
                                  end_scale_1=K.FLAG_STEP_1984["end_scale_1"])),
        provenance=dict(step0=m0["created"], step1=m1.get("updated"), step2=m2.get("updated")),
        layers=layers_meta)
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, default=str), encoding="utf-8")
    sizes["meta.json"] = (out / "meta.json").stat().st_size

    # ---------------------------------------------------------------- files.js: one literal per file
    lines = ['// GENERATED by pipeline/step3_export.py. Do not edit: rerun the export.',
             '// Framework publishes only files named by a string literal in a FileAttachment call.',
             'import {FileAttachment} from "observablehq:stdlib";', '',
             'export const files = {',
             '  meta: FileAttachment("meta.json"),',
             '  units: FileAttachment("units_adm1.json"),',
             '  outlines: FileAttachment("admin1.geojson"),',
             '  cells: FileAttachment("cells.u32.gz"),',
             '  cellUnit: FileAttachment("cell_adm1.u8.gz"),',
             '  cellStep: FileAttachment("cell_step.u8.gz"),',
             '  units2: FileAttachment("units_adm2.json"),',
             '  outlines2: FileAttachment("admin2.geojson"),',
             '  cellUnit2: FileAttachment("cell_adm2.u16.gz"),',
             '  units3: FileAttachment("units_adm3.json"),',
             '  cellUnit3: FileAttachment("cell_adm3.u16.gz"),',
             '  outlines3: {' + ", ".join(f'{js_key(pid)}: FileAttachment("admin3/{pid}.geojson")' for pid in children3) + '},',
             '  layers: {']
    for tag, mfiles in files.items():
        lines.append(f'    {js_key(tag)}: {{')
        for k, ext in (("share", "share.u16.gz"), ("mean", "mean.i16.gz"), ("events", "events.json"), ("summary", "summary.json")):
            lines.append(f'      {k}: FileAttachment("adm1/{tag}_{ext}"),')
        lines.append('      adm2: {')
        for pid, base in files2[tag].items():
            lines.append(f'        {js_key(pid)}: {{share: FileAttachment("{base}_share.u16.gz"), mean: FileAttachment("{base}_mean.i16.gz"), '
                         f'events: FileAttachment("{base}_events.json"), summary: FileAttachment("{base}_summary.json")}},')
        lines.append('      },')
        lines.append('      adm3: {')
        for pid, base in files3[tag].items():
            lines.append(f'        {js_key(pid)}: {{side: FileAttachment("{base}_side.u8.gz"), share: FileAttachment("{base}_share.u8.gz"), '
                         f'mean: FileAttachment("{base}_mean.i16.gz"), '
                         f'events: FileAttachment("{base}_events.bin.gz"), summary: FileAttachment("{base}_summary.json")}},')
        lines.append('      },')
        lines.append('      maps: {')
        for d, mf in mfiles.items():
            lines.append(f'        {js_key(d)}: FileAttachment("{mf["file"]}"),')
        lines += ['      }', '    },']
    lines += ['  }', '};', '']
    (out / "files.js").write_text("\n".join(lines), encoding="utf-8")

    total = sum(sizes.values())
    big = sorted(sizes.items(), key=lambda kv: -kv[1])[:5]
    (out / "export_report.json").write_text(json.dumps(dict(created=meta["created"], total_bytes=total, files=sizes), indent=1), encoding="utf-8")
    log(f"done: {len(sizes)} files, {total / 1e6:.1f} MB in {out}; largest " + ", ".join(f"{k} {v / 1e6:.2f} MB" for k, v in big))


if __name__ == "__main__":
    main()
