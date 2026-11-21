"""Project conventions, stated once. Every step imports from here; nothing is retyped.

Reasons and measurements behind each value are in
`.claude/skills/drywet-explorer/SKILL.md`. Items marked PROPOSED await the
owner's decision and must not be described as settled.
"""

# ---- period and window -------------------------------------------------
PERIOD = ("1950-01", "2025-12")          # owner decision 2026-11-20: full record, flagged
N_MONTHS = 912
WINDOW = dict(west=94.5, east=141.5, south=-11.5, north=6.5)   # degrees; contains all of adm0
SCALES = (1, 3, 6, 12)
BASELINE = (1991, 2020)

# ---- index direction ---------------------------------------------------
# Stored values are never sign-flipped. Direction is metadata, applied through
# is_dry / is_wet below, so a bare threshold can never be used on the wrong index.
DRY_SIGN = {"spi": -1, "spei": -1, "eddi": +1}
INDEX_BOUND = {"spi": 3.09, "spei": 3.09, "eddi": 2.028}   # clip (SPI, SPEI); 30-year rank ceiling (EDDI)


def to_float(values):
    """float64 array with every non-value as NaN.

    A numpy masked array (what netCDF4 returns) is filled with NaN first:
    np.asarray() on it would keep the fill value as if it were data. Any value
    beyond the physical range of a standardised index is also set to NaN, so an
    unmasked fill (-9999, -32768) can never be classed as an extreme.
    """
    import numpy as np

    if np.ma.isMaskedArray(values):
        values = np.ma.asarray(values, dtype="float64").filled(np.nan)
    v = np.array(values, dtype="float64", copy=True)
    v[~np.isfinite(v) | (np.abs(v) > VALUE_SANITY_LIMIT)] = np.nan
    return v


VALUE_SANITY_LIMIT = 10.0     # no standardised index here exceeds 3.09 in magnitude


def is_dry(index, values, level=1.0):
    """True where `values` are at or beyond `level` on the dry side of `index`. Never true for a non-value."""
    return to_float(values) * DRY_SIGN[index] >= level


def is_wet(index, values, level=1.0):
    """True where `values` are at or beyond `level` on the wet (or low-demand) side. Never true for a non-value."""
    return to_float(values) * DRY_SIGN[index] <= -level


def eddi_bound(attrs):
    """EDDI's attainable bound, parsed from a source file's `attainable_range` attribute.

    The bound depends on the baseline length, so the file is the authority;
    INDEX_BOUND['eddi'] is only the value expected for the 1991-2020 baseline.
    """
    import re

    m = re.search(r"(\d+\.\d+)", str(attrs["attainable_range"]))
    if not m:
        raise ValueError(f"cannot read a bound from attainable_range: {attrs['attainable_range']!r}")
    return float(m.group(1))


# ---- SPI classes: WMO-No. 1090 (2012), Table 1 --------------------------
# Code 0 is no data. The breaks live in classify_spi() and nowhere else.
SPI_CLASS_LABELS = {
    1: "extremely dry",    # -2.0 and less
    2: "severely dry",     # -1.5 to -1.99
    3: "moderately dry",   # -1.0 to -1.49
    4: "near normal",      # -0.99 to 0.99
    5: "moderately wet",   # 1.0 to 1.49
    6: "very wet",         # 1.5 to 1.99
    7: "extremely wet",    # 2.0 and above
}
# The table is symmetric and closed towards the extremes: -1.0 itself is
# moderately dry, +1.0 itself moderately wet, -2.0 extremely dry, +2.0 extremely wet.
# EDDI classes are NOT defined here: the source files carry `eddi_cat` (NOAA
# categories, built in the nino project). Read that variable; do not retype breaks.
# PROPOSED: applying SPI_CLASSES to SPEI.


def classify_spi(values):
    """SPI class codes 1..7 (0 where not finite), matching WMO-1090 Table 1 at both -1.0 and +1.0."""
    import numpy as np

    v = to_float(values)
    out = np.zeros(v.shape, dtype="uint8")
    fin = np.isfinite(v)
    out[fin & (v <= -2.0)] = 1
    out[fin & (v > -2.0) & (v <= -1.5)] = 2
    out[fin & (v > -1.5) & (v <= -1.0)] = 3
    out[fin & (v > -1.0) & (v < 1.0)] = 4
    out[fin & (v >= 1.0) & (v < 1.5)] = 5
    out[fin & (v >= 1.5) & (v < 2.0)] = 6
    out[fin & (v >= 2.0)] = 7
    return out


# ---- class schemes -----------------------------------------------------
# Class codes do NOT run in the same direction in the two schemes: SPI code 1 is
# the driest, EDDI code 1 is the lowest demand. Nothing may rely on code order.
# Use the `side` of a class ('dry', 'normal', 'wet') from class_scheme() instead.
INDEX_SCHEME = {"spi": "spi7", "spei": "spi7", "eddi": "eddi11"}
SCHEME_STATUS = {"spi": "WMO-No. 1090 Table 1", "spei": "PROPOSED: SPI classes applied to SPEI",
                 "eddi": "NOAA categories as stored in the source file's eddi_cat"}
# Storage of share tables, per admin level. Shares are round(share * share_scale);
# means are round(mean * mean_scale) as int16. adm3 is stored coarser because it
# is 13 times larger and its units hold a dozen cells: half-percent steps and
# 0.01 index units lose nothing a kecamatan figure can carry. Measured on EDDI-1:
# 32 MB per layer at the adm1/adm2 encoding, about a third of that at this one.
SHARE_ENCODING = {
    1: dict(share_dtype="uint16", share_scale=10000, share_missing=65535, mean_scale=1000),
    2: dict(share_dtype="uint16", share_scale=10000, share_missing=65535, mean_scale=1000),
    3: dict(share_dtype="uint8", share_scale=200, share_missing=255, mean_scale=100),
}
MEAN_MISSING = -32768        # int16 code for "no value" in stored means


def class_scheme(index, eddi_cat_attrs=None):
    """List of (code, label, side) for an index. Code 0 is always no data.

    For EDDI the labels are read from the source variable's flag_meanings, so
    the categories are never retyped here; pass that variable's attrs.
    In EDDI, 'wet' means low evaporative demand, not wet conditions.
    """
    if INDEX_SCHEME[index] == "spi7":
        side = {1: "dry", 2: "dry", 3: "dry", 4: "normal", 5: "wet", 6: "wet", 7: "wet"}
        return [(c, SPI_CLASS_LABELS[c], side[c]) for c in range(1, 8)]
    if eddi_cat_attrs is None:
        raise ValueError("EDDI classes come from the file: pass the eddi_cat variable's attrs")
    labels = str(eddi_cat_attrs["flag_meanings"]).split()
    values = [int(v) for v in list(eddi_cat_attrs["flag_values"])]
    assert values == list(range(len(labels))), f"unexpected eddi_cat flag_values: {values}"
    out = []
    for v, lab in zip(values, labels):
        side = "dry" if lab.startswith("ED") else "wet" if lab.startswith("EW") else "normal"
        out.append((v + 1, lab, side))       # stored 0..10 -> codes 1..11, keeping 0 for no data
    return out


def classify_eddi_cat(cat):
    """Class codes 1..11 from the file's eddi_cat (0..10); 0 where it is not a value."""
    import numpy as np

    v = to_float(cat)
    out = np.zeros(v.shape, dtype="uint8")
    ok = np.isfinite(v) & (v >= 0) & (v <= 10) & (v == np.round(v))
    out[ok] = v[ok].astype("uint8") + 1
    return out


# ---- events (owner decision 2026-11-20: WMO-No. 1090 section 6.1) --------
# "Drought, according to the SPI, starts when the SPI value is equal or below
# -1.0 and ends when the value becomes positive."
#   start: first month at or beyond EVENT_ONSET on the event's side
#   continues: while the index has not crossed to the other side; exactly 0 continues
#   end: the last month before the index is on the other side, or before a missing month
#   magnitude: sum of the absolute index over the event's months (WMO section 3)
# WMO defines this for SPI drought only. Using the mirror image for wet events,
# and using either for SPEI and EDDI, is this project's own extension and must
# be labelled as such wherever it is shown.
EVENT_ONSET = 1.0
EVENT_RULE = dict(
    name="WMO-No. 1090 section 6.1", onset=EVENT_ONSET,
    start="first month with the index at or beyond the onset level on the event's side",
    end="the month before the index is on the opposite side of zero; a missing month also ends it",
    magnitude="sum of the absolute index over the event's months",
    extension="wet events, and all SPEI and EDDI events, use the mirrored or transferred rule: a project choice",
)
# PROPOSED: events are identified on the unit's area-weighted MEAN index (from
# step 1), not cell by cell and not on the share of area beyond a threshold.

# ---- zonal aggregation -------------------------------------------------
SUPERSAMPLE = 8            # coverage fractions from an 8 x 8 sub-grid per cell: steps of 1/64
MAP_MIN_FRACTION = 0.5     # used only by step 0's "half inside" count. The MAP draws every touched cell
                           # (step 1), the same set the statistics use: owner's all-touched rule.
EARTH_RADIUS_KM = 6371.0088
# PROPOSED: minimum support for a percent-of-area figure, in cell equivalents.
MIN_CELL_EQUIV = 30

# ---- quality flags (owner confirmed both rules 2026-11-20) --------------
FLAG_EARLY_RECORD = dict(
    name="early_record",
    start="1950-01", end="1969-12",
    scope="every cell",
    reason="TerraClimate reads about 10 points (1950s) and 4 points (1960s) drier than gauges at the same cells",
)
# step_1984 replaces the earlier riau_block run-length rule, which was too narrow.
# Region and period both confirmed by the owner on 2026-11-20.
FLAG_STEP_1984 = dict(
    name="step_1984",
    start="1950-01",
    end_scale_1="1983-12",       # an n-month index is flagged through this month plus (n - 1)
    scope="land cells with the early-1984 step on SPI-12 or EDDI-12",
    layers=(("spi", 12), ("eddi", 12)),
    before=("1975-01", "1983-12"), after=("1985-01", "1993-12"),
    before_min=1.0,              # mean before, on the dry-positive scale, at least this
    step_min=1.0,                # mean before minus mean after, at least this
    reason="TerraClimate's monthly inputs change at 1984-01 across northern and central Sumatra and West "
           "Kalimantan, in rainfall and in evaporative demand; three gauges inside the region read near normal "
           "in 1970-83 where TerraClimate reads about 20% low",
    limits="the thresholds are a judgement and the edge is a gradient; no gauge evidence for West Kalimantan; "
           "the cause in TerraClimate has not been looked up",
)
UNIT_FLAG_MAJORITY = 0.5         # PROPOSED: a unit carries a cell flag when over half its cell area does

# Emerging hot spot test (step 4): months in the space-time cube, ending at the month on the map.
# PROPOSED. Chosen from analysis/ehsa_retest.py (output in analysis/ehsa_retest_spi03*.txt).
HOTSPOT_WINDOW = 12


def month_position(month):
    """'YYYY-MM' -> 0-based position in the record (PERIOD[0] is 0)."""
    y0, m0 = (int(x) for x in PERIOD[0].split("-"))
    y, m = (int(x) for x in month.split("-"))
    return (y - y0) * 12 + (m - m0)


def step_1984_last_position(scale):
    """Last flagged month position for an index accumulated over `scale` months.

    The inputs change at 1984-01. An n-month value still contains pre-1984
    months until 1984-01 plus (n - 2), so the flag runs through 1983-12 plus (n - 1).
    """
    return month_position(FLAG_STEP_1984["end_scale_1"]) + (int(scale) - 1)


def step_1984_cells(dry_positive):
    """Cells with the step, from one [time, ...] cube on the dry-positive scale.

    Returns (mask, before, after). NaN-safe: a cell with no value in either window is not flagged.
    """
    import numpy as np
    import warnings

    F = FLAG_STEP_1984
    b0, b1 = (month_position(m) for m in F["before"])
    a0, a1 = (month_position(m) for m in F["after"])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        before = np.nanmean(dry_positive[b0:b1 + 1], axis=0)
        after = np.nanmean(dry_positive[a0:a1 + 1], axis=0)
    mask = np.isfinite(before) & np.isfinite(after) & (before >= F["before_min"]) & ((before - after) >= F["step_min"])
    return mask, before, after
