"""Step 2: flags on events and the per-unit summary, on series worked by hand."""
import numpy as np

from pipeline import conventions as K
from pipeline.step2_events import event_table, summarise

NT = K.N_MONTHS
EARLY_LAST = K.month_position("1969-12")


def series(n_units=1):
    return np.full((NT, n_units), 0.5)                     # quietly positive: no event on either side for SPI


def table(mean, index="spi", scale=1, majority=None, share=None):
    nu = mean.shape[1]
    sh = np.full(mean.shape, 0.25) if share is None else share
    return event_table(mean, sh, sh, index, scale, np.zeros(nu, bool) if majority is None else majority)


def rows(t, side=0, unit=1):
    m = (t["side"] == side) & (t["unit"] == unit)
    order = np.argsort(t["start"][m])
    return {k: v[m][order] for k, v in t.items()}


def test_direction_comes_from_the_index():
    m = series()
    m[100:103, 0] = -1.5
    assert len(rows(table(m, "spi"), side=0)["start"]) == 1 and len(rows(table(m, "spi"), side=1)["start"]) == 0
    # the same numbers as EDDI are low demand, not dry
    e = np.full((NT, 1), -0.5)
    e[100:103, 0] = 1.5
    assert rows(table(e, "eddi"), side=0)["start"].tolist() == [100]
    assert len(rows(table(m - 1.0, "eddi"), side=0)["start"]) == 0


def test_n_early_counts_months_inside_the_early_record():
    m = series()
    m[EARLY_LAST - 2:EARLY_LAST + 1, 0] = -1.5              # ends exactly on 1969-12
    m[EARLY_LAST + 1, 0] = 0.5
    m[EARLY_LAST + 2:EARLY_LAST + 5, 0] = -1.5              # starts after it
    m[300:310, 0] = -1.5
    r = rows(table(m))
    assert r["n_early"].tolist() == [3, 0, 0] and r["flagged"].tolist() == [True, False, False]
    m2 = series()
    m2[EARLY_LAST - 1:EARLY_LAST + 4, 0] = -1.5             # straddles: 2 months inside, 3 outside
    r2 = rows(table(m2))
    assert r2["n_early"].tolist() == [2] and r2["duration"].tolist() == [5] and r2["flagged"].tolist() == [True]
    m3 = series()
    m3[EARLY_LAST + 1:EARLY_LAST + 3, 0] = -1.5             # starts exactly on 1970-01
    assert rows(table(m3))["n_early"].tolist() == [0]


def test_step_flag_end_depends_on_the_scale_and_needs_a_majority_unit():
    for scale in (1, 3, 6, 12):
        last = K.step_1984_last_position(scale)
        m = series(2)
        m[last, :] = -1.5                                   # starts on the flag's last month
        m[last + 1, :] = 0.5
        m[last + 2, :] = -1.5                               # starts two months later
        t = table(m, scale=scale, majority=np.array([True, False]))
        assert rows(t, unit=1)["step_flagged"].tolist() == [True, False], scale
        assert rows(t, unit=2)["step_flagged"].tolist() == [False, False], scale
        assert rows(t, unit=1)["flagged"].tolist() == [True, False]
    # one month past the scale-1 end is still inside the scale-12 flag
    m = series()
    m[K.step_1984_last_position(1) + 1, 0] = -1.5
    assert rows(table(m, scale=1, majority=np.array([True])))["step_flagged"].tolist() == [False]
    assert rows(table(m, scale=12, majority=np.array([True])))["step_flagged"].tolist() == [True]


def test_max_share_is_the_peak_of_the_supplied_side_share():
    m = series()
    m[500:504, 0] = -1.5
    share = np.zeros((NT, 1))
    share[500:504, 0] = [0.2, 0.9, 1.0, 0.4]
    r = rows(table(m, share=share))
    assert np.isclose(r["max_share"][0], 1.0) and r["max_share_t"].tolist() == [502]


def summary_for(m, majority=None):
    t = table(m, majority=majority)
    s = summarise(t, np.arange(1, m.shape[1] + 1), [f"C{i}" for i in range(m.shape[1])], np.isfinite(m).sum(axis=0), NT)
    return s[s["side"] == "dry"].set_index("id")


def test_summary_figures_are_given_twice_all_and_unflagged():
    m = series()
    m[12:32, 0] = -1.5                                      # 20 months in 1951: early_record, flagged
    m[32, 0] = 0.5
    m[600:605, 0] = -1.2                                    # 5 months in 2000: unflagged
    s = summary_for(m).loc[1]
    assert s["n_events"] == 2 and s["n_events_unflagged"] == 1
    assert s["months_in_events"] == 25 and s["months_in_events_unflagged"] == 5
    assert s["longest_months"] == 20 and s["longest_start"] == "1951-01"
    assert s["longest_unflagged_months"] == 5 and s["longest_unflagged_start"] == "2000-01"
    assert np.isclose(s["max_magnitude"], 30.0) and np.isclose(s["max_magnitude_unflagged"], 6.0)
    assert s["started_1950s"] == 1 and s["started_1950s_unflagged"] == 0
    assert s["started_2000s"] == 1 and s["started_2000s_unflagged"] == 1


def test_summary_marks_a_longest_event_that_is_still_running():
    m = series(2)
    m[600:603, 0] = -1.5
    m[NT - 8:, 0] = -1.5                                    # unit 1: open at the end, and its longest
    m[600:620, 1] = -1.5
    m[NT - 3:, 1] = -1.5                                    # unit 2: open at the end, but not its longest
    s = summary_for(m)
    assert s.loc[1, "longest_months"] == 8 and bool(s.loc[1, "longest_is_open"]) and bool(s.loc[1, "in_event_now"])
    assert s.loc[1, "current_months"] == 8 and s.loc[1, "current_start"] == "2025-05"
    assert s.loc[2, "longest_months"] == 20 and not bool(s.loc[2, "longest_is_open"]) and bool(s.loc[2, "in_event_now"])
    assert s.loc[2, "last_closed_end"] == "2001-08" and s.loc[2, "months_since_last_closed"] == NT - 1 - 619


def test_summary_of_a_unit_with_no_events_or_only_flagged_events():
    m = series(2)
    m[12:15, 1] = -1.5                                      # unit 2: one early, flagged event only
    s = summary_for(m)
    assert s.loc[1, "n_events"] == 0 and np.isnan(s.loc[1, "longest_months"]) and s.loc[1, "longest_start"] == ""
    assert not bool(s.loc[1, "in_event_now"]) and np.isnan(s.loc[1, "max_magnitude"])
    assert s.loc[2, "n_events"] == 1 and s.loc[2, "n_events_unflagged"] == 0
    assert np.isnan(s.loc[2, "longest_unflagged_months"]) and np.isnan(s.loc[2, "max_magnitude_unflagged"])


def test_share_of_months_uses_months_with_a_value():
    m = series()
    m[:11, 0] = np.nan                                      # an 11-month warm-up
    m[100:110, 0] = -1.5
    s = summary_for(m).loc[1]
    assert s["valid_months"] == NT - 11 and np.isclose(s["share_of_months_in_events"], round(10 / (NT - 11), 4))
