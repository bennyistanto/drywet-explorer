"""Step 2: EVENTS. Onset to termination, per admin unit, for every layer.

Built in the same pass as step 1 (`python -m pipeline.step1_classes`), because
events are found on the UNROUNDED unit mean, which exists only in memory there.
Finding them on the stored, rounded mean changed the start or end of 2 to 4% of
kecamatan events (method review, 2026-11-20). This module holds the functions;
running it alone only explains that.

Writes to data/step2/:
  events/{index}{scale:02d}_adm{n}.npz   one row per event; columns in EVENT_COLUMNS
  summary/{index}{scale:02d}_adm{n}.csv  one row per unit and side; columns in SUMMARY_COLUMNS
  manifest.json

Method
  Rule: conventions.EVENT_RULE (WMO-No. 1090 section 6.1; owner decision 2026-11-20).
  Series: the unit's area-weighted MEAN index over its all-touched cells, in
    float64. PROPOSED choice; an event here is "the unit as a whole crossed the
    onset level", not "some part of the unit did".
  Sides: dry and wet are scanned separately. Direction per index comes from
    conventions.DRY_SIGN: an EDDI dry event is high evaporative demand and an
    EDDI "wet" event is low demand, not wet conditions.
  Flags: rules in conventions, both confirmed by the owner.
  Figures a reader could take as a record (count, longest, largest, per decade)
    are given for all events and for unflagged events only.
"""
import json
from datetime import datetime

import numpy as np
import pandas as pd

from . import config as C
from . import conventions as K
from .events import scan_events

DECADES = tuple(range(1950, 2030, 10))

EVENT_COLUMNS = dict(
    unit="unit id (units_adm{n}.csv)",
    side="0 dry, 1 wet; for EDDI, 1 is low evaporative demand",
    start="first month, 0-based position from the first month of the record",
    end="last month, inclusive",
    duration="months from start to end",
    magnitude="sum of the absolute unit-mean index over the event",
    peak="most extreme unit-mean index during the event, as a positive number",
    peak_t="month position of the peak",
    n_onset="months of the event at or beyond the onset level: the STATE months",
    max_share="largest share of the unit's area in classes on the event's side during the event, 0..1",
    max_share_t="month position of max_share",
    open="still running in the last month of the record; duration is so far",
    ended_by_missing="ended because the next month had no value",
    n_early="months of the event inside early_record",
    step_flagged="unit is step_1984 majority and the event starts on or before that flag's last month for this scale",
    flagged="n_early > 0 or step_flagged",
)
SUMMARY_COLUMNS = dict(
    valid_months="months in which the unit has a value",
    n_events="events on this side", n_events_unflagged="of which unflagged",
    months_in_events="sum of durations", months_in_events_unflagged="same, unflagged events only",
    share_of_months_in_events="months_in_events / valid_months",
    longest_months="longest event", longest_start="its first month", longest_is_open="it is still running: so far",
    longest_unflagged_months="longest unflagged event", longest_unflagged_start="its first month",
    longest_unflagged_is_open="it is still running: so far",
    max_magnitude="largest magnitude", max_magnitude_unflagged="largest magnitude among unflagged events",
    in_event_now="an event is running in the last month", current_start="its first month",
    current_months="its duration so far", current_flagged="it is flagged",
    last_closed_end="last month of the most recent finished event",
    months_since_last_closed="months from that month to the last month of the record",
    started_DECADEs="events that started in the decade", started_DECADEs_unflagged="same, unflagged events only",
)


def ym(t):
    """Month positions -> 'YYYY-MM' strings."""
    y0, m0 = (int(x) for x in K.PERIOD[0].split("-"))
    k = (m0 - 1) + np.asarray(t, dtype=np.int64)
    return np.char.add(np.char.add((y0 + k // 12).astype(str), "-"), np.char.zfill(((k % 12) + 1).astype(str), 2))


def event_table(mean, share_dry, share_wet, index, scale, unit_step_majority):
    """All events of one layer at one admin level.

    mean, share_dry, share_wet: float [month, unit], NaN where there is no value.
    unit_step_majority: bool [unit]. Returns a dict of equal-length arrays (EVENT_COLUMNS).
    """
    early_end = K.month_position(K.FLAG_EARLY_RECORD["end"])
    step_end = K.step_1984_last_position(scale)
    maj = np.asarray(unit_step_majority, dtype=bool)
    parts = []
    for s_code, share in ((0, share_dry), (1, share_wet)):
        d = np.asarray(mean, dtype=np.float64) * K.DRY_SIGN[index] * (1 if s_code == 0 else -1)
        ev = scan_events(d, onset=K.EVENT_ONSET, extra=share)
        ne = len(ev["series"])
        n_early = np.clip(np.minimum(ev["end"], early_end) - ev["start"] + 1, 0, None)
        step_f = maj[ev["series"]] & (ev["start"] <= step_end) if ne else np.zeros(0, bool)
        parts.append(dict(
            unit=ev["series"].astype(np.int32) + 1, side=np.full(ne, s_code, np.uint8),
            start=ev["start"].astype(np.int16), end=ev["end"].astype(np.int16),
            duration=ev["duration"].astype(np.int16), magnitude=ev["magnitude"].astype(np.float32),
            peak=ev["peak"].astype(np.float32), peak_t=ev["peak_t"].astype(np.int16),
            n_onset=ev["n_onset"].astype(np.int16), max_share=ev["extra_max"].astype(np.float32),
            max_share_t=ev["extra_t"].astype(np.int16), open=ev["open"].astype(bool),
            ended_by_missing=ev["ended_by_missing"].astype(bool), n_early=n_early.astype(np.int16),
            step_flagged=np.asarray(step_f, dtype=bool), flagged=(n_early > 0) | np.asarray(step_f, dtype=bool)))
    return {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}


def _pick_longest(df, src, name):
    """Longest event per unit from `src` (earliest wins a tie), written into df."""
    if len(src):
        ix = src.groupby("unit")["duration"].idxmax()
        best = src.loc[ix].set_index("unit")
        df[f"{name}_months"] = best["duration"].reindex(df.index)
        st = best["start"].reindex(df.index)
        df[f"{name}_start"] = pd.Series(np.where(st.notna(), ym(st.fillna(0).to_numpy(dtype=int)), ""), index=df.index)
        df[f"{name}_is_open"] = best["open"].reindex(df.index).eq(True)
    else:
        df[f"{name}_months"] = np.nan
        df[f"{name}_start"] = ""
        df[f"{name}_is_open"] = False


def summarise(cols, unit_ids, unit_codes, valid_months, nt):
    """One row per unit and side from an event table (SUMMARY_COLUMNS)."""
    e = pd.DataFrame(cols)
    e["decade"] = 1950 + (e["start"].to_numpy().astype(int) // 120) * 10
    rows = []
    for s_code, side in ((0, "dry"), (1, "wet")):
        es = e[e["side"] == s_code]
        eu = es[~es["flagged"]]
        g, gu = es.groupby("unit"), eu.groupby("unit")
        df = pd.DataFrame(dict(id=np.asarray(unit_ids), code=np.asarray(unit_codes), side=side)).set_index("id")
        df["valid_months"] = np.asarray(valid_months)
        df["n_events"] = g.size().reindex(df.index, fill_value=0)
        df["n_events_unflagged"] = gu.size().reindex(df.index, fill_value=0)
        df["months_in_events"] = g["duration"].sum().reindex(df.index, fill_value=0)
        df["months_in_events_unflagged"] = gu["duration"].sum().reindex(df.index, fill_value=0)
        df["share_of_months_in_events"] = np.round(df["months_in_events"] / df["valid_months"].where(df["valid_months"] > 0), 4)
        _pick_longest(df, es, "longest")
        _pick_longest(df, eu, "longest_unflagged")
        df["max_magnitude"] = np.round(g["magnitude"].max().reindex(df.index), 3)
        df["max_magnitude_unflagged"] = np.round(gu["magnitude"].max().reindex(df.index), 3)
        op = es[es["open"]].set_index("unit")
        df["in_event_now"] = df.index.isin(op.index)
        st = op["start"].reindex(df.index)
        df["current_start"] = pd.Series(np.where(st.notna(), ym(st.fillna(0).to_numpy(dtype=int)), ""), index=df.index)
        df["current_months"] = op["duration"].reindex(df.index)
        df["current_flagged"] = op["flagged"].reindex(df.index)
        cl = es[~es["open"]].groupby("unit")["end"].max().reindex(df.index)
        df["last_closed_end"] = pd.Series(np.where(cl.notna(), ym(cl.fillna(0).to_numpy(dtype=int)), ""), index=df.index)
        df["months_since_last_closed"] = (nt - 1 - cl)
        for label, src in (("", es), ("_unflagged", eu)):
            dec = src.groupby(["unit", "decade"]).size().unstack(fill_value=0) if len(src) else pd.DataFrame()
            for dcd in DECADES:
                df[f"started_{dcd}s{label}"] = dec[dcd].reindex(df.index, fill_value=0) if dcd in dec else 0
        rows.append(df.reset_index())
    return pd.concat(rows, ignore_index=True)


def build(tag, n, index, scale, mean, share_dry, share_wet, units):
    """Write the event table and summary for one layer and level. Returns statistics for the manifest."""
    (C.STEP2 / "events").mkdir(parents=True, exist_ok=True)
    (C.STEP2 / "summary").mkdir(parents=True, exist_ok=True)
    assert mean.shape[1] == len(units), "unit axis does not match the unit table"
    cols = event_table(mean, share_dry, share_wet, index, scale, units["step_1984_majority"].to_numpy(dtype=bool))
    ep = C.STEP2 / "events" / f"{tag}_adm{n}.npz"
    np.savez_compressed(ep, **cols)
    summ = summarise(cols, units["id"].to_numpy(), units["code"].to_numpy(), np.isfinite(mean).sum(axis=0), mean.shape[0])
    sp = C.STEP2 / "summary" / f"{tag}_adm{n}.csv"
    summ.to_csv(sp, index=False, encoding="utf-8")
    e = pd.DataFrame(cols)
    dry, wet = e[e["side"] == 0], e[e["side"] == 1]
    unf = e[~e["flagged"]]
    return dict(
        events=int(len(e)), dry=int(len(dry)), wet=int(len(wet)), flagged=int(e["flagged"].sum()),
        step_flagged=int(e["step_flagged"].sum()), open_dry_units=int(dry["open"].sum()),
        open_wet_units=int(wet["open"].sum()),
        mean_duration_dry=float(dry["duration"].mean()) if len(dry) else None,
        mean_duration_wet=float(wet["duration"].mean()) if len(wet) else None,
        longest=int(e["duration"].max()) if len(e) else 0,
        longest_unflagged=int(unf["duration"].max()) if len(unf) else 0,
        ended_by_missing=int(e["ended_by_missing"].sum()),
        max_share_max=float(np.nanmax(e["max_share"])) if len(e) else None,
        step_last_position=int(K.step_1984_last_position(scale)),
        outputs={ep.name: ep.stat().st_size, sp.name: sp.stat().st_size})


def write_manifest(layer_stats, layer_sides):
    """Merge this run's layers into data/step2/manifest.json."""
    path = C.STEP2 / "manifest.json"
    man = json.load(open(path, encoding="utf-8")) if path.exists() else {}
    layers = man.get("layers", {})
    layers.update(layer_stats)
    sides = man.get("max_share_classes", {})
    sides.update(layer_sides)
    s0 = json.load(open(C.STEP0 / "manifest.json", encoding="utf-8"))
    from .step0_grid import versions
    man = dict(
        step="step2_events", script="pipeline/step2_events.py, called from pipeline/step1_classes.py",
        updated=datetime.now().isoformat(timespec="seconds"),
        rule=K.EVENT_RULE, rule_decided="owner, 2026-11-20",
        series=dict(what="unit area-weighted mean index over all-touched cells, unrounded float64", status="proposed"),
        sides=dict(dry=0, wet=1, direction=K.DRY_SIGN, eddi_note="EDDI wet side is low evaporative demand"),
        month_position=dict(zero=K.PERIOD[0], last=K.PERIOD[1], n=K.N_MONTHS),
        flags=dict(early_record=K.FLAG_EARLY_RECORD,
                   early_record_last_position=K.month_position(K.FLAG_EARLY_RECORD["end"]),
                   step_1984=K.FLAG_STEP_1984,
                   step_1984_last_position={str(sc): K.step_1984_last_position(sc) for sc in K.SCALES},
                   unit_flag_majority=dict(value=K.UNIT_FLAG_MAJORITY, status="proposed",
                                           source="step_1984_majority in data/step0/units_adm{n}.csv, tested unrounded"),
                   flagged="n_early > 0 or step_flagged"),
        inputs=dict(step0_manifest_created=s0["created"], units="data/step0/units_adm{n}.csv",
                    state="computed in memory by pipeline/step1_classes.py from the source cubes in data/step1/manifest.json"),
        event_columns=EVENT_COLUMNS, summary_columns=SUMMARY_COLUMNS,
        max_share_classes=sides, versions=versions(), layers=layers)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(man, fh, indent=2, default=str)


if __name__ == "__main__":
    raise SystemExit("Events are built in the same pass as step 1, on the unrounded unit mean.\n"
                     "Run: python -m pipeline.step1_classes [index[,index] [scale[,scale]]]")
