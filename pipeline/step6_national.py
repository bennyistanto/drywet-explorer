"""Step 6: Indonesia as one unit, for the national summary on the dashboard.

Steps 1 and 2 work on provinces, kabupaten and kecamatan. This adds the country, with the same functions and
the same rules, so that the national view has the tiles, charts, events and ENSO comparison a province has.

The unit is EVERY cell the map draws: every land cell touched by any Indonesian unit, each at its full area
(the all-touched rule, as at every other level). It is not the sum of the provinces: provinces share border
cells, and adding them would count those cells more than once.

For each index and scale:
  share of the national cell area in each class, and the area-weighted mean index, every month
      (pipeline.step1_classes.unit_stats, encoded as the province tables are)
  events on the unrounded national mean, and their summary
      (pipeline.step2_events.event_table and summarise)

Writes, straight into the site:
  site/data/national/{tag}_share.u16.gz   [month, 1, class]  as adm1
  site/data/national/{tag}_mean.i16.gz    [month, 1]
  site/data/national/{tag}_events.json    columns, as adm1
  site/data/national/{tag}_summary.json   records, as adm1
  site/data/national.json                 the unit's record and per-layer notes
  site/data/national_files.js             generated: one literal FileAttachment per file
  data/step6/layers/{tag}.json            per-layer record, so that indices can be run side by side

Run from the repository root:
  python -m pipeline.step6_national            all indices and scales
  python -m pipeline.step6_national spi 3,12   some of them
"""
import gzip
import json
import sys
import time
from datetime import datetime

import numpy as np
import xarray as xr
from scipy import sparse

from . import config as C
from . import conventions as K
from . import step2_events
from .step0_grid import open_window, provenance
from .step1_classes import encode, side_share, source_of, unit_stats
from .step3_export import events_json, gz_write, js_key, summary_json

T0 = time.time()
STEP6 = C.OUT / "step6"
NAME = "Indonesia"


def log(msg):
    print(f"[{time.time() - T0:5.0f}s] {msg}", flush=True)


def main():
    indices = sys.argv[1].split(",") if len(sys.argv) > 1 else ["spi", "spei", "eddi"]
    scales = [int(s) for s in sys.argv[2].split(",")] if len(sys.argv) > 2 else list(K.SCALES)
    out = C.SITE_DATA / "national"
    grid = xr.open_dataset(C.STEP0 / "grid.nc")
    glat, glon = grid["lat"].values, grid["lon"].values
    ny, nx = len(glat), len(glon)
    cell_area = grid["cell_area_km2"].values.astype(np.float64).ravel()
    grid.close()
    drawn = np.fromfile(C.STEP1 / "maps" / "cells.u32", "<u4").astype(np.int64)
    n = len(drawn)
    area = cell_area[drawn]
    W = sparse.csr_matrix(area[None, :])                         # one unit: every drawn cell at full area
    total = np.array([area.sum()])
    step = np.frombuffer(gzip.open(C.SITE_DATA / "cell_step.u8.gz").read(), np.uint8).astype(bool)
    assert len(step) == n
    step_share = float(area[step].sum() / area.sum())
    step_majority = step_share > K.UNIT_FLAG_MAJORITY
    log(f"{n:,} cells, {total[0]:,.0f} km2; step_1984 share of area {step_share:.3f}, majority {step_majority}")

    ldir = STEP6 / "layers"
    ldir.mkdir(parents=True, exist_ok=True)
    for index in indices:
        for scale in scales:
            tag = f"{index}{scale:02d}"
            path, var, catvar = source_of(index, scale)
            ds, sub = open_window(path, var)
            assert np.array_equal(sub["lat"].values, glat) and np.array_equal(sub["lon"].values, glon), "grid differs from step 0"
            v = K.to_float(sub.values.reshape(K.N_MONTHS, ny * nx)[:, drawn])
            if catvar:
                lat0 = int(np.flatnonzero(ds["lat"].values == glat[0])[0])
                lon0 = int(np.flatnonzero(ds["lon"].values == glon[0])[0])
                cat = ds[catvar].isel(lat=slice(lat0, lat0 + ny), lon=slice(lon0, lon0 + nx))
                cls = K.classify_eddi_cat(cat.values.reshape(K.N_MONTHS, ny * nx)[:, drawn])
                scheme = K.class_scheme(index, ds[catvar].attrs)
            else:
                cls = K.classify_spi(v)
                scheme = K.class_scheme(index)
            ds.close()
            codes = [c for c, _, _ in scheme]
            a, valid, mean = unit_stats(cls, v, W, codes)
            s_enc, m_enc, _ = encode(a, valid, mean, total, 1)
            sdry = side_share(a, valid, scheme, "dry")
            swet = side_share(a, valid, scheme, "wet")
            cols = step2_events.event_table(mean, sdry, swet, index, scale, np.array([step_majority]))
            summ = step2_events.summarise(cols, np.array([1]), np.array(["ID"]), np.isfinite(mean).sum(axis=0), mean.shape[0])
            summ = summ.astype(object).where(summ.notna(), None)

            sizes = {}
            sizes["share"] = gz_write(out / f"{tag}_share.u16.gz", s_enc.astype("<u2").tobytes())
            sizes["mean"] = gz_write(out / f"{tag}_mean.i16.gz", m_enc.astype("<i2").tobytes())
            (out / f"{tag}_events.json").write_text(events_json(cols, columns=list(cols)), encoding="utf-8")
            (out / f"{tag}_summary.json").write_text(summary_json(summ), encoding="utf-8")
            ok = np.isfinite(mean[:, 0])
            rec = dict(
                tag=tag, index=index, scale=scale, source=provenance(path), classes=codes,
                months_with_value=int(ok.sum()), first_month_with_value=int(np.flatnonzero(ok)[0]),
                mean_min=float(np.nanmin(mean)), mean_max=float(np.nanmax(mean)),
                events_dry=int((cols["side"] == 0).sum()), events_wet=int((cols["side"] == 1).sum()),
                latest=dict(mean=float(mean[-1, 0]), dry=float(sdry[-1, 0]), wet=float(swet[-1, 0])), bytes=sizes)
            (ldir / f"{tag}.json").write_text(json.dumps(rec), encoding="utf-8")
            log(f"{tag}: mean {rec['mean_min']:+.2f} to {rec['mean_max']:+.2f}; events dry {rec['events_dry']}, wet {rec['events_wet']}; "
                f"latest month mean {rec['latest']['mean']:+.2f}, dry {rec['latest']['dry']:.1%}, wet {rec['latest']['wet']:.1%}")

    layers = {f.stem: json.load(open(f, encoding="utf-8")) for f in sorted(ldir.glob("*.json"))}
    meta = dict(
        created=datetime.now().isoformat(timespec="seconds"),
        unit=dict(id=1, code="ID", name=NAME, n_cells=int(n), cells_km2=float(total[0]), step_1984_share=step_share,
                  step_1984_majority=bool(step_majority), supported=True),
        rule="every land cell touched by any Indonesian unit, each at its full area; not the sum of the provinces",
        layers=layers)
    (C.SITE_DATA / "national.json").write_text(json.dumps(meta, separators=(",", ":")), encoding="utf-8")
    lines = ["// Generated by pipeline/step6_national.py. Do not edit.", 'import {FileAttachment} from "observablehq:stdlib";',
             "export const nationalFiles = {", '  meta: FileAttachment("national.json"),', "  layers: {"]
    for tag in sorted(layers):
        b = f"national/{tag}"
        lines.append(f'    {js_key(tag)}: {{share: FileAttachment("{b}_share.u16.gz"), mean: FileAttachment("{b}_mean.i16.gz"), '
                     f'events: FileAttachment("{b}_events.json"), summary: FileAttachment("{b}_summary.json")}},')
    lines += ["  }", "};", ""]
    (C.SITE_DATA / "national_files.js").write_text("\n".join(lines), encoding="utf-8")
    log(f"done: {len(layers)} layers")


if __name__ == "__main__":
    main()
