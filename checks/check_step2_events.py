"""Independent check of step 2 events and summaries, from the source cubes.

Events are found on the UNROUNDED unit mean, which is not stored. So for three
layers this script reads the source cube itself with netCDF4, builds each
sampled unit's mean and side shares from its all-touched cells in float64,
finds events with a plain loop written here, and compares every stored field
and the summary row. Nothing is imported from pipeline.events, step1 or step2.

Run from the repository root: python checks/check_step2_events.py
"""
import json
import sys
from pathlib import Path

import netCDF4
import numpy as np
import pandas as pd
import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline import config as C  # noqa: E402

SEED = 835127
LAYERS = (("spi", 3), ("spei", 12), ("eddi", 6))
N_UNITS = {1: 6, 2: 14, 3: 20}
rng = np.random.default_rng(SEED)
m1 = json.load(open(C.STEP1 / "manifest.json", encoding="utf-8"))
m2 = json.load(open(C.STEP2 / "manifest.json", encoding="utf-8"))
SIGN = {"spi": -1, "spei": -1, "eddi": 1}          # dry side, written out here on purpose
EARLY_LAST = (1969 - 1950) * 12 + 11
STEP_LAST_1 = (1983 - 1950) * 12 + 11
NT = 912
print(f"seed {SEED}; manifest step_1984 last positions {m2['flags']['step_1984_last_position']}")

grid = xr.open_dataset(C.STEP0 / "grid.nc")
lat, lon = grid["lat"].values, grid["lon"].values
land = grid["land"].values.astype(bool).ravel()
area = grid["cell_area_km2"].values.astype(np.float64).ravel()
ny, nx = len(lat), len(lon)
units = {n: pd.read_csv(C.STEP0 / f"units_adm{n}.csv", dtype={"code": str}) for n in (1, 2, 3)}
wts = {n: np.load(C.STEP0 / f"weights_adm{n}.npz") for n in (1, 2, 3)}
SRC = {"spi": (C.SPI_FILE, C.SPI_VAR), "spei": (C.SPEI_FILE, C.SPEI_VAR), "eddi": (C.EDDI_FILE, C.EDDI_VAR)}


def ym(t):
    return f"{1950 + t // 12}-{t % 12 + 1:02d}"


def spi_class(v):
    c = np.zeros(v.shape, int)
    f = np.isfinite(v)
    c[f & (v <= -2)] = 1
    c[f & (v > -2) & (v <= -1.5)] = 2
    c[f & (v > -1.5) & (v <= -1)] = 3
    c[f & (v > -1) & (v < 1)] = 4
    c[f & (v >= 1) & (v < 1.5)] = 5
    c[f & (v >= 1.5) & (v < 2)] = 6
    c[f & (v >= 2)] = 7
    return c


def plain_events(x, share):
    out, t = [], 0
    while t < NT:
        if not np.isnan(x[t]) and x[t] >= 1.0:
            s, miss = t, False
            while t + 1 < NT:
                if np.isnan(x[t + 1]):
                    miss = True
                    break
                if x[t + 1] < 0:
                    break
                t += 1
            seg, sh = x[s:t + 1], share[s:t + 1]
            has = np.isfinite(sh).any()
            out.append(dict(start=s, end=t, duration=t - s + 1, magnitude=float(seg.sum()), peak=float(seg.max()),
                            peak_t=s + int(np.argmax(seg)), n_onset=int((seg >= 1.0).sum()), open=(t == NT - 1),
                            ended_by_missing=miss and t != NT - 1,
                            max_share=float(np.nanmax(sh)) if has else float("nan"),
                            max_share_t=s + int(np.nanargmax(sh)) if has else -1))
        t += 1
    return out


def same(got, want):
    if isinstance(want, float):
        if np.isnan(want):
            return bool(np.isnan(got))
        return abs(float(got) - want) <= 2e-6 * max(1.0, abs(want))     # float32 storage of a float64 value
    return got == want


tot_events = tot_bad = tot_sides = 0
over_one = 0
for index, scale in LAYERS:
    tag = f"{index}{scale:02d}"
    L = m1["layers"][tag]
    nc = netCDF4.Dataset(SRC[index][0].format(n=scale))
    j0 = int(np.argmin(np.abs(nc["lat"][:] - lat[0])))
    i0 = int(np.argmin(np.abs(nc["lon"][:] - lon[0])))
    cube = np.ma.filled(nc[SRC[index][1].format(n=scale)][:, j0:j0 + ny, i0:i0 + nx].astype("float64"), np.nan).reshape(NT, ny * nx)
    if index == "eddi":
        cat = np.ma.filled(nc[C.EDDI_CAT_VAR][:, j0:j0 + ny, i0:i0 + nx].astype("float64"), np.nan).reshape(NT, ny * nx)
    nc.close()
    step_last = STEP_LAST_1 + scale - 1
    bad = n_ev = 0
    for n in (1, 2, 3):
        u = units[n]
        pool = u[u["n_cells"] > 0]
        pick = pool.sample(N_UNITS[n], random_state=int(rng.integers(1e9)))
        ev = np.load(C.STEP2 / "events" / f"{tag}_adm{n}.npz")
        over_one += int((ev["max_share"] > 1.0).sum())
        sm = pd.read_csv(C.STEP2 / "summary" / f"{tag}_adm{n}.csv", dtype={"code": str})
        for _, r in pick.iterrows():
            uid = int(r["id"])
            cells = wts[n]["cell"][wts[n]["unit"] == uid].astype(np.int64)
            cells = cells[land[cells]]
            w = area[cells]
            v = cube[:, cells]
            has = np.isfinite(v)
            wv = (w * has).sum(axis=1)
            with np.errstate(invalid="ignore", divide="ignore"):
                mean = np.where(wv > 0, (np.where(has, v, 0.0) * w).sum(axis=1) / wv, np.nan)
            cls = (np.where(np.isfinite(cat[:, cells]), cat[:, cells] + 1, 0).astype(int) if index == "eddi" else spi_class(v))
            majority = bool(r["step_1984_majority"])
            for s_code, side in ((0, "dry"), (1, "wet")):
                codes = [c["code"] for c in L["classes"] if c["side"] == side]
                with np.errstate(invalid="ignore", divide="ignore"):
                    share = np.where(wv > 0, (np.isin(cls, codes) * w).sum(axis=1) / wv, np.nan)
                mine = plain_events(mean * SIGN[index] * (1 if side == "dry" else -1), share)
                sel = (ev["unit"] == uid) & (ev["side"] == s_code)
                order = np.argsort(ev["start"][sel])
                st = {k: ev[k][sel][order] for k in ev.files}
                tot_sides += 1
                n_ev += len(mine)
                if len(mine) != len(st["start"]):
                    bad += 1
                    print(f"  COUNT {tag} adm{n} unit {uid} {side}: stored {len(st['start'])}, rebuilt {len(mine)}")
                    continue
                unfl = []
                for i, e in enumerate(mine):
                    n_early = max(0, min(e["end"], EARLY_LAST) - e["start"] + 1)
                    stepf = majority and e["start"] <= step_last
                    exp = dict(e, n_early=n_early, step_flagged=stepf, flagged=(n_early > 0) or stepf)
                    if not exp["flagged"]:
                        unfl.append(e)
                    for k, want in exp.items():
                        if not same(st[k][i], want):
                            bad += 1
                            print(f"  FIELD {tag} adm{n} unit {uid} {side} event {i} {k}: stored {st[k][i]}, rebuilt {want}")
                row = sm[(sm["id"] == uid) & (sm["side"] == side)].iloc[0]
                lg = max(mine, key=lambda e: (e["duration"], -e["start"]), default=None)
                lu = max(unfl, key=lambda e: (e["duration"], -e["start"]), default=None)
                exp = dict(
                    n_events=len(mine), n_events_unflagged=len(unfl), months_in_events=sum(e["duration"] for e in mine),
                    months_in_events_unflagged=sum(e["duration"] for e in unfl), in_event_now=any(e["open"] for e in mine),
                    longest_months=lg["duration"] if lg else np.nan, longest_is_open=bool(lg["open"]) if lg else False,
                    longest_start=ym(lg["start"]) if lg else "",
                    longest_unflagged_months=lu["duration"] if lu else np.nan,
                    longest_unflagged_is_open=bool(lu["open"]) if lu else False,
                    max_magnitude=round(max((e["magnitude"] for e in mine), default=np.nan), 3),
                    max_magnitude_unflagged=round(max((e["magnitude"] for e in unfl), default=np.nan), 3))
                for dcd in range(1950, 2030, 10):
                    exp[f"started_{dcd}s"] = sum(1 for e in mine if 1950 + (e["start"] // 120) * 10 == dcd)
                    exp[f"started_{dcd}s_unflagged"] = sum(1 for e in unfl if 1950 + (e["start"] // 120) * 10 == dcd)
                for k, want in exp.items():
                    got = row[k]
                    if isinstance(want, str):
                        okk = ("" if pd.isna(got) else str(got)) == want
                    elif isinstance(want, float) and np.isnan(want):
                        okk = pd.isna(got)
                    else:
                        okk = (not pd.isna(got)) and abs(float(got) - float(want)) <= 2e-3
                    if not okk:
                        bad += 1
                        print(f"  SUMMARY {tag} adm{n} unit {uid} {side} {k}: stored {got}, rebuilt {want}")
    never = [c["label"] for c in L["classes"] if not c["occurs"]]
    print(f"{tag}: events compared {n_ev:,}, differences {bad}; classes marked as never occurring {never}; "
          f"attainable bound {L.get('attainable_bound')}")
    tot_events += n_ev
    tot_bad += bad
print(f"\nunit-sides checked {tot_sides}, events compared {tot_events:,}, differences {tot_bad}")
print(f"events with max_share above 1 in the three layers: {over_one}")
for n in (1, 2, 3):
    u = units[n]
    print(f"adm{n}: step_1984 majority units {int(u['step_1984_majority'].sum())}; "
          f"units whose rounded share is exactly 0.5 but are majority {int(((u['step_1984_share'] == 0.5) & u['step_1984_majority']).sum())}")
print("step 2 manifest keys:", sorted(m2))
