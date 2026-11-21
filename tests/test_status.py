"""pipeline.status against the event scan and hand-built series."""
import numpy as np

from pipeline import status as S
from pipeline.events import events_reference, scan_events


def test_running_matches_the_event_scan():
    rng = np.random.default_rng(5)
    d = np.cumsum(rng.normal(scale=0.5, size=(300, 40)), axis=0)
    d -= d.mean(axis=0)
    d[rng.random(d.shape) < 0.01] = np.nan
    run = S.running(d)
    want = np.zeros(d.shape, np.int16)
    ev = scan_events(d)
    for s, a, b in zip(ev["series"], ev["start"], ev["end"]):
        want[a: b + 1, s] = np.arange(1, b - a + 2)
    assert np.array_equal(run, want)
    for s in range(5):                                     # and against the plain per-series reference
        ref = np.zeros(300, np.int16)
        for a, b, _ in events_reference(d[:, s]):
            ref[a: b + 1] = np.arange(1, b - a + 2)
        assert np.array_equal(run[:, s], ref)


def codes(values):
    d = np.array(values, dtype=float)[:, None]
    dd, dw = S.running(d), S.running(-d)
    return S.duration_code(dd, dw, np.isfinite(d))[:, 0].tolist(), S.status_code(d, dd, dw)[:, 0].tolist()


def test_states_and_bins_by_hand():
    #        none  new  new  deep  persist ease  ease  ended none
    series = [0.2, 1.2, 1.1, 1.6, 1.6, 0.4, 0.0, -0.3, -0.2]
    how, st = codes(series)
    assert st == [1, 2, 2, 3, 4, 5, 5, 6, 1]
    assert how == [1, 2, 2, 3, 3, 3, 4, 1, 1]              # months 1, 2: first bin; months 3, 4, 5: second; month 6: third
    # the same on the wet side
    how_w, st_w = codes([-v for v in series])
    assert st_w == [1, 7, 7, 8, 9, 10, 10, 11, 1]
    assert how_w == [1, 7, 7, 8, 8, 8, 9, 1, 1]


def test_no_value_and_a_switch_of_side():
    how, st = codes([1.5, np.nan, 1.5, -1.5, 0.5])
    assert st[1] == 0 and how[1] == 0                      # no value: no code, and the event has ended
    assert st[2] == 2                                      # a new dry event after the gap
    assert st[3] == 7                                      # dry ends as wet begins: the running event is shown
    assert st[4] == 11                                     # the wet event ended (index crossed zero)
    assert how[3] == 7


def test_combined_code_round_trip():
    rng = np.random.default_rng(6)
    d = np.cumsum(rng.normal(scale=0.5, size=(400, 30)), axis=0)
    d -= d.mean(axis=0)
    d[rng.random(d.shape) < 0.01] = np.nan
    dd, dw = S.running(d), S.running(-d)
    how, st = S.duration_code(dd, dw, np.isfinite(d)), S.status_code(d, dd, dw)
    code = S.combined_code(st, how)
    assert code.max() <= 51 and len(np.unique(st)) == 12
    st2, how2 = S.decode_combined(code)
    assert np.array_equal(st2, st) and np.array_equal(how2, how)


def test_long_durations_reach_the_last_bin():
    how, st = codes([1.5] * 30)
    assert how[0] == 2 and how[2] == 3 and how[5] == 4 and how[11] == 5 and how[23] == 6 and how[29] == 6
    assert st[0] == 2 and st[2] == 4                       # flat at the onset level: persisting, not deepening
