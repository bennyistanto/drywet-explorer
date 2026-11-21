"""Print the global and variable attributes of one file per index family, for the method document.
Run from the repository root: python analysis/source_attrs.py"""
import sys
from pathlib import Path

import netCDF4 as nc

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline.step1_classes import source_of          # noqa: E402

for index in ("spi", "spei", "eddi"):
    path, var, catvar = source_of(index, 3)
    with nc.Dataset(path) as ds:
        print(f"\n===== {index.upper()}-3  {path}")
        print("dimensions:", {k: len(v) for k, v in ds.dimensions.items()})
        print("variables:", list(ds.variables))
        for k in ds.ncattrs():
            print(f"  global {k}: {str(ds.getncattr(k))[:400]}")
        for name in [var] + ([catvar, "eddi_pct"] if catvar else []):
            if name in ds.variables:
                v = ds.variables[name]
                print(f"  -- {name} {v.dtype} {v.dimensions}")
                for k in v.ncattrs():
                    print(f"     {k}: {str(v.getncattr(k))[:400]}")
