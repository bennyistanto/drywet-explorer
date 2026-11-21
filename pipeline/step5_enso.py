"""Step 5: the ENSO table the dashboard's ENSO section reads.

Source: the tables built by the `nino` repo (notebook 02_enso_indices) from NOAA CPC files, under
config.ENSO. Nothing is recomputed here: the index values and the event catalogue are copied, cut to this
project's period, and laid on its month axis.

  RONI  Relative Oceanic Nino Index, 3-month running mean, each season placed on its centre month
        https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt
  ONI   Oceanic Nino Index, the same layout
        https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt
  events  El Nino and La Nina episodes by the rule recorded in the source manifest:
        |index| >= 0.5 for 5 consecutive overlapping seasons, applied to RONI

The phase of a month is the RONI episode it falls in (start and end inclusive), else neutral.
RONI is used, not ONI, as in `nino` (its README gives the reason: NOAA's Climate Prediction Center made it
the primary index in 2026).

Writes site/data/enso.json. Run from the repository root:  python -m pipeline.step5_enso
"""
import json
from datetime import datetime

import numpy as np
import pandas as pd

from . import config as C
from . import conventions as K


def main():
    man = json.load(open(C.ENSO / "enso_manifest.json", encoding="utf-8"))
    m = pd.read_csv(C.ENSO / "indices_monthly.csv", parse_dates=["date"])
    ev = pd.read_csv(C.ENSO / "events.csv", parse_dates=["start", "end", "peak_date"])
    pos = lambda d: (d.year - 1950) * 12 + d.month - 1              # noqa: E731
    m["t"] = [pos(d) for d in m["date"]]
    m = m[(m["t"] >= 0) & (m["t"] < K.N_MONTHS)].sort_values("t")
    assert (m["t"].to_numpy() == np.arange(K.N_MONTHS)).all(), "ENSO table does not cover every month of the record"
    assert m["roni"].notna().all() and m["oni"].notna().all()

    ev = ev[ev["index"] == "roni"].copy()
    ev["t0"] = [pos(d) for d in ev["start"]]
    ev["t1"] = [pos(d) for d in ev["end"]]
    ev["tp"] = [pos(d) for d in ev["peak_date"]]
    ev = ev[ev["t0"] < K.N_MONTHS].sort_values("t0")
    phase = np.zeros(K.N_MONTHS, np.int8)
    events = []
    for r in ev.itertuples():
        sign = 1 if r.phase == "El Nino" else -1
        a, b = max(r.t0, 0), min(r.t1, K.N_MONTHS - 1)
        assert (phase[a: b + 1] == 0).all(), "episodes overlap"
        phase[a: b + 1] = sign
        events.append(dict(phase=sign, start=int(r.t0), end=int(b), runs_past_record=bool(r.t1 > K.N_MONTHS - 1),
                           peak=int(r.tp), peak_value=round(float(r.peak_value), 2), strength=r.amplitude_class,
                           flavour=r.flavour, seasons=int(r.n_seasons)))
    out = dict(
        created=datetime.now().isoformat(timespec="seconds"), index="roni", months=K.N_MONTHS,
        roni=[round(float(x), 2) for x in m["roni"]], oni=[round(float(x), 2) for x in m["oni"]],
        phase=phase.tolist(), events=events,
        counts=dict(el_nino_months=int((phase == 1).sum()), la_nina_months=int((phase == -1).sum()),
                    neutral_months=int((phase == 0).sum()), el_nino_events=sum(e["phase"] == 1 for e in events),
                    la_nina_events=sum(e["phase"] == -1 for e in events)),
        method=dict(event_rule=man["method"]["event_rule"], strength=man["method"]["amplitude_classes"],
                    season_alignment=man["method"]["season_alignment"], flavour=man["method"]["flavour"]),
        sources=dict(roni=man["sources"]["roni"]["url"], oni=man["sources"]["oni"]["url"],
                     retrieved=man["sources"]["roni"]["retrieved"], built_by="nino repo, notebook 02_enso_indices",
                     generated=man["generated"]))
    (C.SITE_DATA / "enso.json").write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    c = out["counts"]
    print(f"enso.json: {c['el_nino_events']} El Nino and {c['la_nina_events']} La Nina episodes in the record; months "
          f"El Nino {c['el_nino_months']}, La Nina {c['la_nina_months']}, neutral {c['neutral_months']}; "
          f"RONI {min(out['roni'])} to {max(out['roni'])}")


if __name__ == "__main__":
    main()
