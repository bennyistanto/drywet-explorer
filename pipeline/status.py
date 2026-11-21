"""Where each series stands in an event, month by month: how long it has lasted and what it is doing.

The event rule is the one used everywhere else (pipeline/events.py, WMO-No. 1090 section 6.1): an event starts
in the first month the index is at or beyond the onset level on one side, and runs until the index crosses
zero or a month is missing. This module does not find events again by another rule: `running` gives, for
every month, the number of months the event in progress has lasted, and tests/test_status.py asserts that
this is exactly what scan_events' start and end dates imply.

Two readings of that, both stored per cell and month:

  HOW LONG   the months so far, in bins (DURATION_BINS)
  STATUS     one of five states of an event, from run theory:
               new         first or second month of the event
               deepening   third month on, at or beyond the onset level, and further from zero than a month ago
               persisting  third month on, at or beyond the onset level, not further from zero than a month ago
               easing      third month on, back inside the onset level, not yet across zero
               ended       the event ended this month (it was running a month ago and is not now)

The five states and the bins are THIS PROJECT'S OWN (owner asked for a run-theory status, 2026-11-21): no
standard defines them. They are PROPOSED. They describe the record up to the month shown; none is a forecast.

Codes, one byte per cell and month, for both products:
  0 no value   1 no event
  dry side 2..6, wet side 7..11, in the order of DURATION_BINS or of STATES.
"""
import numpy as np

DURATION_BINS = ((1, 2, "1 to 2 months"), (3, 5, "3 to 5 months"), (6, 11, "6 to 11 months"),
                 (12, 23, "12 to 23 months"), (24, None, "24 months or more"))
STATES = ("new", "deepening", "persisting", "easing", "ended")
NEW_MONTHS = 2        # PROPOSED: an event is "new" in its first two months


def running(d, onset=1.0):
    """Months so far of the event in progress, int16 [time, series]; 0 where no event is running.

    d: float [time, series], the event's own side POSITIVE (as for events.scan_events), NaN = no value.
    """
    d = np.asarray(d, dtype=np.float64)
    nt, ns = d.shape
    out = np.zeros((nt, ns), np.int16)
    dur = np.zeros(ns, np.int16)
    for t in range(nt):
        x = d[t]
        fin = np.isfinite(x)
        cont = (dur > 0) & fin & (x >= 0)
        ending = (dur > 0) & ~cont
        begin = (dur == 0) & fin & (x >= onset)          # a series that just ended has x < 0 or no value: it cannot begin
        dur = np.where(cont, dur + 1, 0).astype(np.int16)
        dur[begin & ~ending] = 1
        out[t] = dur
    return out


def duration_code(dur_dry, dur_wet, has_value):
    """HOW LONG codes from the two sides' running durations."""
    code = np.where(has_value, 1, 0).astype(np.uint8)
    for base, dur in ((2, dur_dry), (7, dur_wet)):
        for k, (lo, hi, _) in enumerate(DURATION_BINS):
            m = (dur >= lo) if hi is None else (dur >= lo) & (dur <= hi)
            code[m] = base + k
    return code


def combined_code(status, howlong):
    """Both products in one byte, which is what the site ships (two separate maps cost twice the bytes).

    0 no value, 1 no event, else 2 + side * 25 + state * 5 + bin, with side 0 dry, 1 wet; state the position
    in STATES; bin the position in DURATION_BINS (0 for "ended", which has no running duration).
    decode_combined is the inverse; the page does the same arithmetic.
    """
    status = np.asarray(status).astype(np.int16)
    howlong = np.asarray(howlong).astype(np.int16)
    k = status - 2
    side, state = k // 5, k % 5
    b = np.where(howlong >= 2, (howlong - 2) % 5, 0)
    return np.where(status < 2, status, 2 + side * 25 + state * 5 + b).astype(np.uint8)


def decode_combined(code):
    """(status, howlong) codes from a combined code."""
    code = np.asarray(code).astype(np.int16)
    k = code - 2
    side, state, b = k // 25, (k % 25) // 5, k % 5
    status = np.where(code < 2, code, 2 + side * 5 + state)
    howlong = np.where(code < 2, code, np.where(state == 4, 1, 2 + side * 5 + b))
    return status.astype(np.uint8), howlong.astype(np.uint8)


def status_code(d, dur_dry, dur_wet, onset=1.0):
    """STATUS codes. d: float [time, series] with the DRY side positive."""
    d = np.asarray(d, dtype=np.float64)
    has = np.isfinite(d)
    code = np.where(has, 1, 0).astype(np.uint8)
    prev = np.vstack([np.full((1, d.shape[1]), np.nan), d[:-1]])
    for base, dur, x, xp in ((2, dur_dry, d, prev), (7, dur_wet, -d, -prev)):
        was = np.vstack([np.zeros((1, d.shape[1]), np.int16), dur[:-1]])
        ended = (was > 0) & (dur == 0) & has               # with no value this month the cell stays "no value"
        code[ended] = base + 4
    # an event in progress always wins over "ended" on the other side (a dry event can end in the month a wet one begins)
    for base, dur, x, xp in ((2, dur_dry, d, prev), (7, dur_wet, -d, -prev)):
        on = dur > 0
        new = on & (dur <= NEW_MONTHS)
        later = on & ~new
        at = x >= onset
        code[new] = base
        code[later & at & (x > xp)] = base + 1
        code[later & at & ~(x > xp)] = base + 2
        code[later & ~at] = base + 3
    return code
