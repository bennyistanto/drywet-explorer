"""Step 9: which side of the water balance is beyond the threshold in each cell, for the "Driver" map.

The three indices measure rainfall (SPI), evaporative demand (EDDI) and the balance of the two (SPEI). At the
same accumulation they are read together, cell by cell and month by month:

  state of an index in a cell   0 neither, 1 dry side, 2 wet side
  dry side                      conventions.is_dry at conventions.EVENT_ONSET  (SPI, SPEI <= -1.0; EDDI >= +1.0)
  wet side                      conventions.is_wet at the same level           (SPI, SPEI >= +1.0; EDDI <= -1.0)

One byte per cell and month:  0 where any of the three has no value, else 1 + spi + 3 * spei + 9 * eddi (1..27).
The page groups the 27 combinations into the legend (rain and demand together, rain alone, demand alone,
water balance only); the grouping lives in site/components/palette.js so that it can change without a rerun.

The threshold is the event onset level, the same for all three, so that "dry" means the same distance from
normal in each. It is NOT the class side of the "This month" map: EDDI's classes start at the 70th percentile,
SPI's at -1.0, and the two would not be comparable. This is a project choice (owner asked for the view on
2026-11-24; the measurement behind it is analysis/index_lead_lag.py).

Writes, straight into the site:
  site/data/driver/s{scale:02d}/{decade}.u8.gz   uint8 [months in the decade, drawn cell]
  site/data/driver.json                          how to decode, per-layer counts
  site/data/driver_files.js                      generated: one literal FileAttachment per file
  data/step9/layers/s{scale:02d}.json            per-layer record

Run from the repository root:
  python -m pipeline.step9_driver          all scales
  python -m pipeline.step9_driver 3,12     some of them
"""
import json
import sys
import time
from datetime import datetime

import numpy as np

from . import config as C
from . import conventions as K
from .step0_grid import open_window, provenance
from .step1_classes import source_of
from .step3_export import gz_write, js_key

T0 = time.time()
STEP9 = C.OUT / "step9"
INDICES = ("spi", "spei", "eddi")
WEIGHT = dict(spi=1, spei=3, eddi=9)


def log(msg):
    print(f"[{time.time() - T0:5.0f}s] {msg}", flush=True)


def state_of(index, values):
    """uint8 per value: 0 neither, 1 dry side, 2 wet side, 255 no value."""
    v = K.to_float(values)
    s = np.zeros(v.shape, np.uint8)
    s[K.is_dry(index, v, K.EVENT_ONSET)] = 1
    s[K.is_wet(index, v, K.EVENT_ONSET)] = 2
    s[~np.isfinite(v)] = 255
    return s


def combine(states):
    """states: {index: uint8 array}. 0 where any index has no value, else 1 + spi + 3 * spei + 9 * eddi."""
    missing = np.zeros(states["spi"].shape, bool)
    code = np.ones(states["spi"].shape, np.uint8)
    for index in INDICES:
        s = states[index]
        missing |= s == 255
        code += (np.where(s == 255, 0, s) * WEIGHT[index]).astype(np.uint8)
    code[missing] = 0
    return code


def decode(code):
    """Inverse of combine for codes 1..27: (spi, spei, eddi) states."""
    k = np.asarray(code).astype(np.int16) - 1
    return k % 3, (k // 3) % 3, k // 9


def main():
    scales = [int(s) for s in sys.argv[1].split(",")] if len(sys.argv) > 1 else list(K.SCALES)
    drawn = np.fromfile(C.STEP1 / "maps" / "cells.u32", "<u4").astype(np.int64)
    n = len(drawn)
    ldir = STEP9 / "layers"
    ldir.mkdir(parents=True, exist_ok=True)
    for scale in scales:
        tag = f"s{scale:02d}"
        states, sources = {}, {}
        for index in INDICES:
            path, var, _ = source_of(index, scale)
            ds, sub = open_window(path, var)
            assert sub.shape[0] == K.N_MONTHS
            states[index] = state_of(index, sub.values.reshape(K.N_MONTHS, -1)[:, drawn])
            sources[index] = provenance(path)
            ds.close()
            log(f"{tag}: read {index}")
        code = combine(states)
        back = decode(code[code > 0])
        for index, b in zip(INDICES, back):
            assert np.array_equal(b, states[index][code > 0]), "combined code does not decode"
        files, size = {}, 0
        for dcd in range(1950, 2030, 10):
            a = (dcd - 1950) * 12
            raw = code[a: a + 120]
            if not len(raw):
                continue
            b = gz_write(C.SITE_DATA / "driver" / tag / f"{dcd}.u8.gz", np.ascontiguousarray(raw).tobytes())
            files[dcd] = dict(file=f"driver/{tag}/{dcd}.u8.gz", first_month=a, months=len(raw), bytes=b)
            size += b
        has = (code > 0).any(axis=1)
        rec = dict(tag=tag, scale=scale, sources=sources, maps=files, bytes=size,
                   first_month_with_value=int(np.flatnonzero(has)[0]),
                   cell_months=np.bincount(code.ravel(), minlength=28).tolist(),
                   latest_month=np.bincount(code[-1], minlength=28).tolist())
        (ldir / f"{tag}.json").write_text(json.dumps(rec), encoding="utf-8")
        cm = np.array(rec["cell_months"], dtype=np.float64)
        valid = cm[1:].sum()
        sp, se, ed = decode(np.arange(1, 28))
        both, rain, dem = (sp == 1) & (ed == 1), (sp == 1) & (ed != 1), (sp != 1) & (ed == 1)
        log(f"{tag}: {size / 1e6:.1f} MB; cell-months dry on rain and demand {cm[1:][both].sum() / valid:.1%}, "
            f"rain alone {cm[1:][rain].sum() / valid:.1%}, demand alone {cm[1:][dem].sum() / valid:.1%}, "
            f"balance only {cm[1:][(sp != 1) & (ed != 1) & (se == 1)].sum() / valid:.1%}")

    layers = {f.stem: json.load(open(f, encoding="utf-8")) for f in sorted(ldir.glob("*.json"))}
    meta = dict(
        created=datetime.now().isoformat(timespec="seconds"), n_drawn=int(n), level=K.EVENT_ONSET,
        rule="per cell and month: each index is dry, wet or neither at the event onset level, on the same accumulation",
        note="the level and the grouping into drivers are this project's own, proposed",
        encoding="0 no value in at least one index; else 1 + spi + 3 * spei + 9 * eddi, each 0 neither, 1 dry side, 2 wet side",
        layers=layers)
    (C.SITE_DATA / "driver.json").write_text(json.dumps(meta, separators=(",", ":")), encoding="utf-8")
    lines = ["// Generated by pipeline/step9_driver.py. Do not edit.", 'import {FileAttachment} from "observablehq:stdlib";',
             "export const driverFiles = {", '  meta: FileAttachment("driver.json"),', "  layers: {"]
    for tag, L in sorted(layers.items()):
        lines.append(f"    {js_key(tag)}: {{" + ", ".join(f'{d}: FileAttachment("{f["file"]}")' for d, f in sorted(L["maps"].items(), key=lambda kv: int(kv[0]))) + "},")
    lines += ["  }", "};", ""]
    (C.SITE_DATA / "driver_files.js").write_text("\n".join(lines), encoding="utf-8")
    log(f"done: {len(layers)} layers, {sum(L['bytes'] for L in layers.values()) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
