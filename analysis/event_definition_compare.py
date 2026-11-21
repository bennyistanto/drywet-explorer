"""How much do drought-event statistics depend on the event definition?

Three definitions, applied to TerraClimate SPI at 1, 3, 6, 12 months over
Indonesian cells, 1950-01..2025-12. Read-only on inputs. Prints every number.

  T   threshold run, as precip-index runtheory.identify_runs:
      maximal run of months with SPI < -1.0 (strict).
      magnitude = sum(-1.0 - SPI)
  Wa  WMO-No. 1090 section 3 (McKee 1993): maximal run of months with SPI < 0
      that reaches -1.0 or less at least once. The whole excursion counts.
      magnitude = sum(-SPI)
  Wb  WMO-No. 1090 section 6.1: starts at the first month with SPI <= -1.0,
      ends when SPI becomes positive. Same as Wa minus the lead-in months.
      magnitude = sum(-SPI) from the start month

A missing value ends any run. A run still open in the last month is counted
and reported separately as open.

Run: python analysis/event_definition_compare.py
"""
import sys
import time

import geopandas as gpd
import numpy as np
import xarray as xr
from rasterio import features
from rasterio.transform import from_origin

W, E, S, N = 94.5, 141.5, -11.5, 6.5
THR = -1.0
SCALES = (1, 3, 6, 12)
SPI = r"G:\temp\terraclimate\spi\wld_cli_terraclimate_spi_gamma_{n}_month.nc"
ADM1 = r"E:\temp\idn-bnd\idn_bnd_adm1.shp"
RUNTHEORY = r"C:\Users\benny\OneDrive\Documents\Github\precip-index\src"
CASE = (108.30, -6.45)  # a cell in Indramayu, the case cell used in the nino series


def load_window(n):
    ds = xr.open_dataset(SPI.format(n=n))
    lat = ds["lat"].values
    lon = ds["lon"].values
    li = np.where((lat >= S) & (lat <= N))[0]
    lo = np.where((lon >= W) & (lon <= E))[0]
    sub = ds[f"spi_gamma_{n}_month"].isel(lat=slice(li.min(), li.max() + 1), lon=slice(lo.min(), lo.max() + 1))
    out = (sub.values.astype(np.float32), sub["lat"].values, sub["lon"].values, ds["time"].values)
    ds.close()
    return out


class Acc:
    """Pooled event statistics for one definition."""

    def __init__(self, nt, ncell):
        self.hist = np.zeros(nt + 1, np.int64)
        self.mag = 0.0
        self.n = 0
        self.per_cell = np.zeros(ncell, np.int32)
        self.longest = np.zeros(ncell, np.int32)
        self.open = 0

    def add(self, sel, dur, mag):
        d = dur[sel]
        if d.size == 0:
            return
        self.hist += np.bincount(d, minlength=self.hist.size)
        self.mag += float(mag[sel].sum())
        self.n += int(d.size)
        self.per_cell[sel] += 1
        self.longest[sel] = np.maximum(self.longest[sel], d)

    def pctl(self, q):
        c = np.cumsum(self.hist)
        return int(np.searchsorted(c, q / 100 * c[-1]))

    def months(self):
        return int((self.hist * np.arange(self.hist.size)).sum())


def scan(x):
    """Streaming scan over time. x is (time, cell)."""
    nt, nc = x.shape
    accT, accA, accB = Acc(nt, nc), Acc(nt, nc), Acc(nt, nc)
    t_len = np.zeros(nc, np.int32)
    t_mag = np.zeros(nc, np.float64)
    n_len = np.zeros(nc, np.int32)   # negative excursion
    n_mag = np.zeros(nc, np.float64)
    h_len = np.zeros(nc, np.int32)   # since first month <= THR within the excursion
    h_mag = np.zeros(nc, np.float64)
    hit = np.zeros(nc, bool)
    for t in range(nt + 1):
        if t < nt:
            v = x[t]
            fin = np.isfinite(v)
            v0 = np.where(fin, v, 0.0).astype(np.float64)
            below = fin & (v < THR)
            neg = fin & (v < 0)
            reach = fin & (v <= THR)
        else:  # flush whatever is open after the last month
            below = np.zeros(nc, bool)
            neg = np.zeros(nc, bool)
            reach = neg
            v0 = np.zeros(nc)
        # threshold run
        endT = (~below) & (t_len > 0)
        accT.add(endT, t_len, t_mag)
        if t == nt:
            accT.open = int(endT.sum())
        t_len[endT] = 0
        t_mag[endT] = 0
        t_len[below] += 1
        t_mag[below] += THR - v0[below]
        # negative excursion
        endN = (~neg) & (n_len > 0)
        fire = endN & hit
        accA.add(fire, n_len, n_mag)
        accB.add(fire, h_len, h_mag)
        if t == nt:
            accA.open = accB.open = int(fire.sum())
        for a in (n_len, h_len):
            a[endN] = 0
        for a in (n_mag, h_mag):
            a[endN] = 0
        hit[endN] = False
        n_len[neg] += 1
        n_mag[neg] -= v0[neg]
        hit |= reach
        on = neg & hit
        h_len[on] += 1
        h_mag[on] -= v0[on]
    return accT, accA, accB


def events_1d(v, kind):
    """Plain per-series reference, used for the case cell printout."""
    out = []
    i = 0
    n = len(v)
    while i < n:
        inrun = np.isfinite(v[i]) and (v[i] < THR if kind == "T" else v[i] < 0)
        if not inrun:
            i += 1
            continue
        j = i
        while j < n and np.isfinite(v[j]) and (v[j] < THR if kind == "T" else v[j] < 0):
            j += 1
        seg = v[i:j]
        if kind == "T":
            out.append((i, j - 1))
        elif (seg <= THR).any():
            k = i + int(np.argmax(seg <= THR)) if kind == "Wb" else i
            out.append((k, j - 1))
        i = j
    return out


t0 = time.time()
first = True
for n in SCALES:
    arr, slat, slon, tt = load_window(n)
    if first:
        dx = abs(float(slon[1] - slon[0]))
        dy = abs(float(slat[1] - slat[0]))
        tr = from_origin(float(slon[0]) - dx / 2, float(slat[0]) + dy / 2, dx, dy)
        g = gpd.read_file(ADM1, engine="pyogrio")
        grid = features.rasterize(zip(g.geometry, range(1, len(g) + 1)), out_shape=(len(slat), len(slon)),
                                  transform=tr, fill=0, dtype="int32")
        mask = (grid > 0) & np.isfinite(arr).any(axis=0)
        iy = int(np.argmin(np.abs(slat - CASE[1])))
        ix = int(np.argmin(np.abs(slon - CASE[0])))
        ym = [str(x)[:7] for x in tt]
        print(f"Indonesian land cells: {int(mask.sum()):,}; months {ym[0]} to {ym[-1]}")
        first = False
    case = arr[:, iy, ix].copy()
    x = arr[:, mask]
    del arr
    nfin = int(np.isfinite(x).sum())
    accT, accA, accB = scan(x)
    yrs = len(tt) / 12

    print(f"\n=== SPI-{n}  [{time.time() - t0:.0f}s]  finite cell-months {nfin:,} ===")
    print(f"  exactly -1.0 values (in WMO, out of strict run): {int((x == THR).sum()):,}")
    print("  def   events/cell  per decade   mean dur  median  p90   max   mean magnitude  % of months in event  open at end")
    for name, a in (("T ", accT), ("Wa", accA), ("Wb", accB)):
        dmean = a.months() / a.n
        print(f"  {name}    {a.per_cell.mean():8.1f}   {a.per_cell.mean() / yrs * 10:8.2f}   {dmean:8.2f}  {a.pctl(50):5d}  "
              f"{a.pctl(90):4d}  {int(np.nonzero(a.hist)[0].max()):4d}   {a.mag / a.n:10.2f}   {100 * a.months() / nfin:12.2f}%   "
              f"{a.open:,} cells ({100 * a.open / x.shape[1]:.1f}%)")
    print(f"  threshold runs per WMO event: {accT.n / accA.n:.2f}")
    print(f"  mean duration ratio Wa/T {accA.months() / accA.n / (accT.months() / accT.n):.2f}, "
          f"Wb/T {accB.months() / accB.n / (accT.months() / accT.n):.2f}")
    print(f"  longest event per cell, median across cells: T {int(np.median(accT.longest))}, "
          f"Wa {int(np.median(accA.longest))}, Wb {int(np.median(accB.longest))} months")
    for k in (1, 2):
        print(f"  share of events lasting {k} month{'s' if k > 1 else ''} or less: "
              f"T {100 * accT.hist[:k + 1].sum() / accT.n:.1f}%, Wa {100 * accA.hist[:k + 1].sum() / accA.n:.1f}%, "
              f"Wb {100 * accB.hist[:k + 1].sum() / accB.n:.1f}%")
    n3 = accT.hist[3:].sum()
    print(f"  T with min_duration=3 keeps {100 * n3 / accT.n:.1f}% of threshold runs "
          f"({n3 / x.shape[1]:.1f} per cell)")

    # reference check of T against precip-index on sampled cells
    try:
        if RUNTHEORY not in sys.path:
            sys.path.insert(0, RUNTHEORY)
        from runtheory import identify_events
        rng = np.random.default_rng(20261120)
        bad = 0
        idx = rng.choice(x.shape[1], 30, replace=False)
        for c in idx:
            ev = identify_events(x[:, c].astype(float), threshold=THR, min_duration=1)
            aT, _, _ = scan(x[:, [c]])
            dsum = float(ev["duration"].sum()) if len(ev) else 0.0
            msum = float(ev["magnitude"].sum()) if len(ev) else 0.0
            if len(ev) != aT.n or abs(dsum - aT.months()) > 0 or abs(msum - aT.mag) > 1e-3:
                bad += 1
                if bad <= 2:
                    print(f"    mismatch cell {c}: ref n={len(ev)} dur={dsum} mag={msum:.3f} | scan n={aT.n} dur={aT.months()} mag={aT.mag:.3f}")
        print(f"  reference check, T against precip-index identify_events on 30 cells (seed 20261120): {30 - bad} agree, {bad} differ")
    except Exception as e:  # noqa: BLE001
        print("  reference check not run:", repr(e)[:200])

    # case cell, events touching 1997-1998
    print(f"  case cell lon {slon[ix]:.3f} lat {slat[iy]:.3f}, events touching 1997-1998:")
    for kind in ("T", "Wa", "Wb"):
        evs = [(a, b) for a, b in events_1d(case, kind) if ym[b] >= "1997-01" and ym[a] <= "1998-12"]
        txt = "; ".join(f"{ym[a]}..{ym[b]} ({b - a + 1} mo)" for a, b in evs) or "none"
        print(f"    {kind:2s}: {txt}")

print(f"\ndone in {time.time() - t0:.0f}s")
