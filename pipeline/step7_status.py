"""Step 7: where each cell stands in an event, for two more maps per index and scale.

  HOW LONG   months so far of the event running in the cell, in bins
  STATUS     new, deepening, persisting, easing or ended, for the dry and the wet side

pipeline/status.py defines both and says what is this project's own choice. The event rule is the one of
pipeline/events.py, applied here to every drawn cell's own index (steps 1 and 2 apply it to a unit's mean).
A cell's event is therefore not its unit's event: a kabupaten can be in no event while cells inside it are.

Both maps travel in ONE byte per cell and month (status.combined_code): two separate maps measured 13.4 MB
for one layer, which over twelve layers is more than the site can carry.

Writes, straight into the site:
  site/data/status/{tag}/{decade}.u8.gz    uint8 [months in the decade, drawn cell], combined code
  site/data/status.json                    how to decode, labels, per-layer counts
  site/data/status_files.js                generated: one literal FileAttachment per file
  data/step7/layers/{tag}.json             per-layer record, so that indices can be run side by side

Run from the repository root:
  python -m pipeline.step7_status              all indices and scales
  python -m pipeline.step7_status spi 3,12     some of them
"""
import json
import sys
import time
from datetime import datetime

import numpy as np

from . import config as C
from . import conventions as K
from . import status as S
from .step0_grid import open_window, provenance
from .step1_classes import source_of
from .step3_export import gz_write, js_key

T0 = time.time()
STEP7 = C.OUT / "step7"


def log(msg):
    print(f"[{time.time() - T0:5.0f}s] {msg}", flush=True)


def main():
    indices = sys.argv[1].split(",") if len(sys.argv) > 1 else ["spi", "spei", "eddi"]
    scales = [int(s) for s in sys.argv[2].split(",")] if len(sys.argv) > 2 else list(K.SCALES)
    drawn = np.fromfile(C.STEP1 / "maps" / "cells.u32", "<u4").astype(np.int64)
    n = len(drawn)
    ldir = STEP7 / "layers"
    ldir.mkdir(parents=True, exist_ok=True)
    for index in indices:
        for scale in scales:
            tag = f"{index}{scale:02d}"
            path, var, _ = source_of(index, scale)
            ds, sub = open_window(path, var)
            assert sub.shape[0] == K.N_MONTHS
            d = K.to_float(sub.values.reshape(K.N_MONTHS, -1)[:, drawn]) * K.DRY_SIGN[index]      # dry side positive
            ds.close()
            dd, dw = S.running(d, K.EVENT_ONSET), S.running(-d, K.EVENT_ONSET)
            assert not ((dd > 0) & (dw > 0)).any(), "a cell is in a dry and a wet event at once"
            howlong = S.duration_code(dd, dw, np.isfinite(d))
            status = S.status_code(d, dd, dw, K.EVENT_ONSET)
            code = S.combined_code(status, howlong)
            back = S.decode_combined(code)
            assert np.array_equal(back[0], status) and np.array_equal(back[1], howlong), "combined code does not decode"
            files, size = {}, 0
            for dcd in range(1950, 2030, 10):
                a = (dcd - 1950) * 12
                raw = code[a: a + 120]
                if not len(raw):
                    continue
                b = gz_write(C.SITE_DATA / "status" / tag / f"{dcd}.u8.gz", np.ascontiguousarray(raw).tobytes())
                files[dcd] = dict(file=f"status/{tag}/{dcd}.u8.gz", first_month=a, months=len(raw), bytes=b)
                size += b
            st_all, st_now = np.bincount(status.ravel(), minlength=12), np.bincount(status[-1], minlength=12)
            rec = dict(tag=tag, index=index, scale=scale, source=provenance(path), maps=files, bytes=size,
                       cell_months=dict(status=st_all.tolist(), howlong=np.bincount(howlong.ravel(), minlength=12).tolist()),
                       latest_month=dict(status=st_now.tolist(), howlong=np.bincount(howlong[-1], minlength=12).tolist()),
                       longest_running=dict(dry=int(dd.max()), wet=int(dw.max())))
            (ldir / f"{tag}.json").write_text(json.dumps(rec), encoding="utf-8")
            log(f"{tag}: {size / 1e6:.1f} MB; longest running dry {rec['longest_running']['dry']}, wet {rec['longest_running']['wet']} months; "
                f"latest month in a dry event {st_now[2:6].sum() / n:.1%}, in a wet event {st_now[7:11].sum() / n:.1%}")

    layers = {f.stem: json.load(open(f, encoding="utf-8")) for f in sorted(ldir.glob("*.json"))}
    meta = dict(
        created=datetime.now().isoformat(timespec="seconds"), n_drawn=int(n), onset=K.EVENT_ONSET, new_months=S.NEW_MONTHS,
        rule="events of each cell's own index, by the rule of pipeline/events.py (WMO-No. 1090 section 6.1)",
        note="the five states and the duration bins are this project's own, proposed",
        encoding="0 no value; 1 no event; else 2 + side * 25 + state * 5 + bin (side 0 dry, 1 wet; bin 0 for 'ended')",
        states=list(S.STATES), bins=[dict(label=lab, months=[lo, hi]) for lo, hi, lab in S.DURATION_BINS], layers=layers)
    (C.SITE_DATA / "status.json").write_text(json.dumps(meta, separators=(",", ":")), encoding="utf-8")
    lines = ["// Generated by pipeline/step7_status.py. Do not edit.", 'import {FileAttachment} from "observablehq:stdlib";',
             "export const statusFiles = {", '  meta: FileAttachment("status.json"),', "  layers: {"]
    for tag, L in sorted(layers.items()):
        lines.append(f"    {js_key(tag)}: {{" + ", ".join(f'{d}: FileAttachment("{f["file"]}")' for d, f in sorted(L["maps"].items(), key=lambda kv: int(kv[0]))) + "},")
    lines += ["  }", "};", ""]
    (C.SITE_DATA / "status_files.js").write_text("\n".join(lines), encoding="utf-8")
    log(f"done: {len(layers)} layers, {sum(L['bytes'] for L in layers.values()) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
