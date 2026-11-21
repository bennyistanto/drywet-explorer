"""pipeline.hotspot against brute-force versions and hand-built cases."""
import itertools

import numpy as np

from pipeline import hotspot as H


def brute_gi(cube):
    """Gi* straight from the formula, one bin at a time."""
    body = cube[H.TIME_STEP:]
    vals = body[np.isfinite(body)]
    n, xbar = len(vals), vals.mean()
    S = np.sqrt((vals ** 2).mean() - xbar ** 2)
    T, ny, nx = body.shape
    out = np.full(body.shape, np.nan)
    for t, i, j in itertools.product(range(T), range(ny), range(nx)):
        if not np.isfinite(body[t, i, j]):
            continue
        nb = cube[t: t + H.TIME_STEP + 1, max(i - 1, 0): i + 2, max(j - 1, 0): j + 2]   # this step and one back
        nb = nb[np.isfinite(nb)]
        w = len(nb)
        out[t, i, j] = (nb.sum() - xbar * w) / (S * np.sqrt((n * w - w * w) / (n - 1)))
    return out


def test_gi_star_matches_the_formula():
    rng = np.random.default_rng(1)
    cube = rng.normal(size=(7, 6, 8))
    cube[:, 0, 0] = np.nan            # a cell with no value
    cube[:, 3, 4] = np.nan
    z = H.gi_star(cube, "cube")
    assert z.shape == (6, 6, 8)
    np.testing.assert_allclose(z, brute_gi(cube), rtol=1e-9, atol=1e-9, equal_nan=True)
    # against climatology: the neighbourhood sum over the root of the neighbourhood count
    zc = H.gi_star(cube, "climatology")
    nb = cube[2:4, 1:4, 4:7]
    nb = nb[np.isfinite(nb)]
    assert abs(zc[2, 2, 5] - nb.sum() / np.sqrt(len(nb))) < 1e-9
    assert np.isnan(zc[:, 0, 0]).all()


def test_gi_star_neighbourhood_looks_back_not_forward():
    cube = np.zeros((4, 5, 5))
    cube[1, 2, 2] = 10.0              # body index 0
    z = H.gi_star(cube, "cube")
    assert z[1, 2, 2] > z[2, 2, 2]    # the step after sees it, two steps after does not
    cube2 = np.zeros((4, 5, 5))
    cube2[3, 2, 2] = 10.0             # body index 2: must not raise the bin before it
    z2 = H.gi_star(cube2, "cube")
    assert z2[1, 2, 2] < 0 and z2[2, 2, 2] > 0


def test_step4_sums_give_the_same_gi_star():
    """Step 4 builds the neighbourhood sums once for the whole record and slices a window out of them.
    A window's z-scores must equal Gi* run on that window's cube alone."""
    import xarray as xr
    from pipeline.step4_hotspot import neighbourhood_sums

    rng = np.random.default_rng(3)
    full = rng.normal(size=(20, 6, 7))
    full[:, 0, :] = np.nan                                     # a row of sea
    drawn = np.flatnonzero(np.isfinite(full[0]).ravel())
    v, sx, sw = neighbourhood_sums(xr.DataArray(full, dims=("time", "lat", "lon")), 1, drawn, (6, 7))
    W, t = 8, 15
    w = slice(t - W + 1, t + 1)
    for ref in ("cube", "climatology"):
        z = H.z_from_sums(sx[w], sw[w], v[w], ref)
        want = H.gi_star(full[t - W: t + 1], ref).reshape(W, -1)[:, drawn]
        np.testing.assert_allclose(z, want, rtol=1e-5, atol=1e-5)


def test_fdr_threshold_is_benjamini_hochberg():
    p = np.array([0.001, 0.008, 0.039, 0.041, 0.042, 0.06, 0.074, 0.205, 0.212, 0.216])
    # at alpha 0.10 with m = 10 the limits are 0.01, 0.02, ..., 0.10. Rank 7 fails (0.074 > 0.07);
    # rank 6 passes (0.06 <= 0.06) and is the last one that does
    assert H.fdr_threshold(p, 0.10) == 0.06
    assert H.fdr_threshold(np.array([0.5, 0.9]), 0.10) == 0.0


def test_mann_kendall_against_pair_count():
    rng = np.random.default_rng(2)
    a = rng.normal(size=(15, 4))
    z = H.mann_kendall_z(a)
    T = 15
    for k in range(4):
        s = sum(np.sign(a[j, k] - a[i, k]) for i in range(T) for j in range(i + 1, T))
        sd = np.sqrt(T * (T - 1) * (2 * T + 5) / 18)
        want = (s - 1) / sd if s > 0 else (s + 1) / sd if s < 0 else 0.0
        assert abs(z[k] - want) < 1e-12
    assert H.mann_kendall_z(np.arange(12.0)[:, None])[0] > H.Z90


def series(text):
    """'..HH.C' -> (hot, cold) columns of one cell."""
    hot = np.array([c == "H" for c in text])[:, None]
    cold = np.array([c == "C" for c in text])[:, None]
    return hot, cold


def cat(text, trend=0):
    hot, cold = series(text)
    return int(H.one_side(hot, cold, np.array([trend]))[0])


def test_categories_hot_side():
    assert cat("...........H") == 1                    # new: hot in the final step only
    assert cat("........HHHH") == 2                    # consecutive: one final run, never hot before
    assert cat(".H......HHHH") == 6                    # hot before the run, never cold: sporadic
    assert cat(".C......HHHH") == 2                    # CHOICE: consecutive wins over oscillating
    assert cat(".C..H...HHHH") == 7                    # oscillating: earlier cold, on and off
    assert cat("HHHHHHHHHHHH", 0) == 4                 # persistent
    assert cat("HHHHHHHHHHHH", 1) == 3                 # intensifying
    assert cat("HHHHHHHHHHHH", -1) == 5                # diminishing
    assert cat(".HHHHHHHHHHH", 0) == 4                 # 11 of 12 is over 90%
    assert cat("..HHHHHHHHHH", 0) == 2                 # 10 of 12 is under 90%: a single final run
    assert cat("HHHHHHHHHHH.") == 8                    # historical: 90% hot, final step not
    assert cat("HHHH........") == 0
    assert cat("............") == 0


def test_classify_sides_and_missing():
    T = 12
    z = np.zeros((T, 1, 4))
    z[:, 0, 0] = 5.0                                   # hot throughout, flat: persistent hot
    z[:, 0, 1] = -5.0                                  # persistent cold
    z[-1, 0, 2] = 5.0                                  # new hot
    z[:, 0, 3] = np.nan
    c = H.classify(z, fdr=False)
    assert c[0].tolist() == [4, -4, 1, -128]
    z[:, 0, 0] = np.linspace(3, 9, T)                  # rising: intensifying
    z[:, 0, 1] = np.linspace(-3, -9, T)                # cold deepening: intensifying cold
    assert H.classify(z, fdr=False)[0, :2].tolist() == [3, -3]
