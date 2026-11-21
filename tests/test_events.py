"""The event rule (WMO-No. 1090 section 6.1) on series small enough to work by hand."""
import numpy as np

from pipeline import conventions as K
from pipeline.events import events_reference, scan_events


def run(spi, side="dry", index="spi", **kw):
    """Events on one index series, with the direction applied the way step 2 applies it."""
    v = np.array(spi, dtype=float)[:, None]
    d = v * K.DRY_SIGN[index] * (1 if side == "dry" else -1)
    return scan_events(d, **kw)


def spans(e):
    return list(zip(e["start"].tolist(), e["end"].tolist()))


def test_starts_at_first_month_at_or_below_minus_one_not_at_the_first_negative_month():
    e = run([0.5, -0.4, -0.9, -1.0, -1.6, -0.3, 0.2, 0.4])
    assert spans(e) == [(3, 5)]                      # the lead-in at positions 1, 2 is not part of it
    assert e["duration"].tolist() == [3]
    assert np.isclose(e["magnitude"][0], 1.0 + 1.6 + 0.3)
    assert np.isclose(e["peak"][0], 1.6) and e["peak_t"].tolist() == [4]
    assert e["n_onset"].tolist() == [2]              # two of its three months are at or below -1.0


def test_exactly_minus_one_starts_and_exactly_zero_continues():
    e = run([-1.0, 0.0, -0.2, 0.01, -1.0])
    assert spans(e) == [(0, 2), (4, 4)]
    assert e["open"].tolist() == [False, True]


def test_does_not_fragment_a_drought_that_dips_above_the_threshold():
    e = run([-1.2, -0.5, -1.3, -0.1, -1.1, 0.3])
    assert spans(e) == [(0, 4)]                      # a threshold run would give three events


def test_never_reaching_minus_one_is_no_event():
    assert len(run([-0.9, -0.99, -0.5, 0.2])["start"]) == 0


def test_event_running_in_the_last_month_is_open():
    e = run([0.1, -1.4, -0.6])
    assert spans(e) == [(1, 2)] and e["open"].tolist() == [True]


def test_missing_month_ends_an_event_and_is_marked():
    e = run([-1.5, -0.5, np.nan, -0.5, -1.2, 0.5])
    assert spans(e) == [(0, 1), (4, 4)]
    assert e["ended_by_missing"].tolist() == [True, False]


def test_warm_up_nans_produce_nothing():
    assert spans(run([np.nan, np.nan, -1.1, 0.4])) == [(2, 2)]


def test_wet_events_mirror_dry_events():
    e = run([0.2, 1.0, 0.3, 0.0, -0.1, 1.7], side="wet")
    assert spans(e) == [(1, 3), (5, 5)]


def test_eddi_dry_is_positive():
    v = [0.1, 1.2, 0.4, -0.2, -1.3, -0.1, 0.3]
    assert spans(run(v, side="dry", index="eddi")) == [(1, 2)]
    assert spans(run(v, side="wet", index="eddi")) == [(4, 5)]


def test_extra_tracks_its_maximum_during_the_event():
    v = np.array([-1.2, -0.5, -1.5, 0.4])[:, None]
    share = np.array([0.3, 0.1, 0.8, 0.9])[:, None]
    e = scan_events(-v, extra=share)
    assert np.isclose(e["extra_max"][0], 0.8) and e["extra_t"].tolist() == [2]


def test_second_event_carries_nothing_over_from_the_first():
    # first event: long, deep, high share. second: short, shallow, low share.
    v = np.array([-2.9, -2.5, -1.8, -1.2, 0.5, 0.3, -1.1, -0.2, 0.4])[:, None]
    share = np.array([1.0, 0.9, 0.8, 0.7, 0.0, 0.0, 0.3, 0.1, 0.0])[:, None]
    e = scan_events(-v, extra=share)
    assert spans(e) == [(0, 3), (6, 7)]
    assert e["duration"].tolist() == [4, 2]
    assert np.allclose(e["magnitude"], [2.9 + 2.5 + 1.8 + 1.2, 1.1 + 0.2])
    assert np.allclose(e["peak"], [2.9, 1.1]) and e["peak_t"].tolist() == [0, 6]
    assert e["n_onset"].tolist() == [4, 1]
    assert np.allclose(e["extra_max"], [1.0, 0.3]) and e["extra_t"].tolist() == [0, 6]


def test_second_event_with_no_extra_value_does_not_inherit_one():
    v = np.array([-1.5, 0.5, -1.5, 0.5])[:, None]
    share = np.array([0.8, 0.0, np.nan, 0.0])[:, None]
    e = scan_events(-v, extra=share)
    assert np.isclose(e["extra_max"][0], 0.8) and np.isnan(e["extra_max"][1]) and e["extra_t"].tolist() == [0, -1]


def test_all_fields_equal_a_plain_reference_on_random_series():
    rng = np.random.default_rng(11)
    d = rng.normal(0, 1, size=(300, 40))
    for j in range(40):
        d[1:, j] = 0.6 * d[:-1, j] + 0.8 * d[1:, j]
    d[rng.random(d.shape) < 0.01] = np.nan
    x = rng.random(d.shape)
    e = scan_events(d, extra=x)
    n = 0
    for j in range(40):
        m = e["series"] == j
        for i, (s, t, is_open) in enumerate(events_reference(d[:, j])):
            seg, xs = d[s:t + 1, j], x[s:t + 1, j]
            assert e["duration"][m][i] == t - s + 1
            assert np.isclose(e["magnitude"][m][i], seg.sum())
            assert np.isclose(e["peak"][m][i], seg.max()) and e["peak_t"][m][i] == s + int(np.argmax(seg))
            assert e["n_onset"][m][i] == int((seg >= 1.0).sum())
            assert np.isclose(e["extra_max"][m][i], xs.max()) and e["extra_t"][m][i] == s + int(np.argmax(xs))
            n += 1
    assert n > 200


def test_vector_scan_equals_plain_reference_on_random_series():
    rng = np.random.default_rng(7)
    d = rng.normal(0, 1, size=(400, 60))
    for j in range(1, 60):                            # persistence, so events have length
        d[1:, j] = 0.7 * d[:-1, j] + 0.7 * d[1:, j]
    d[rng.random(d.shape) < 0.01] = np.nan
    d[rng.random(d.shape) < 0.01] = 0.0
    e = scan_events(d)
    for j in range(60):
        m = e["series"] == j
        got = list(zip(e["start"][m].tolist(), e["end"][m].tolist(), e["open"][m].tolist()))
        assert got == events_reference(d[:, j]), f"series {j}"
