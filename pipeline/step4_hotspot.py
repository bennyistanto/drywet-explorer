"""Step 4 (a TEST, owner 2026-11-21): emerging hot spot pattern of every drawn cell, for every month.

For each index and scale, and each month t, the space-time cube is the HOTSPOT_WINDOW months ending at t.
pipeline/hotspot.py holds the method (Gi* per bin, Mann-Kendall on each cell's Gi* series, 17 categories)
and says which parts follow Esri's pages and which are choices made here. The cube ends at the month on
the map, so "the final time step" is the month the reader is looking at.

Hot and cold are measured against hotspot.REFERENCE (now climatology: mean 0, sd 1), not against the
cube's own average as Esri's tool does; pipeline/hotspot.py z_from_sums says why.

The value is the index with positive = dry, on the cells the map draws (all touched, as everywhere else).
Cells outside Indonesia's units are not part of the cube: a coastal cell's neighbourhood holds fewer bins.

Writes, straight into the site (nothing here feeds another step):
  site/data/hotspot/{tag}/{decade}.u8.gz   uint8 [months in the decade, drawn cell]
                                           0 = no result, else category + 9 (1..8 cold -8..-1, 9 none, 10..17 hot 1..8)
  site/data/hotspot.json                   categories, parameters, per-layer file list and category counts
  site/data/hotspot_files.js               generated: one literal FileAttachment per file
  data/step4/manifest.json                 the same parameters and counts, with provenance

Run from the repository root:
  python -m pipeline.step4_hotspot              all indices and scales
  python -m pipeline.step4_hotspot spi 3,12     some of them (the file lists then cover those only)
"""
import json
import sys
import time
from datetime import datetime

import numpy as np
from scipy.ndimage import uniform_filter

from . import config as C
from . import conventions as K
from . import hotspot as H
from .step0_grid import open_window, provenance, versions
from .step1_classes import source_of
from .step3_export import gz_write, js_key

T0 = time.time()
WINDOW = K.HOTSPOT_WINDOW
CHUNK = 60


def log(msg):
    print(f"[{time.time() - T0:5.0f}s] {msg}", flush=True)


def neighbourhood_sums(sub, sign, drawn, shape):
    """Read one layer and return, on the drawn cells, [month, cell] arrays of the value (positive = dry),
    the neighbourhood sum and the neighbourhood count. Row 0 of the sums is not usable: it has no step back."""
    ny, nx = shape
    nT, n = sub.shape[0], len(drawn)
    mask = np.zeros(ny * nx, bool)
    mask[drawn] = True
    mask = mask.reshape(ny, nx)
    v = np.full((nT, n), np.nan, np.float32)
    s1 = np.zeros((nT, n), np.float32)          # spatial sums of each month alone
    w1 = np.zeros((nT, n), np.uint8)
    k = H.SPATIAL * H.SPATIAL
    for a in range(0, nT, CHUNK):
        x = K.to_float(sub.isel(time=slice(a, a + CHUNK)).values) * sign
        x[:, ~mask] = np.nan
        ok = np.isfinite(x)
        xs = uniform_filter(np.where(ok, x, 0.0).astype(np.float64), size=(1, H.SPATIAL, H.SPATIAL), mode="constant") * k
        ws = uniform_filter(ok.astype(np.float64), size=(1, H.SPATIAL, H.SPATIAL), mode="constant") * k
        b = slice(a, a + x.shape[0])
        v[b] = x.reshape(x.shape[0], -1)[:, drawn]
        s1[b] = xs.reshape(x.shape[0], -1)[:, drawn]
        w1[b] = np.rint(ws.reshape(x.shape[0], -1)[:, drawn])
    sx = s1.astype(np.float64)
    sw = w1.astype(np.float64)
    for back in range(1, H.TIME_STEP + 1):
        sx[back:] += s1[:-back]
        sw[back:] += w1[:-back]
    return v, sx, sw


def main():
    indices = sys.argv[1].split(",") if len(sys.argv) > 1 else ["spi", "spei", "eddi"]
    scales = [int(s) for s in sys.argv[2].split(",")] if len(sys.argv) > 2 else list(K.SCALES)
    out = C.SITE_DATA / "hotspot"
    drawn = np.fromfile(C.STEP1 / "maps" / "cells.u32", "<u4")
    n = len(drawn)
    codes = sorted(H.CATEGORIES)
    layers, sources = {}, {}
    for index in indices:
        for scale in scales:
            tag = f"{index}{scale:02d}"
            path, var, _ = source_of(index, scale)
            ds, sub = open_window(path, var)
            assert sub.shape[0] == K.N_MONTHS
            v, sx, sw = neighbourhood_sums(sub, K.DRY_SIGN[index], drawn, sub.shape[1:])
            ds.close()
            sources[tag] = provenance(path)
            # first month whose whole window, and each bin's step back, has values
            first = (scale - 1) + H.TIME_STEP + WINDOW - 1
            enc = np.zeros((K.N_MONTHS, n), np.uint8)
            counts = np.zeros((K.N_MONTHS, len(codes)), np.int32)
            for t in range(first, K.N_MONTHS):
                w = slice(t - WINDOW + 1, t + 1)
                z = H.z_from_sums(sx[w], sw[w], v[w])
                cat = H.classify(z, fdr=True)
                ok = cat != -128
                enc[t, ok] = (cat[ok].astype(np.int16) + 9).astype(np.uint8)
                counts[t] = [(cat == c).sum() for c in codes]
                if t % 120 == 0:
                    log(f"{tag} month {t}")
            (out / tag).mkdir(parents=True, exist_ok=True)
            files = {}
            for d in range(1950, 2030, 10):
                a = (d - 1950) * 12
                raw = enc[a: a + 120]
                if not len(raw):
                    continue
                name = f"hotspot/{tag}/{d}.u8.gz"
                size = gz_write(out / tag / f"{d}.u8.gz", np.ascontiguousarray(raw).tobytes())
                files[d] = dict(file=name, first_month=a, months=len(raw), bytes=size)
            total = counts[first:].sum(axis=0)
            layers[tag] = dict(
                index=index, scale=scale, first_month_with_result=first, maps=files,
                cell_months={str(c): int(k) for c, k in zip(codes, total)},
                categories_that_occur=[int(c) for c, k in zip(codes, total) if k > 0],
                latest_month={str(c): int(k) for c, k in zip(codes, counts[-1])},
                bytes=int(sum(f["bytes"] for f in files.values())))
            log(f"{tag}: first result month {first}; {len(layers[tag]['categories_that_occur'])} of 17 categories occur; "
                f"{layers[tag]['bytes'] / 1e6:.1f} MB")

    params = dict(
        test=True, window_months=WINDOW, time_step_back=H.TIME_STEP, spatial_cells=H.SPATIAL,
        confidence=0.90, fdr="Benjamini-Hochberg over every bin of the cube, alpha 0.10",
        trend="Mann-Kendall on the Gi* z-scores, 90%", value="index with positive = dry; hot = dry cluster, cold = wet cluster",
        reference=H.REFERENCE, reference_note="climatology: mean 0, sd 1 (the index's baseline); cube: mean and sd of the window over every drawn cell",
        encoding="0 no result; else category + 9", n_drawn=int(n),
        source="https://doc.esri.com/en/arcgis-pro/latest/tool-reference/space-time-pattern-mining/learnmoreemerging.html")
    # One record per layer on disk, so that runs for different indices can go side by side: whichever
    # finishes last writes the site's list from every layer built with these same parameters.
    ldir = C.STEP4 / "layers"
    ldir.mkdir(parents=True, exist_ok=True)
    for tag, L in layers.items():
        (ldir / f"{tag}.json").write_text(json.dumps(dict(parameters=params, source=sources[tag], layer=L)), encoding="utf-8")
    layers, sources = {}, {}
    for f in sorted(ldir.glob("*.json")):
        rec = json.load(open(f, encoding="utf-8"))
        if rec["parameters"] == params:
            layers[f.stem], sources[f.stem] = rec["layer"], rec["source"]
    meta = dict(created=datetime.now().isoformat(timespec="seconds"), parameters=params,
                categories=[dict(category=c, code=c + 9, label=H.CATEGORIES[c]) for c in codes], layers=layers)
    (C.SITE_DATA / "hotspot.json").write_text(json.dumps(meta, separators=(",", ":")), encoding="utf-8")
    lines = ["// Generated by pipeline/step4_hotspot.py. Do not edit.", 'import {FileAttachment} from "observablehq:stdlib";',
             "export const hotspotFiles = {", '  meta: FileAttachment("hotspot.json"),', "  layers: {"]
    for tag, L in sorted(meta["layers"].items()):
        lines.append(f"    {js_key(tag)}: {{" + ", ".join(f'{d}: FileAttachment("{f["file"]}")' for d, f in sorted(L["maps"].items(), key=lambda kv: int(kv[0]))) + "},")
    lines += ["  }", "};", ""]
    (C.SITE_DATA / "hotspot_files.js").write_text("\n".join(lines), encoding="utf-8")
    C.STEP4.mkdir(parents=True, exist_ok=True)
    (C.STEP4 / "manifest.json").write_text(json.dumps(dict(meta, sources=sources, versions=versions()), indent=1), encoding="utf-8")
    log(f"done: {sum(L['bytes'] for L in meta['layers'].values()) / 1e6:.1f} MB in {len(meta['layers'])} layers")


if __name__ == "__main__":
    main()
