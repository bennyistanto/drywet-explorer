"""Which index moves first: SPI (rain), SPEI (rain minus demand) or EDDI (demand)?

Question (owner, 2026-11-24): when a dry or wet spell happens, which of the three indices detects it first,
and how do they complement each other, for Indonesia, a province, a kabupaten or a kecamatan?

Everything here is at the level of a UNIT (its area-weighted mean index), on the same accumulation for all
three indices, because that is what the dashboard would show. The cell-level question was measured earlier in
analysis/eddi_early_signal.py.

Inputs, all written by the pipeline (nothing is read from the source cubes):
  data/step1/shares/{tag}_adm{n}.npz    unit mean index per month, stored rounded (0.001; 0.01 for adm3)
  data/step2/events/{tag}_adm{n}.npz    events by the WMO 6.1 rule, found on the unrounded mean
  site/data/national/{tag}_mean.i16.gz, {tag}_events.json, site/data/national.json   the same for Indonesia

Period: the months the page treats as reliable. From 1970-01, or for a unit that is step_1984 majority, from
the month after that flag ends for the scale. Events: unflagged only.

Sections
  A  same-month correlation of dryness between the indices, per unit
  B  correlation at shifts of -3 to +3 months: at which shift do two indices match best
  C  months at or beyond the onset level (1.0): which indices agree, pooled over units
  D  episodes: events of the three indices that overlap in time are one episode. Which indices take part,
     and which started first. ASSUMPTION of this script: "the same episode" = intervals that overlap, chained.

Dryness d = index * DRY_SIGN, so d > 0 is dry for every index. Run from the repository root:
  python analysis/index_lead_lag.py > analysis/index_lead_lag.txt
"""
import gzip
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipeline import conventions as K  # noqa: E402

STEP0, STEP1, STEP2, SITE = ROOT / "data/step0", ROOT / "data/step1", ROOT / "data/step2", ROOT / "site/data"
INDICES = ("spi", "spei", "eddi")
LAGS = range(-3, 4)
MIN_PAIRS = 120          # months needed for a correlation
T = K.N_MONTHS
EARLY_END = K.month_position(K.FLAG_EARLY_RECORD["end"])
ENC = json.load(open(STEP1 / "manifest.json", encoding="utf-8"))["share_encoding"]
LEVELS = (("Indonesia", 0), ("province", 1), ("kabupaten", 2), ("kecamatan", 3))


def load(level, index, scale):
    """Dryness [month, unit] with NaN outside the reliable period, and the unit's unflagged events."""
    tag = f"{index}{scale:02d}"
    if level == 0:
        m = np.frombuffer(gzip.open(SITE / "national" / f"{tag}_mean.i16.gz").read(), "<i2").reshape(T, 1)
        mscale = ENC["per_level"]["adm1"]["mean_scale"]
        ev = {k: np.asarray(v) for k, v in json.load(open(SITE / "national" / f"{tag}_events.json", encoding="utf-8")).items()}
        maj = np.array([json.load(open(SITE / "national.json", encoding="utf-8"))["unit"]["step_1984_majority"]])
    else:
        z = np.load(STEP1 / "shares" / f"{tag}_adm{level}.npz")
        m = z["mean"]
        mscale = ENC["per_level"][f"adm{level}"]["mean_scale"]
        ev = dict(np.load(STEP2 / "events" / f"{tag}_adm{level}.npz"))
        maj = pd.read_csv(STEP0 / f"units_adm{level}.csv")["step_1984_majority"].to_numpy(dtype=bool)
    d = np.where(m == ENC["mean_missing"], np.nan, m.astype(np.float64) / mscale) * K.DRY_SIGN[index]
    first = np.where(maj, K.step_1984_last_position(scale) + 1, EARLY_END + 1)
    d[np.arange(T)[:, None] < first[None, :]] = np.nan
    keep = ~ev["flagged"].astype(bool)
    return d, {k: v[keep] for k, v in ev.items()}


def corr_shift(x, y, lag):
    """Per-unit correlation of x[t] with y[t + lag]. lag > 0: x is the earlier series."""
    if lag > 0:
        a, b = x[:-lag], y[lag:]
    elif lag < 0:
        a, b = x[-lag:], y[:lag]
    else:
        a, b = x, y
    ok = np.isfinite(a) & np.isfinite(b)
    n = ok.sum(axis=0)
    a0, b0 = np.where(ok, a, 0.0), np.where(ok, b, 0.0)
    with np.errstate(invalid="ignore", divide="ignore"):
        ma, mb = a0.sum(0) / n, b0.sum(0) / n
        da, db = np.where(ok, a - ma, 0.0), np.where(ok, b - mb, 0.0)
        r = (da * db).sum(0) / np.sqrt((da * da).sum(0) * (db * db).sum(0))
    r[n < MIN_PAIRS] = np.nan
    return r


def q(v, p):
    v = v[np.isfinite(v)]
    return float(np.percentile(v, p)) if len(v) else float("nan")


def by_unit(ev, side, n_units):
    """List per unit (id - 1) of (start, end, open) arrays for one side."""
    k = ev["side"] == side
    u, s, e, o = ev["unit"][k].astype(int) - 1, ev["start"][k].astype(int), ev["end"][k].astype(int), ev["open"][k].astype(bool)
    order = np.lexsort((s, u))
    u, s, e, o = u[order], s[order], e[order], o[order]
    cut = np.searchsorted(u, np.arange(n_units + 1))
    return [(s[cut[i]:cut[i + 1]], e[cut[i]:cut[i + 1]], o[cut[i]:cut[i + 1]]) for i in range(n_units)]


def episodes(per_index):
    """Merge overlapping events of the three indices into episodes. per_index: {name: (start, end, open)}.
    Returns a list of {name: (first start, last end, any open)}."""
    rows = sorted((int(s), int(e), bool(o), name) for name, (ss, ee, oo) in per_index.items() for s, e, o in zip(ss, ee, oo))
    out, cur, cur_end = [], None, -1
    for s, e, o, name in rows:
        if cur is None or s > cur_end:
            cur = {}
            out.append(cur)
            cur_end = e
        cur_end = max(cur_end, e)
        if name in cur:
            s0, e0, o0 = cur[name]
            cur[name] = (min(s0, s), max(e0, e), o0 or o)
        else:
            cur[name] = (s, e, o)
    return out


def diff_line(label, v):
    v = np.asarray(v)
    if not len(v):
        return f"    {label}: none"
    return (f"    {label}: n={len(v):,}  earlier {np.mean(v < 0):6.1%} | same month {np.mean(v == 0):6.1%} | later {np.mean(v > 0):6.1%}"
            f" | median {np.median(v):+.0f}, mean {v.mean():+.2f} months | within 1 month {np.mean(np.abs(v) <= 1):6.1%}")


def main():
    print("Which index moves first: unit level, same accumulation, reliable months, unflagged events")
    print(f"onset level {K.EVENT_ONSET}; months from 1970-01 (later for step_1984-majority units)\n")
    for scale in K.SCALES:
        for lname, level in LEVELS:
            D, EV = {}, {}
            for index in INDICES:
                D[index], EV[index] = load(level, index, scale)
            n_units = D["spi"].shape[1]
            has = np.isfinite(D["spi"]).sum(0) >= MIN_PAIRS
            print(f"=== {scale}-month, {lname}: {int(has.sum()):,} units with {MIN_PAIRS}+ months ===")

            # A and B
            for a, b in (("eddi", "spi"), ("spei", "spi"), ("eddi", "spei")):
                R = np.array([corr_shift(D[a], D[b], lag) for lag in LAGS])          # [lag, unit]
                r0 = R[list(LAGS).index(0)]
                ok = np.isfinite(R).all(0)
                best = np.array(list(LAGS))[np.argmax(R[:, ok], axis=0)] if ok.any() else np.array([])
                if n_units == 1:
                    print(f"  corr d({a.upper()}[t], {b.upper()}[t+L]) L=-3..+3: " + " ".join(f"{R[i, 0]:+.2f}" for i in range(len(LAGS))))
                else:
                    print(f"  corr d({a.upper()}, {b.upper()}) same month: median {q(r0, 50):+.2f} (p10 {q(r0, 10):+.2f}, p90 {q(r0, 90):+.2f})")
                    print("    median by shift L=-3..+3: " + " ".join(f"{q(R[i], 50):+.2f}" for i in range(len(LAGS))))
                    print("    units whose best shift is L: " + " ".join(f"{l:+d}:{np.mean(best == l):.0%}" for l in LAGS)
                          + f"   (L>0: {a.upper()} earlier)")

            # C: agreement of months at or beyond the onset level
            allok = np.isfinite(D["spi"]) & np.isfinite(D["spei"]) & np.isfinite(D["eddi"])
            for side, sgn in (("dry", 1), ("wet", -1)):
                f = {i: (D[i] * sgn >= K.EVENT_ONSET) & allok for i in INDICES}
                tot = allok.sum()
                combos = Counter()
                code = f["spi"] * 1 + f["spei"] * 2 + f["eddi"] * 4
                for c in range(1, 8):
                    combos[c] = int(((code == c) & allok).sum())
                names = {1: "SPI only", 2: "SPEI only", 4: "EDDI only", 3: "SPI+SPEI", 5: "SPI+EDDI", 6: "SPEI+EDDI", 7: "all three"}
                anyc = sum(combos.values())
                print(f"  {side} months at the onset level in any index: {anyc / tot:.1%} of {tot:,} unit-months; of those: "
                      + ", ".join(f"{names[c]} {combos[c] / max(anyc, 1):.0%}" for c in (7, 3, 6, 5, 1, 2, 4)))

            # D: episodes
            for side, scode in (("dry", 0), ("wet", 1)):
                per = {i: by_unit(EV[i], scode, n_units) for i in INDICES}
                part, first = Counter(), Counter()
                d_es, d_ps, d_ep, e_es = [], [], [], []
                n3 = np.zeros(n_units, int)
                for u in range(n_units):
                    for ep in episodes({i: per[i][u] for i in INDICES}):
                        part["+".join(i.upper() for i in INDICES if i in ep)] += 1
                        if "eddi" in ep and "spi" in ep:
                            d_es.append(ep["eddi"][0] - ep["spi"][0])
                            if not (ep["eddi"][2] or ep["spi"][2]):
                                e_es.append(ep["eddi"][1] - ep["spi"][1])
                        if "spei" in ep and "spi" in ep:
                            d_ps.append(ep["spei"][0] - ep["spi"][0])
                        if "eddi" in ep and "spei" in ep:
                            d_ep.append(ep["eddi"][0] - ep["spei"][0])
                        if len(ep) == 3:
                            n3[u] += 1
                            s0 = min(v[0] for v in ep.values())
                            first["+".join(i.upper() for i in INDICES if ep[i][0] == s0)] += 1
                n_ep = sum(part.values())
                print(f"  {side} episodes: {n_ep:,}; events SPI {int((EV['spi']['side'] == scode).sum()):,}, SPEI {int((EV['spei']['side'] == scode).sum()):,}, "
                      f"EDDI {int((EV['eddi']['side'] == scode).sum()):,}")
                print("    indices taking part: " + ", ".join(f"{k} {v / max(n_ep, 1):.0%}" for k, v in part.most_common()))
                n_all = sum(first.values())
                print(f"    all three take part in {n_all:,}; started first: " + ", ".join(f"{k} {v / max(n_all, 1):.0%}" for k, v in first.most_common()))
                if n_units > 1:
                    print(f"    all-three episodes per unit: median {np.median(n3[has]):.0f}, p10 {np.percentile(n3[has], 10):.0f}, p90 {np.percentile(n3[has], 90):.0f}")
                print(diff_line("EDDI start minus SPI start ", d_es))
                print(diff_line("SPEI start minus SPI start ", d_ps))
                print(diff_line("EDDI start minus SPEI start", d_ep))
                print(diff_line("EDDI end minus SPI end     ", e_es))
            print()


if __name__ == "__main__":
    main()
