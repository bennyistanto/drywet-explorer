"""Step 1 arithmetic on a grid small enough to work by hand.

Four cells in use (grid cells 0, 1, 2, 4; cell 3 is sea). Areas 10, 20, 30, 40 km2.
Unit 1 touches cells 0 and 1. Unit 2 touches cells 1, 2 and 4, so cell 1 is shared.
Unit 3 touches only the sea cell. Unit 4 has no row at all.
"""
import numpy as np

from pipeline import conventions as K
from pipeline.step1_classes import encode, side_share, unit_stats, weights_matrix

AREA = np.array([10.0, 20.0, 30.0, 999.0, 40.0])          # by grid cell; cell 3 is not land
POS = np.array([0, 1, 2, -1, 3])                           # position among cells in use
CELL = np.array([0, 1, 1, 2, 4, 3])
UNIT = np.array([1, 1, 2, 2, 2, 3])
SUBCELLS = np.array([64, 0, 3, 64, 1, 64])                 # must make no difference at all


def W():
    return weights_matrix(CELL, UNIT, POS, AREA, n_units=4)


def test_all_touched_gives_every_land_row_the_full_cell_area():
    w = W().toarray()
    assert w.shape == (4, 4)
    assert w[0].tolist() == [10.0, 20.0, 0.0, 0.0]
    assert w[1].tolist() == [0.0, 20.0, 30.0, 40.0]        # the shared cell counts fully in both units
    assert w[2].tolist() == [0.0, 0.0, 0.0, 0.0]           # touches only sea
    assert w[3].tolist() == [0.0, 0.0, 0.0, 0.0]           # no row, but it keeps its place on the axis


def test_coverage_fraction_is_not_a_weight():
    # a cell touched with 0 of 64 sub-cells inside still weighs its whole area
    assert W()[0, 1] == 20.0 and SUBCELLS[1] == 0


def test_shares_mean_and_missing():
    #            cell: 0     1     2     4
    v = np.array([[-2.5, -1.2, 0.3, 1.6],                  # month 0
                  [np.nan, -1.0, np.nan, 2.0],             # month 1: cells 0 and 2 have no value
                  [np.nan, np.nan, np.nan, np.nan]])       # month 2: nothing
    cls = K.classify_spi(v)
    codes = [1, 2, 3, 4, 5, 6, 7]
    area, valid, mean = unit_stats(cls, v, W(), codes)
    # unit 1, month 0: cell 0 (10 km2) extremely dry, cell 1 (20 km2) moderately dry
    assert np.allclose(area[0, 0], [10, 0, 20, 0, 0, 0, 0]) and valid[0, 0] == 30
    assert np.isclose(mean[0, 0], (10 * -2.5 + 20 * -1.2) / 30)
    # unit 2, month 0: cell 1 moderately dry (20), cell 2 near normal (30), cell 4 very wet (40)
    assert np.allclose(area[0, 1], [0, 0, 20, 30, 0, 40, 0]) and valid[0, 1] == 90
    assert np.isclose(mean[0, 1], (20 * -1.2 + 30 * 0.3 + 40 * 1.6) / 90)
    # month 1: missing cells leave both the numerator and the denominator
    assert valid[1, 0] == 20 and np.allclose(area[1, 0], [0, 0, 20, 0, 0, 0, 0]) and np.isclose(mean[1, 0], -1.0)
    assert valid[1, 1] == 60 and np.isclose(mean[1, 1], (20 * -1.0 + 40 * 2.0) / 60)
    # no valued cell: no value, never zero or normal
    assert valid[2, 0] == 0 and np.isnan(mean[2, 0])
    assert valid[0, 2] == 0 and np.isnan(mean[0, 2]) and valid[0, 3] == 0


def test_encode_rounds_once_and_marks_missing_per_level():
    v = np.array([[-2.5, -1.2, 0.3, 1.6], [np.nan] * 4])
    cls = K.classify_spi(v)
    area, valid, mean = unit_stats(cls, v, W(), [1, 2, 3, 4, 5, 6, 7])
    total = np.asarray(W().sum(axis=1)).ravel()
    for level in (1, 3):
        E = K.SHARE_ENCODING[level]
        s, m, vf = encode(area, valid, mean, total, level)
        assert s.dtype == np.dtype(E["share_dtype"])
        assert s[0, 0].tolist() == [round(E["share_scale"] / 3), 0, round(2 * E["share_scale"] / 3), 0, 0, 0, 0]
        assert m[0, 0] == round(((10 * -2.5 + 20 * -1.2) / 30) * E["mean_scale"])
        assert (s[1] == E["share_missing"]).all() and (m[1] == K.MEAN_MISSING).all() and (vf[1] == 0).all()
        assert (s[0, 3] == E["share_missing"]).all() and vf[0, 0] == 10000


def test_mean_is_rounded_from_float64_not_float32():
    # 0.0005 above a storage step in float64, but float32 would land on the step below
    target = 1.2345000001
    v = np.array([[target, target, target, target]])
    area, valid, mean = unit_stats(K.classify_spi(v), v, W(), [1, 2, 3, 4, 5, 6, 7])
    _, m, _ = encode(area, valid, mean, np.asarray(W().sum(axis=1)).ravel(), 1)
    assert m[0, 0] == round(target * 1000) == 1235


def test_side_share_is_unrounded_and_never_above_one():
    rng = np.random.default_rng(3)
    v = rng.normal(0, 1.2, size=(200, 4))
    cls = K.classify_spi(v)
    scheme = K.class_scheme("spi")
    area, valid, _ = unit_stats(cls, v, W(), [c for c, _, _ in scheme])
    dry, wet = side_share(area, valid, scheme, "dry"), side_share(area, valid, scheme, "wet")
    ok = valid > 0
    assert np.nanmax(dry) <= 1.0 and np.nanmax(wet) <= 1.0
    assert np.all(dry[ok] + wet[ok] <= 1.0 + 1e-12)
    assert np.isnan(dry[:, 2]).all()                        # the unit with no land has no share
    # unit 1, a month where both cells are dry: the dry side is all of it
    v2 = np.array([[-1.5, -1.0, 0.0, 0.0]])
    a2, val2, _ = unit_stats(K.classify_spi(v2), v2, W(), [c for c, _, _ in scheme])
    assert side_share(a2, val2, scheme, "dry")[0, 0] == 1.0 and side_share(a2, val2, scheme, "wet")[0, 0] == 0.0


def test_encode_side_rounds_the_total_once_and_marks_missing():
    from pipeline.step1_classes import encode_side
    # thirds: three classes of 1/3 each round to 67 + 67 + 67 = 201 of 200 if added after rounding
    dry = np.array([[1.0, 1 / 3, np.nan]])
    wet = np.array([[0.0, 2 / 3, np.nan]])
    for level in (1, 3):
        E = K.SHARE_ENCODING[level]
        s = encode_side(dry, wet, level)
        assert s.shape == (1, 3, 2) and s.dtype == np.dtype(E["share_dtype"])
        assert s[0, 0].tolist() == [E["share_scale"], 0]                       # never above the scale
        assert s[0, 1].tolist() == [round(E["share_scale"] / 3), round(2 * E["share_scale"] / 3)]
        assert s[0, 2].tolist() == [E["share_missing"], E["share_missing"]]


def test_side_uses_the_scheme_not_the_code_order():
    # EDDI: code 1 is the LOW demand end. A cell in ED2 (stored 8, code 9) is on the dry side.
    attrs = dict(flag_values=list(range(11)), flag_meanings="EW4 EW3 EW2 EW1 EW0 Normal ED0 ED1 ED2 ED3 ED4")
    scheme = K.class_scheme("eddi", attrs)
    cat = np.array([[8.0, 8.0, 1.0, 1.0]])                 # cells 0, 1 in ED2; cells 2, 4 in EW3
    cls = K.classify_eddi_cat(cat)
    area, valid, _ = unit_stats(cls, np.array([[1.4, 1.4, -1.6, -1.6]]), W(), [c for c, _, _ in scheme])
    assert side_share(area, valid, scheme, "dry")[0, 0] == 1.0
    assert np.isclose(side_share(area, valid, scheme, "wet")[0, 1], 70 / 90)
