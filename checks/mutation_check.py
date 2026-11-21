"""Do the tests catch deliberate errors? Applies one text mutation at a time to a
scratch copy of pipeline/ and tests/, runs pytest there, and reports caught or missed.

The repository itself is never modified. Run from the repository root:
    python checks/mutation_check.py <empty scratch folder>
"""
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
work = Path(sys.argv[1])

MUTANTS = [
    # (file, exact text, replacement, what it breaks)
    ("pipeline/events.py", "        dur[begin] = 0\n", "", "duration not reset between events"),
    ("pipeline/events.py", "        mag[begin] = 0.0\n", "", "magnitude not reset"),
    ("pipeline/events.py", "        peak[begin] = -np.inf\n", "", "peak not reset"),
    ("pipeline/events.py", "        n_on[begin] = 0\n", "", "n_onset not reset"),
    ("pipeline/events.py", "        ex[begin] = np.nan\n", "", "extra maximum not reset"),
    ("pipeline/events.py", "        ex_t[begin] = -1\n", "", "extra month not reset"),
    ("pipeline/events.py", "cont = active & fin & (x >= 0)", "cont = active & fin & (x > 0)", "exactly 0 ends an event"),
    ("pipeline/events.py", "fin & (x >= onset)\n", "fin & (x > onset)\n", "exactly onset does not start"),
    ("pipeline/step2_events.py", "- ev[\"start\"] + 1, 0, None)", "- ev[\"start\"], 0, None)", "n_early one short"),
    ("pipeline/step2_events.py", "(ev[\"start\"] <= step_end)", "(ev[\"start\"] < step_end)", "step flag ends a month early"),
    ("pipeline/step2_events.py", "step_end = K.step_1984_last_position(scale)", "step_end = K.step_1984_last_position(1)", "step flag ignores the scale"),
    ("pipeline/step2_events.py", "* K.DRY_SIGN[index] * (1 if s_code == 0 else -1)", "* -1 * (1 if s_code == 0 else -1)", "direction ignores the index"),
    ("pipeline/step2_events.py", "(n_early > 0) | np.asarray(step_f, dtype=bool)", "(n_early > 0)", "step flag left out of flagged"),
    ("pipeline/step2_events.py", "es, eu = None, None", "es, eu = None, None", "placeholder, expected not to apply"),
    ("pipeline/step2_events.py", "        eu = es[~es[\"flagged\"]]\n", "        eu = es\n", "unflagged figures include flagged events"),
    ("pipeline/step2_events.py", "df[\"months_since_last_closed\"] = (nt - 1 - cl)", "df[\"months_since_last_closed\"] = (nt - cl)", "months since last event off by one"),
    ("pipeline/step2_events.py", "df[f\"{name}_is_open\"] = best[\"open\"]", "df[f\"{name}_is_open\"] = ~best[\"open\"]", "longest_is_open inverted"),
    ("pipeline/step2_events.py", "df[\"valid_months\"].where(df[\"valid_months\"] > 0), 4)", "float(912), 4)", "share of months over the whole record"),
    ("pipeline/step1_classes.py", "np.asarray(cell_area, dtype=np.float64)[cell[keep]]", "np.asarray(cell_area, dtype=np.float64)[cell[keep]] * 0 + 1.0", "cells counted, not area-weighted"),
    ("pipeline/step1_classes.py", "    keep = pos >= 0\n    n_sel", "    keep = pos >= -1\n    n_sel", "sea cells kept"),
    ("pipeline/step1_classes.py", "    valid = area.sum(axis=2)\n", "    valid = np.asarray(W.sum(axis=1)).ravel()[None, :] * np.ones(area.shape[:2])\n", "denominator is all cells, not valued cells"),
    ("pipeline/step1_classes.py", "m_enc[mok] = np.round(mean[mok] * E[\"mean_scale\"])", "m_enc[mok] = np.round(mean[mok].astype(np.float32) * E[\"mean_scale\"])", "mean rounded from float32"),
    ("pipeline/step1_classes.py", "if s == side]\n    with np.errstate", "if s != side]\n    with np.errstate", "side share takes the other classes"),
    ("pipeline/conventions.py", "out[ok] = v[ok].astype(\"uint8\") + 1", "out[ok] = v[ok].astype(\"uint8\")", "EDDI codes off by one"),
    ("pipeline/conventions.py", "ok = np.isfinite(v) & (v >= 0) & (v <= 10)", "ok = np.isfinite(v) & (v >= -1) & (v <= 10)", "negative EDDI category accepted"),
    ("pipeline/conventions.py", "side = \"dry\" if lab.startswith(\"ED\") else \"wet\" if lab.startswith(\"EW\")", "side = \"wet\" if lab.startswith(\"ED\") else \"dry\" if lab.startswith(\"EW\")", "EDDI sides swapped"),
    ("pipeline/conventions.py", "side = {1: \"dry\", 2: \"dry\", 3: \"dry\", 4: \"normal\", 5: \"wet\", 6: \"wet\", 7: \"wet\"}", "side = {1: \"wet\", 2: \"wet\", 3: \"wet\", 4: \"normal\", 5: \"dry\", 6: \"dry\", 7: \"dry\"}", "SPI sides swapped"),
    ("pipeline/conventions.py", "    if np.ma.isMaskedArray(values):\n        values = np.ma.asarray(values, dtype=\"float64\").filled(np.nan)\n", "", "mask dropped"),
    ("pipeline/conventions.py", "FLAG_EARLY_RECORD = dict(\n    name=\"early_record\",\n    start=\"1950-01\", end=\"1969-12\",", "FLAG_EARLY_RECORD = dict(\n    name=\"early_record\",\n    start=\"1950-01\", end=\"1970-12\",", "early_record a year longer"),
    ("pipeline/conventions.py", "UNIT_FLAG_MAJORITY = 0.5 ", "UNIT_FLAG_MAJORITY = 0.4 ", "majority threshold changed"),
    ("pipeline/conventions.py", "EVENT_ONSET = 1.0", "EVENT_ONSET = 1.2", "onset level changed"),
    ("pipeline/conventions.py", "    3: dict(share_dtype=\"uint8\", share_scale=200, share_missing=255, mean_scale=100),", "    3: dict(share_dtype=\"uint8\", share_scale=200, share_missing=254, mean_scale=100),", "adm3 missing code changed"),
    ("pipeline/conventions.py", "    out[fin & (v > -1.5) & (v <= -1.0)] = 3", "    out[fin & (v > -1.5) & (v < -1.0)] = 3", "exactly -1.0 not moderately dry"),
    ("pipeline/conventions.py", "return month_position(FLAG_STEP_1984[\"end_scale_1\"]) + (int(scale) - 1)", "return month_position(FLAG_STEP_1984[\"end_scale_1\"]) + int(scale)", "step flag a month long"),
]


def run(folder):
    r = subprocess.run([sys.executable, "-m", "pytest", "tests", "-q", "-x", "-p", "no:cacheprovider"], cwd=folder,
                       capture_output=True, text=True)
    return r.returncode, (r.stdout.strip().splitlines() or [""])[-1]


def fresh():
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    for d in ("pipeline", "tests"):
        shutil.copytree(REPO / d, work / d, ignore=shutil.ignore_patterns("__pycache__"))


fresh()
code, last = run(work)
print(f"baseline copy: exit {code}: {last}")
assert code == 0, "the unmodified copy must pass"
caught = missed = skipped = 0
for rel, old, new, what in MUTANTS:
    p = work / rel
    s = p.read_text(encoding="utf-8")
    if s.count(old) != 1 or old == new:
        skipped += 1
        print(f"  SKIPPED  {what}  ({rel}: text found {s.count(old)} times)")
        continue
    p.write_text(s.replace(old, new), encoding="utf-8")
    code, last = run(work)
    p.write_text(s, encoding="utf-8")              # restore; Windows often refuses to delete the folder mid-run
    if code != 0:
        caught += 1
        print(f"  caught   {what}")
    else:
        missed += 1
        print(f"  MISSED   {what}  ({rel})")
print(f"\n{caught} caught, {missed} missed, {skipped} skipped, of {len(MUTANTS)}")
