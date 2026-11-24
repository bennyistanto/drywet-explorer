"""The driver code: one byte for the state of three indices."""
import numpy as np

from pipeline.step9_driver import combine, decode, state_of


def test_state_uses_each_index_own_dry_direction():
    v = np.array([-1.0, -0.99, 0.0, 0.99, 1.0, np.nan])
    assert state_of("spi", v).tolist() == [1, 0, 0, 0, 2, 255]
    assert state_of("spei", v).tolist() == [1, 0, 0, 0, 2, 255]
    assert state_of("eddi", v).tolist() == [2, 0, 0, 0, 1, 255]      # high demand is the dry side


def test_combine_round_trips_every_combination():
    grid = np.array([[a, b, c] for a in range(3) for b in range(3) for c in range(3)], dtype=np.uint8)
    code = combine(dict(spi=grid[:, 0], spei=grid[:, 1], eddi=grid[:, 2]))
    assert sorted(code.tolist()) == list(range(1, 28))
    sp, se, ed = decode(code)
    assert np.array_equal(sp, grid[:, 0]) and np.array_equal(se, grid[:, 1]) and np.array_equal(ed, grid[:, 2])


def test_missing_in_any_index_is_no_value():
    code = combine(dict(spi=np.array([1, 255, 0], np.uint8), spei=np.array([1, 1, 0], np.uint8), eddi=np.array([255, 1, 0], np.uint8)))
    assert code.tolist() == [0, 0, 1]
