"""Emerging hot spot analysis on a space-time cube of one index: Getis-Ord Gi* per bin, Mann-Kendall on
each cell's Gi* series, and the 17 pattern categories.

Source of the rules: Esri, "How Emerging Hot Spot Analysis works" and the tool reference,
  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/space-time-pattern-mining/learnmoreemerging.html
  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/space-time-pattern-mining/emerginghotspots.html
(read 2026-11-21).

What follows the pages:
  - a bin's neighbourhood is its spatial neighbours plus the same cells N time steps BACK (never forward);
    Neighborhood Time Step defaults to 1;
  - the global mean and standard deviation come from the entire cube (the default "Define Global Window");
  - a bin is a hot or cold spot from 90% confidence, and the bin class uses an FDR correction;
  - Mann-Kendall is run on each location's series of Gi* z-scores;
  - the category definitions, including the "90 percent of time-step intervals" conditions.

What the pages do NOT state, and is therefore a choice made here (each is marked CHOICE below):
  - the spatial neighbourhood for a raster: the 3 x 3 block of cells (contiguity, edges and corners);
  - the FDR procedure: Benjamini-Hochberg over every bin of the cube, at 0.10;
  - the trend level for Intensifying and Diminishing: 90% (|z| >= 1.645), no tie correction;
  - "90 percent of T bins" is n >= 0.9 * T, not rounded;
  - precedence where a cell meets two definitions: New and Consecutive first, then the 90% classes, then
    Oscillating, then Sporadic;
  - Persistent requires the final bin to be hot (otherwise the cell is Historical).

The value in the cube is the index with its sign turned so that POSITIVE IS DRY (conventions.DRY_SIGN), so
for all three indices a hot spot is a cluster of dry values (for EDDI, of high evaporative demand) and a
cold spot a cluster of wet values. This is a continuous standardised value, not a count: Gi* then tests
whether the neighbourhood mean is unusual against the whole cube.
"""
import numpy as np
from scipy.ndimage import uniform_filter
from scipy.stats import norm

Z90 = 1.6448536269514722
FDR_ALPHA = 0.10            # CHOICE
SPATIAL = 3                 # CHOICE: 3 x 3 cells
TIME_STEP = 1               # Esri default: the bin's own step and one step back
NINETY = 0.9
REFERENCE = "climatology"   # CHOICE (owner, 2026-11-21): "climatology" or "cube"; see z_from_sums

CATEGORIES = {
    0: "No pattern detected",
    1: "New hot spot", 2: "Consecutive hot spot", 3: "Intensifying hot spot", 4: "Persistent hot spot",
    5: "Diminishing hot spot", 6: "Sporadic hot spot", 7: "Oscillating hot spot", 8: "Historical hot spot",
    -1: "New cold spot", -2: "Consecutive cold spot", -3: "Intensifying cold spot", -4: "Persistent cold spot",
    -5: "Diminishing cold spot", -6: "Sporadic cold spot", -7: "Oscillating cold spot", -8: "Historical cold spot",
}


def local_sums(cube):
    """Sum of values and count of valid cells in each bin's space-time neighbourhood.

    cube: float [T + TIME_STEP, ny, nx], NaN where there is no value. Returns (sx, sw), each [T, ny, nx],
    for the last T bins: every one of them has its TIME_STEP earlier bins available.
    """
    ok = np.isfinite(cube)
    x = np.where(ok, cube, 0.0).astype(np.float64)
    k = SPATIAL * SPATIAL
    # mode="constant": cells beyond the window edge do not exist, so they add nothing
    s = uniform_filter(x, size=(1, SPATIAL, SPATIAL), mode="constant", cval=0.0) * k
    w = uniform_filter(ok.astype(np.float64), size=(1, SPATIAL, SPATIAL), mode="constant", cval=0.0) * k
    sx = s[TIME_STEP:].copy()
    sw = w[TIME_STEP:].copy()
    for back in range(1, TIME_STEP + 1):
        sx += s[TIME_STEP - back: len(s) - back]
        sw += w[TIME_STEP - back: len(w) - back]
    return sx, np.rint(sw)


def gi_star(cube, reference=None):
    """Gi* z-score of every bin of the last T steps.

    Getis and Ord (1995) with binary weights: z = (sum_j x_j - xbar * w) / (S * sqrt((n * w - w^2) / (n - 1))),
    where w is the number of valid bins in the neighbourhood and n the number of valid bins in the cube.
    See z_from_sums for what xbar and S are.
    """
    sx, sw = local_sums(cube)
    return z_from_sums(sx, sw, cube[TIME_STEP:], reference)


def z_from_sums(sx, sw, body, reference=None):
    """Gi* z from neighbourhood sums and counts, for the bins of `body` (any shape whose first axis is time).

    reference "cube": the mean and sd are those of `body`, the entire cube being analysed (Esri's default
        global window). Hot and cold are then relative to the average of the cube itself.
    reference "climatology": mean 0 and sd 1, which is what a standardised index has over its baseline by
        construction. z = sum / sqrt(w), the same statistic with the population taken as the baseline
        climate (the finite-population term (n w - w^2) / (n - 1) tends to w). Hot and cold are then
        relative to normal. This is a DEPARTURE from Esri's tool, made because the value is already an
        anomaly: against the cube's own mean, a near-normal place in a dry year came out as a cold spot.
    """
    reference = reference or REFERENCE
    ok = np.isfinite(body)
    if reference == "climatology":
        z = sx / np.sqrt(np.maximum(sw, 1.0))
        z[~ok] = np.nan
        return z
    assert reference == "cube", reference
    n = float(ok.sum())
    b = body[ok].astype(np.float64)
    xbar = float(b.mean())
    S = float(np.sqrt((b ** 2).mean() - xbar ** 2))
    den = S * np.sqrt(np.maximum((n * sw - sw ** 2) / (n - 1.0), 1e-30))
    z = (sx - xbar * sw) / den
    z[~ok] = np.nan
    return z


def fdr_threshold(p, alpha=FDR_ALPHA):
    """Benjamini-Hochberg: the largest p that is still significant, or 0.0 when none is."""
    p = np.sort(p[np.isfinite(p)])
    if not len(p):
        return 0.0
    passed = p <= alpha * np.arange(1, len(p) + 1) / len(p)
    return float(p[np.flatnonzero(passed)[-1]]) if passed.any() else 0.0


def significant(z, fdr=True):
    """(hot, cold) boolean arrays: significant at 90% confidence, with or without the FDR correction."""
    if fdr:
        p = 2.0 * norm.sf(np.abs(z))
        thr = fdr_threshold(p)
        sig = p <= thr if thr > 0 else np.zeros(z.shape, bool)
    else:
        sig = np.abs(z) >= Z90
    sig &= np.isfinite(z)
    return sig & (z > 0), sig & (z < 0)


def mann_kendall_z(a):
    """Mann-Kendall z of each series along axis 0 (no tie correction; Gi* z-scores are continuous)."""
    T = a.shape[0]
    s = np.zeros(a.shape[1:], np.float64)
    for i in range(T - 1):
        s += np.sign(a[i + 1:] - a[i]).sum(axis=0)
    sd = np.sqrt(T * (T - 1) * (2 * T + 5) / 18.0)
    return np.where(s > 0, (s - 1) / sd, np.where(s < 0, (s + 1) / sd, 0.0))


def final_run(flag):
    """Length of the uninterrupted run of True that ends at the last step (0 when the last step is False)."""
    run = np.zeros(flag.shape[1:], np.int32)
    alive = np.ones(flag.shape[1:], bool)
    for t in range(flag.shape[0] - 1, -1, -1):
        alive &= flag[t]
        run += alive
    return run


def one_side(own, other, trend):
    """Category 1..8 for one side. own, other: [T, ...] significance of this side and of the opposite one.
    trend: +1 where this side's clustering intensifies significantly, -1 where it weakens, 0 otherwise."""
    T = own.shape[0]
    n = own.sum(axis=0)
    last = own[-1]
    run = final_run(own)
    most = n >= NINETY * T
    cat = np.zeros(own.shape[1:], np.int8)
    # written from lowest precedence to highest, so a later line overrides an earlier one
    cat[last & ~most] = 6                                                # sporadic
    cat[last & ~most & other[:-1].any(axis=0)] = 7                       # oscillating
    cat[~last & most] = 8                                                # historical
    cat[last & most & (trend == 0)] = 4                                  # persistent
    cat[last & most & (trend > 0)] = 3                                   # intensifying
    cat[last & most & (trend < 0)] = 5                                   # diminishing
    cat[last & (run >= 2) & (n == run) & ~most] = 2                      # consecutive
    cat[last & (n == 1)] = 1                                             # new
    return cat


def classify(z, fdr=True):
    """Pattern category of every cell from its Gi* series z [T, ny, nx]: +1..+8 hot, -1..-8 cold, 0 none.
    Cells with no value in the final bin get -128."""
    valid = np.isfinite(z[-1])
    zc = z[:, valid]                                     # [T, cells with a value]: the work is done on these only
    hot, cold = significant(zc, fdr)
    mk = mann_kendall_z(np.where(np.isfinite(zc), zc, 0.0).astype(np.float32))
    up, down = mk >= Z90, mk <= -Z90
    h = one_side(hot, cold, up.astype(np.int8) - down.astype(np.int8))
    c = one_side(cold, hot, down.astype(np.int8) - up.astype(np.int8))
    cc = np.where(h > 0, h, -c).astype(np.int8)        # the final bin cannot be both hot and cold;
    both = (h == 8) & (c > 0)                            # only Historical (final bin not hot) can meet a cold class
    cc[both] = -c[both]
    cat = np.full(z.shape[1:], -128, np.int8)
    cat[valid] = cc
    return cat


def emerging(cube, fdr=True):
    """cube [T + TIME_STEP, ny, nx] of dry-signed index values, oldest first. Returns (category, z)."""
    z = gi_star(cube)
    return classify(z, fdr), z
