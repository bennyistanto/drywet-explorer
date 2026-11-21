"""Conventions that a wrong sign or a kept fill value would silently break.

Run from the repository root: python -m pytest tests -q
"""
import numpy as np

from pipeline import conventions as K
from pipeline.admin_codes import adm2_codes, adm3_codes, clean_code, prefix_code


def test_classify_spi_matches_wmo_table_at_every_break():
    v = np.array([-2.5, -2.0, -1.99, -1.5, -1.49, -1.0, -0.99, 0.0, 0.99, 1.0, 1.49, 1.5, 1.99, 2.0, 2.5])
    assert K.classify_spi(v).tolist() == [1, 1, 2, 2, 3, 3, 4, 4, 4, 5, 5, 6, 6, 7, 7]


def test_classify_spi_non_values_are_no_data():
    assert K.classify_spi(np.array([np.nan, np.inf, -np.inf])).tolist() == [0, 0, 0]


def test_classify_spi_masked_fill_is_no_data_not_extreme_drought():
    m = np.ma.masked_values(np.array([-9999.0, -1.2], dtype="float32"), -9999.0)
    assert K.classify_spi(m).tolist() == [0, 3]


def test_a_masked_value_inside_the_valid_range_is_still_no_data():
    # the sanity limit cannot rescue this one: -1.2 looks like a real value, only the mask says it is not
    m = np.ma.array([-1.2, -1.2, 1.6], mask=[True, False, False])
    assert K.classify_spi(m).tolist() == [0, 3, 6]
    assert K.is_dry("spi", m).tolist() == [False, True, False]


EDDI_ATTRS = dict(flag_values=list(range(11)), flag_meanings="EW4 EW3 EW2 EW1 EW0 Normal ED0 ED1 ED2 ED3 ED4")


def test_eddi_categories_are_stored_as_code_plus_one_with_zero_for_no_data():
    cat = np.array([0.0, 5.0, 10.0, np.nan, -1.0, 11.0, 2.5])
    assert K.classify_eddi_cat(cat).tolist() == [1, 6, 11, 0, 0, 0, 0]
    assert K.classify_eddi_cat(np.ma.array([3.0, 3.0], mask=[True, False])).tolist() == [0, 4]


def test_eddi_scheme_sides_follow_the_labels():
    s = K.class_scheme("eddi", EDDI_ATTRS)
    assert [c for c, _, _ in s] == list(range(1, 12))
    assert [lab for _, lab, _ in s] == EDDI_ATTRS["flag_meanings"].split()
    assert [side for _, _, side in s] == ["wet"] * 5 + ["normal"] + ["dry"] * 5


def test_spi_scheme_sides_and_opposite_code_direction():
    s = K.class_scheme("spi")
    assert [side for _, _, side in s] == ["dry"] * 3 + ["normal"] + ["wet"] * 3
    assert s[0][1] == "extremely dry" and s[6][1] == "extremely wet"
    assert K.class_scheme("spei") == s
    # code 1 is the dry end for SPI and the low-demand end for EDDI: never compare codes across schemes
    assert s[0][2] == "dry" and K.class_scheme("eddi", EDDI_ATTRS)[0][2] == "wet"


def test_eddi_scheme_refuses_to_guess_the_categories():
    import pytest
    with pytest.raises(ValueError):
        K.class_scheme("eddi")


def test_owner_confirmed_values_are_pinned():
    # these were decided by the owner on 2026-11-20; a change here must be a decision, not an edit
    assert K.PERIOD == ("1950-01", "2025-12") and K.N_MONTHS == 912 and K.SCALES == (1, 3, 6, 12)
    assert K.EVENT_ONSET == 1.0
    assert K.FLAG_EARLY_RECORD["start"] == "1950-01" and K.FLAG_EARLY_RECORD["end"] == "1969-12"
    F = K.FLAG_STEP_1984
    assert F["end_scale_1"] == "1983-12" and F["before"] == ("1975-01", "1983-12") and F["after"] == ("1985-01", "1993-12")
    assert F["before_min"] == 1.0 and F["step_min"] == 1.0 and F["layers"] == (("spi", 12), ("eddi", 12))
    assert K.DRY_SIGN == {"spi": -1, "spei": -1, "eddi": 1}


def test_storage_encodings_are_pinned():
    assert K.SHARE_ENCODING[1] == K.SHARE_ENCODING[2] == dict(share_dtype="uint16", share_scale=10000, share_missing=65535, mean_scale=1000)
    assert K.SHARE_ENCODING[3] == dict(share_dtype="uint8", share_scale=200, share_missing=255, mean_scale=100)
    assert K.MEAN_MISSING == -32768 and K.UNIT_FLAG_MAJORITY == 0.5


def test_classify_spi_unmasked_fill_is_no_data():
    assert K.classify_spi(np.array([-9999.0, -32768.0, -1.0])).tolist() == [0, 0, 3]


def test_classify_spi_float32_same_as_float64():
    v = np.array([-2.0, -1.5, -1.0, 1.0, 1.5, 2.0])
    assert K.classify_spi(v.astype("float32")).tolist() == K.classify_spi(v).tolist()


def test_direction_spi_and_spei_negative_is_dry():
    v = np.array([-2.5, -1.0, -0.999, 0.0, 0.999, 1.0, 2.5, np.nan])
    for idx in ("spi", "spei"):
        assert K.is_dry(idx, v).tolist() == [True, True, False, False, False, False, False, False]
        assert K.is_wet(idx, v).tolist() == [False, False, False, False, False, True, True, False]


def test_direction_eddi_positive_is_dry():
    v = np.array([-2.0, -1.0, 0.0, 1.0, 2.0, np.nan])
    assert K.is_dry("eddi", v).tolist() == [False, False, False, True, True, False]
    assert K.is_wet("eddi", v).tolist() == [True, True, False, False, False, False]


def test_direction_never_true_for_a_fill_value():
    m = np.ma.masked_values(np.array([-9999.0, -32768.0]), -9999.0)
    assert not K.is_dry("spi", m).any() and not K.is_wet("eddi", m).any()


def test_is_dry_agrees_with_dry_classes():
    v = np.linspace(-3.09, 3.09, 6181)
    assert np.array_equal(K.is_dry("spi", v), K.classify_spi(v) <= 3)
    assert np.array_equal(K.is_wet("spi", v), K.classify_spi(v) >= 5)


def test_eddi_bound_from_attribute():
    assert K.eddi_bound({"attainable_range": "+/- 2.028; a nonparametric index cannot exceed ..."}) == 2.028


def test_clean_code_rejects_placeholders_and_joined_codes():
    assert clean_code("31.01", 4) == "3101"
    assert clean_code("11.01.01", 6) == "110101"
    for bad in ("12.--", "71.05/71.10", "52.0452.07", None, float("nan"), "", "31.01.01"):
        assert clean_code(bad, 4) is None


def test_prefix_code_keeps_a_usable_kabupaten_prefix():
    assert prefix_code("91.15.--", 4) == "9115"
    assert prefix_code("61.02.--", 4) == "6102"
    assert prefix_code("12.--", 4) is None
    assert prefix_code(None, 4) is None


def test_adm2_codes_numbers_uncoded_features_in_file_order():
    assert adm2_codes(["31.01", None, "71.05/71.10", "51.06"]) == ["3101", "U01", "U02", "5106"]


def test_adm3_shared_code_is_split_only_for_different_names():
    kd = ["72.08.21", "72.08.21", "72.08.21", "11.01.01", "11.01.01", "61.12.05", "61.12.05", "91.15.--"]
    wk = ["Bolano", "Ongka Malino", "Tomini", "Bakongan", "Bakongann", None, "Batu Ampar", "Walani"]
    nm = [None] * 8
    code, name, shared = adm3_codes(kd, wk, nm)
    assert code[:3] == ["720821-1", "720821-2", "720821-3"] and shared[:3] == [True, True, True]
    assert code[3:5] == ["110101", "110101"] and name[3:5] == ["Bakongan", "Bakongan"]      # spelling variant: one unit
    assert code[5:7] == ["611205", "611205"] and name[5:7] == ["Batu Ampar", "Batu Ampar"]   # unnamed part takes the name
    assert code[7] == "U001" and name[7] == "Walani"
