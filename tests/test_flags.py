"""The two quality flags: dates, the scale-aware end month, and the step test."""
import numpy as np

from pipeline import conventions as K


def test_month_positions():
    assert K.month_position("1950-01") == 0
    assert K.month_position("1969-12") == 239
    assert K.month_position("1983-12") == 407
    assert K.month_position("2025-12") == K.N_MONTHS - 1


def test_step_flag_end_moves_with_the_accumulation_window():
    assert K.step_1984_last_position(1) == K.month_position("1983-12")
    assert K.step_1984_last_position(3) == K.month_position("1984-02")
    assert K.step_1984_last_position(6) == K.month_position("1984-05")
    assert K.step_1984_last_position(12) == K.month_position("1984-11")


def test_first_unflagged_value_holds_no_pre_1984_month():
    # a 12-month value at 1984-12 sums 1984-01..1984-12: the first with no pre-1984 input
    for scale in (1, 3, 6, 12):
        first_clean = K.step_1984_last_position(scale) + 1
        assert first_clean - (scale - 1) == K.month_position("1984-01")


def test_step_cells():
    nt = K.N_MONTHS
    d = np.zeros((nt, 5))
    b0, b1 = K.month_position("1975-01"), K.month_position("1983-12")
    a0, a1 = K.month_position("1985-01"), K.month_position("1993-12")
    d[b0:b1 + 1, 0], d[a0:a1 + 1, 0] = 1.6, 0.2      # dry before, normal after: step
    d[b0:b1 + 1, 1], d[a0:a1 + 1, 1] = 1.6, 1.0      # dry before and after: no step (difference 0.6)
    d[b0:b1 + 1, 2], d[a0:a1 + 1, 2] = 0.8, -0.9     # big difference but not dry enough before
    d[b0:b1 + 1, 3], d[a0:a1 + 1, 3] = 1.0, 0.0      # exactly on both thresholds: step
    d[:, 4] = np.nan                                  # no data: never flagged
    mask, before, after = K.step_1984_cells(d)
    assert mask.tolist() == [True, False, False, True, False]
    assert np.isclose(before[0], 1.6) and np.isclose(after[0], 0.2)
