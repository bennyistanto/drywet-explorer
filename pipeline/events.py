"""Event scan: WMO-No. 1090 section 6.1, vectorised over series.

`scan_events` takes a "dryness" array d[time, series] in which the event's own
side is POSITIVE: for a dry SPI event pass -SPI; for a wet SPI event pass SPI;
for EDDI the signs are the other way round (conventions.DRY_SIGN). The scan
itself knows nothing about indices or direction.

Rule (conventions.EVENT_RULE)
  start     first month with d >= onset
  continue  while d >= 0 (exactly 0 continues: the index has not become positive)
  end       the month before d < 0, or before a missing month
  open      still running in the last month of the record

Returned per event: series, start, end (inclusive month positions), duration,
magnitude (sum of d), peak (largest d) and its month, n_onset (months with
d >= onset), open, ended_by_missing, and, if `extra` is given, the largest
value of `extra` during the event and its month (used for the peak area share).
"""
import numpy as np


def scan_events(d, onset=1.0, extra=None):
    d = np.asarray(d, dtype=np.float64)
    nt, ns = d.shape
    active = np.zeros(ns, bool)
    start = np.zeros(ns, np.int32)
    dur = np.zeros(ns, np.int32)
    mag = np.zeros(ns, np.float64)
    peak = np.zeros(ns, np.float64)
    peak_t = np.zeros(ns, np.int32)
    n_on = np.zeros(ns, np.int32)
    ex = np.full(ns, np.nan)
    ex_t = np.full(ns, -1, np.int32)
    out = {k: [] for k in ("series", "start", "end", "duration", "magnitude", "peak", "peak_t", "n_onset",
                           "open", "ended_by_missing", "extra_max", "extra_t")}

    def emit(sel, end_t, is_open, missing):
        idx = np.flatnonzero(sel)
        if idx.size == 0:
            return
        out["series"].append(idx.astype(np.int32))
        out["start"].append(start[idx].copy())
        out["end"].append(np.full(idx.size, end_t, np.int32))
        out["duration"].append(dur[idx].copy())
        out["magnitude"].append(mag[idx].copy())
        out["peak"].append(peak[idx].copy())
        out["peak_t"].append(peak_t[idx].copy())
        out["n_onset"].append(n_on[idx].copy())
        out["open"].append(np.full(idx.size, is_open, bool))
        out["ended_by_missing"].append(missing[idx].copy() if missing is not None else np.zeros(idx.size, bool))
        out["extra_max"].append(ex[idx].copy())
        out["extra_t"].append(ex_t[idx].copy())

    for t in range(nt):
        x = d[t]
        fin = np.isfinite(x)
        cont = active & fin & (x >= 0)
        ending = active & ~cont
        emit(ending, t - 1, False, ~fin)
        active = cont
        begin = ~active & ~ending & fin & (x >= onset)
        # a series that just ended cannot restart in the same month: x < 0 or missing there
        start[begin] = t
        dur[begin] = 0
        mag[begin] = 0.0
        peak[begin] = -np.inf
        n_on[begin] = 0
        ex[begin] = np.nan
        ex_t[begin] = -1
        active = active | begin
        xa = np.where(active, x, 0.0)
        dur[active] += 1
        mag[active] += xa[active]
        newpk = active & (xa > peak)
        peak[newpk] = xa[newpk]
        peak_t[newpk] = t
        n_on[active & (xa >= onset)] += 1
        if extra is not None:
            e = extra[t]
            better = active & np.isfinite(e) & (np.isnan(ex) | (e > ex))
            ex[better] = e[better]
            ex_t[better] = t
    emit(active, nt - 1, True, None)
    res = {}
    for k, v in out.items():
        res[k] = np.concatenate(v) if v else np.zeros(0, np.float64 if k in ("magnitude", "peak", "extra_max") else np.int32)
    order = np.lexsort((res["start"], res["series"])) if len(res["series"]) else np.zeros(0, np.int64)
    return {k: v[order] for k, v in res.items()}


def events_reference(series, onset=1.0):
    """Plain per-series implementation of the same rule, for tests and audits. Returns (start, end, open) tuples."""
    ev = []
    n = len(series)
    t = 0
    while t < n:
        x = series[t]
        if np.isfinite(x) and x >= onset:
            s = t
            while t + 1 < n and np.isfinite(series[t + 1]) and series[t + 1] >= 0:
                t += 1
            ev.append((s, t, t == n - 1))
        t += 1
    return ev
