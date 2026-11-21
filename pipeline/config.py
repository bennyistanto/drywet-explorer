"""Machine-specific paths. Edit here when the data moves; nothing else hardcodes a drive.

Source folders are read-only: no step may write under them.
"""
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# ---- sources (read-only)
TERRACLIMATE = Path(r"G:\temp\terraclimate")
SPI_FILE = str(TERRACLIMATE / "spi" / "wld_cli_terraclimate_spi_gamma_{n}_month.nc")
SPI_VAR = "spi_gamma_{n}_month"
SPEI_FILE = str(TERRACLIMATE / "spei" / "wld_cli_terraclimate_spei_pearson3_{n}_month.nc")
SPEI_VAR = "spei_pearson3_{n}_month"
EDDI_FILE = str(TERRACLIMATE / "eddi" / "wld_cli_terraclimate_eddi_{n:02d}month_1950_2025_base1991_2020.nc")
EDDI_VAR = "eddi"
EDDI_CAT_VAR = "eddi_cat"
ENSO = Path(r"G:\temp\enso")     # tables built by the `nino` repo from NOAA CPC files
BOUNDARY =str(Path(r"E:\temp\idn-bnd") / "idn_bnd_adm{n}.shp")

# ---- derived (written by the pipeline)
OUT = REPO / "data"
STEP0 = OUT / "step0"
STEP1 = OUT / "step1"            # share tables and class maps; the largest derived folder
STEP2 = OUT / "step2"            # events and per-unit summaries
STEP4 = OUT / "step4"            # manifest of the emerging hot spot test (its maps go straight to the site)
SITE = REPO / "site"            # Observable Framework source root
SITE_DATA = SITE / "data"        # written by step3_export; everything the browser loads
