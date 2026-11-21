"""Unit codes for the boundary attribute tables, in one place.

step0_grid and step0_boundaries both call these on the features in file order,
so a unit id can never differ between the statistics tables and the outlines.

Two numbering schemes occur in the files and must not be mixed:
  Kemendagri (KDPKAB '31.01', KDCPUM '11.01.01'): the code used for units here.
  BPS (a1bps, a2bps): used only for the province of an adm2 feature and as a
    fallback parent for adm3. The two agree for only part of the kabupaten.
"""
import re
from difflib import SequenceMatcher

_DOTTED = re.compile(r"^\d{2}(\.\d{2})*$")
NAME_SIMILARITY = 0.8      # same code, names at least this similar: one unit (spelling variants)


def text(v):
    """A stripped string, or None for null, NaN, empty and '<Null>'."""
    if v is None:
        return None
    try:
        if v != v:          # NaN
            return None
    except Exception:  # noqa: BLE001
        pass
    s = str(v).strip()
    return s if s and s.lower() not in ("<null>", "none", "nan") else None


def digits(v):
    """Digits of a value, or None. For BPS fields, which are plain numbers."""
    s = text(v)
    if s is None:
        return None
    d = "".join(ch for ch in s if ch.isdigit())
    return d or None


def clean_code(v, want):
    """A dotted Kemendagri code with exactly `want` digits, as digits; else None.

    '31.01' -> '3101'. Rejects placeholders ('12.--'), joined codes
    ('71.05/71.10') and anything of another length.
    """
    s = text(v)
    if s is None or not _DOTTED.match(s):
        return None
    d = s.replace(".", "")
    return d if len(d) == want else None


def prefix_code(v, want):
    """The leading numeric groups of a dotted code, as `want` digits; else None.

    '91.15.--' with want=4 -> '9115'. Lets an uncoded kecamatan keep a usable
    kabupaten prefix.
    """
    s = text(v)
    if s is None:
        return None
    out = ""
    for part in s.split("."):
        if len(part) == 2 and part.isdigit():
            out += part
            if len(out) == want:
                return out
        else:
            break
    return None


def adm2_codes(kdpkab):
    """One code per adm2 feature, in order. Features without a clean code get U01, U02, ..."""
    out, n = [], 0
    for v in kdpkab:
        c = clean_code(v, 4)
        if c is None:
            n += 1
            c = f"U{n:02d}"
        out.append(c)
    return out


def _similar(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio() >= NAME_SIMILARITY


def adm3_codes(kdcpum, wadmkc, namobj):
    """Code, name and shared-code marker per adm3 feature, in order.

    Features sharing a KDCPUM are one unit when their names are spelling
    variants or missing, and separate units ('720821-1', '720821-2', ...) when
    the names are clearly different kecamatan. Every feature of a unit gets the
    unit's name, taken from the first feature that has one.
    Features without a clean 6-digit code get U001, U002, ...
    """
    n = len(kdcpum)
    names = [text(a) or text(b) for a, b in zip(wadmkc, namobj)]
    base, nu = [], 0
    for v in kdcpum:
        c = clean_code(v, 6)
        if c is None:
            nu += 1
            c = f"U{nu:03d}"
        base.append(c)
    groups = {}
    for i, c in enumerate(base):
        groups.setdefault(c, []).append(i)
    code = list(base)
    name = list(names)
    shared = [False] * n
    for c, idx in groups.items():
        if len(idx) == 1:
            continue
        clusters = []                      # [name, [feature indices]]
        unnamed = []
        for i in idx:
            if names[i] is None:
                unnamed.append(i)
                continue
            for cl in clusters:
                if _similar(cl[0], names[i]):
                    cl[1].append(i)
                    break
            else:
                clusters.append([names[i], [i]])
        if not clusters:
            continue                       # all unnamed: one unit, no name
        clusters[0][1].extend(unnamed)     # an unnamed part joins the first named unit
        for k, (nm, members) in enumerate(clusters, start=1):
            for i in members:
                name[i] = nm
                if len(clusters) > 1:
                    code[i] = f"{c}-{k}"
                    shared[i] = True
    return code, name, shared
