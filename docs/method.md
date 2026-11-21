# Method

How the dashboard's numbers are made, written so that someone holding the same
kind of data can prepare it and run the pipeline. Each statement here is either
read from the source files' own attributes, computed by a named script in this
repository, or cited. Choices that are this project's own, and not a published
standard, are marked **choice**. Choices still awaiting confirmation are marked
**proposed**.

## 1. What you need before you start

The pipeline does not compute the indices. It starts from index cubes that
already exist, and reduces them to small files a browser can load.

| Input | What it is | Derived from | How | Made with |
|---|---|---|---|---|
| SPI at 1, 3, 6, 12 months | Standardized Precipitation Index | monthly precipitation | n-month running total, fitted with a Gamma distribution over the calibration years, converted to a standard normal score, limited to -3.09 to +3.09 | [`precip-index`](https://github.com/bennyistanto/precip-index) |
| SPEI at 1, 3, 6, 12 months | Standardized Precipitation Evapotranspiration Index | monthly precipitation minus monthly reference evapotranspiration | n-month running total of the difference, fitted with a Pearson type III distribution, same conversion and limits | `precip-index` |
| EDDI at 1, 3, 6, 12 months | Evaporative Demand Drought Index | monthly reference evapotranspiration | trailing n-month sum, ranked per calendar month against the baseline years, turned into a probability with the Tukey plotting position (i - 1/3) / (k + 1 + 1/3), then into a z-score with the inverse normal | [`nino`](https://github.com/bennyistanto/nino), notebook 01 |
| EDDI category | NOAA class of each EDDI value | EDDI percentile, where percentile = 100 x normal probability of EDDI | percentile bounds 0, 2, 5, 10, 20, 30, 70, 80, 90, 95, 98 give EW4 to EW0, Normal, ED0 to ED4 | stored in the EDDI file as `eddi_cat` |
| Admin boundaries, levels 1 to 3 | provinces, kabupaten and kota, kecamatan | national boundary shapefiles | used as they are; codes are read by `pipeline/admin_codes.py` | not made here |
| ENSO tables | RONI and ONI by month, and a list of El Nino and La Nina episodes | NOAA Climate Prediction Center index files | episode = the index at or beyond 0.5 in absolute value for 5 consecutive overlapping 3-month seasons | `nino`, notebook 02 |

Properties the pipeline relies on. If your data differs, change the code named.

- **One grid for all three indices.** Here it is TerraClimate's 1/24 degree
  grid. Step 0 fixes the grid from the first file and every later step asserts
  that it has not changed.
- **One calibration period for all three.** Here 1991 to 2020. The dashboard
  compares the indices side by side, which is only fair on one baseline.
- **Monthly steps, one continuous record.** Here January 1950 to December 2025,
  912 months (`PERIOD` in `pipeline/conventions.py`).
- **Sign.** SPI and SPEI are negative when dry. EDDI is positive when dry,
  because high evaporative demand is the dry side. `DRY_SIGN` in
  `pipeline/conventions.py` carries this, and no threshold is applied without it.
- **EDDI's range is narrower.** A rank-based index cannot exceed what its
  baseline length supports: with 30 years, -2.028 to +2.028. The outermost NOAA
  categories (ED4, EW4) therefore never occur, and the dashboard does not draw
  them in a legend.
- **File and variable names** are set in `pipeline/config.py`. Nothing else
  holds a path.

References for the indices: McKee, Doesken and Kleist (1993) for SPI;
Vicente-Serrano, Begueria and Lopez-Moreno (2010) for SPEI; Hobbins et al.
(2016), doi:10.1175/JHM-D-15-0121.1, for EDDI; Lukas, Hobbins, Rangwala et al.
(2017), EDDI User Guide v1.0, for the categories. These are the references the
source files themselves carry.

## 2. Software

Python with numpy, pandas, xarray, netCDF4, scipy, geopandas, shapely and
rasterio. Node 18 or later for the front end (`npm install`).

## 3. The steps

Run from the repository root, in this order. Times are from the machine this
was built on, for a window of 432 by 1,128 cells.

| Step | Command | Reads | Writes | Time |
|---|---|---|---|---|
| 0a | `python -m pipeline.step0_grid` | one index file, the three boundary files | `data/step0/`: the grid, the land mask, which cells each unit touches, a table of units | 4 min |
| 0b | `python -m pipeline.step0_boundaries` | the three boundary files | simplified outlines for the map | 5 min |
| 1 and 2 | `python -m pipeline.step1_classes` | all twelve index files, step 0 | `data/step1/`: class of every cell every month, share of each unit's area per class, each unit's mean index. `data/step2/`: every event of every unit, and per-unit summaries | 22 min |
| 3 | `python -m pipeline.step3_export` | steps 0 to 2 | `site/data/`: everything the browser loads, plus a generated list of those files | 11 min |
| 4 | `python -m pipeline.step4_hotspot` | all twelve index files, step 1's cell list | `site/data/hotspot/`: the space-time pattern of every cell every month | 30 min |
| 5 | `python -m pipeline.step5_enso` | the ENSO tables | `site/data/enso.json` | seconds |
| 6 | `python -m pipeline.step6_national` | all twelve index files, step 1's cell list | `site/data/national/`: Indonesia as one unit, with the same tables a province has | about 10 min |
| 7 | `python -m pipeline.step7_status` | all twelve index files, step 1's cell list | `site/data/status/`: where each cell stands in an event of its own, every month | about 25 min |
| site | `npm run build`, then `npm run serve` | `site/` | `dist/`, served at http://localhost:3211 | 1 min |

`python -m pytest tests -q` runs the unit tests.

`checks/` holds independent recomputations that compare each step's output with
the source cubes by another route, for example `python checks/check_step6_national.py`.
Each has its last printed result beside it as a `.txt` file.

`analysis/` holds the scripts behind the findings this document relies on (the
less reliable periods, the comparison of event definitions, the test of EDDI as
an early signal, the short-scale example, the hot spot retest), with what each
printed. They read the author's local files, with paths written at the top of
each script; change those to run them elsewhere.

## 4. Definitions

### 4.1 Which cells belong to a unit: all touched

A unit's cells are **every land cell its polygon intersects**, each counted at
its full area. This is the owner's rule. Step 0 finds the cells by exact
intersection of each cell's box with the polygon.

Consequences to keep in mind:

- A cell on a border belongs to every unit it touches, so neighbouring units
  share cells and the shares of area of adjacent units are not independent.
- A small unit can rest on very few cells. A kecamatan has a median of 12. The
  dashboard notes units with fewer than 30 cells (**proposed** threshold).
- The map draws exactly the cells the statistics use.
- **Indonesia as a whole** is every such cell, 96,429 of them, each counted
  once (`pipeline/step6_national.py`). It is not the sum of the provinces,
  which would count shared border cells more than once.

### 4.2 Classes

SPI uses the seven classes of the WMO *Standardized Precipitation Index User
Guide* (WMO-No. 1090, 2012), Table 1:

| Index value | Class |
|---|---|
| 2.0 and above | extremely wet |
| 1.5 to 1.99 | very wet |
| 1.0 to 1.49 | moderately wet |
| -0.99 to 0.99 | near normal |
| -1.0 to -1.49 | moderately dry |
| -1.5 to -1.99 | severely dry |
| -2.0 and less | extremely dry |

SPEI uses the same table (**proposed**: the guide defines it for SPI only).
EDDI uses the category stored in its own file. Classes are assigned to the
unrounded value of each cell.

### 4.3 Share of area and mean index

For each unit and month: the area of its cells in each class divided by the
area of its cells that have a value, and the area-weighted mean of the index
over those cells. Cell area is computed on the sphere from the grid.

### 4.4 Events

An event follows section 6.1 of WMO-No. 1090, which states it for SPI drought:
it **starts in the first month the index is at or beyond 1.0 on one side, and
ends when the index crosses zero**. A month exactly at zero continues the
event; a missing month ends it. (`pipeline/events.py`)

- Events are found on the **unit's mean index**, unrounded (**proposed**), not
  cell by cell.
- The wet side, SPEI and EDDI use the mirrored rule. That extension is a
  **choice**: the guide defines the rule for SPI drought only.
- For each event the pipeline stores: start, end, **duration** in months,
  **magnitude** (sum of the absolute mean index over the event's months),
  **peak** (the most extreme monthly mean) and the largest share of the unit's
  area in a class on the event's side during the event. **Intensity**, shown on
  the dashboard, is magnitude divided by duration.
- Being inside an event is not the same as being dry this month. Measured cell
  by cell on SPI, 28% to 35% of all months fall inside a dry event under this
  rule, depending on the scale, since an event lasts until the index recovers
  to zero.
- Duration depends on the rule as much as on the climate. Measured cell by cell
  on SPI-3, the same record gives a mean dry event of 2.8 months under a plain
  threshold run and 6.7 months under this rule.

### 4.5 Less reliable periods

Two flags, both from comparisons made for this project against rain gauges and
a second rainfall product. Flagged months stay in the record and are drawn
washed out.

- **Before 1970, everywhere.** At gauge sites the gridded rainfall of the 1950s
  and 1960s reads low against the gauges, so the early record looks drier than
  it was.
- **Before 1984, in northern and central Sumatra and West Kalimantan.** The
  monthly inputs step at January 1984 there. The flag runs to December 1983
  plus (scale - 1) months, since an n-month index still contains pre-1984
  months for that long. A unit carries the flag when more than half its cell
  area does (**proposed** threshold).

### 4.6 Space-time pattern: emerging hot spot analysis

`pipeline/hotspot.py`. For each month, the cube is the 12 months ending in that
month (**proposed** window), on the cells of 4.1, holding the index with its
sign turned so that positive is dry.

1. **Getis-Ord Gi\*** for every cell and month. The neighbourhood is the 3 by 3
   block of cells, in that month and the month before (**choice** for the
   block; one step back in time is Esri's default).
2. A cell-month is a hot spot (dry side) or a cold spot (wet side) at 90%
   confidence, after a Benjamini-Hochberg correction over the whole cube
   (**choice** of procedure).
3. **Mann-Kendall** on each cell's 12 Gi\* scores gives the trend, at 90%.
4. The 17 categories (new, consecutive, intensifying, persistent, diminishing,
   sporadic, oscillating and historical, for each side, and no pattern) follow
   Esri's definitions: "How Emerging Hot Spot Analysis works", ArcGIS Pro
   documentation, read 2026-11-21.

Where this departs from Esri's tool, and what to know before using it:

- **Reference.** Esri's tool measures each neighbourhood against the mean of
  the cube itself. Here it is measured against climatology, mean 0 and standard
  deviation 1, which is what a standardised index has over its baseline
  (**choice**). Against the cube's own mean, a near-normal place in a dry year
  was classed as a cold spot.
- **Window.** With 24 months or more, most cells have been both hot and cold
  inside the window and fall into "oscillating". On SPI-3, 14.7 of 17
  categories are populated on average with 12 months, 8.4 with 36.
- **Significance is overstated.** The test treats the 18 values of a
  neighbourhood as independent. Neighbouring cells of an interpolated field are
  not, so about two thirds of cells are in a cluster in a typical month. Read a
  cluster as "this neighbourhood is on the dry (or wet) side of normal", not as
  a rare event.
- It describes the 12 months up to the month shown. It is not a forecast.

### 4.7 Where a cell stands in an event: how long, and status

`pipeline/status.py` and `pipeline/step7_status.py`. The event rule of 4.4 is
applied to **each cell's own index** (4.4 applies it to a unit's mean, so a
cell's event is not its unit's event). For every cell and month the map can
then show:

- **How long**: the months the running event has lasted so far, in bins of 1
  to 2, 3 to 5, 6 to 11, 12 to 23, and 24 or more.
- **Status**, one of five states for each side:

| State | Rule |
|---|---|
| new | first or second month of the event |
| deepening | third month on, at or beyond the onset level (1.0), and further from zero than a month before |
| persisting | third month on, at or beyond the onset level, not further from zero than a month before |
| easing | third month on, back inside the onset level, not yet across zero |
| ended | the event stopped this month |

The five states and the bins are this project's own (**proposed**). They are a
plain-rule alternative to 4.6 for the same questions: is it new, is it
lasting, is it getting worse. They describe the record up to the month shown.

### 4.8 Trend

For the selected unit, in the page: the index is averaged by calendar year over
the years outside the less reliable periods (4.5), and the trend of those
annual values is given as a Theil-Sen slope per decade with a Mann-Kendall
test. Annual values are used because monthly values of an accumulated index
overlap. A significant trend says nothing about its cause: part of an EDDI
trend is warming, and for rainfall the earlier decades are less certain than
the recent ones (6).

### 4.9 El Nino and La Nina

`pipeline/step5_enso.py` copies the Relative Oceanic Nino Index (RONI) and its
episode list onto the dashboard's months: 22 El Nino and 22 La Nina episodes in
1950 to 2025. A month's phase is the episode it falls in, otherwise neutral.

The dashboard then reports, for a unit: its mean index by calendar month in
each phase; for each episode, its driest and wettest month and how many months
reached the event onset level; and, across units, the mean over El Nino months
minus the mean over La Nina months. Months in a less reliable period (4.5) are
left out. These are counts and differences from the record, with no test of
significance: there are few episodes, and both series are strongly correlated
from one month to the next.

## 5. What reaches the browser

The browser never reads an index cube. It loads: one class code per cell and
month, in files by decade; per unit and month, the share of area per class and
the mean index; per unit, its events and a summary; and lookups from cell to
unit so that a click on the map and the tables use the same assignment.
Kabupaten and kecamatan tables are bundled by province and loaded when a
province is opened.

## 6. Known limits

- The record is not homogeneous in time (4.5). Nothing here establishes whether
  the wetter recent decades in the indices are a real trend, a change in the
  inputs, or both.
- Boundaries are present-day and are applied to every year back to 1950.
- All-touched assignment shares border cells between neighbours (4.1).
- Short accumulation periods have little range in a season that is normally
  almost dry: a rainless month in the dry season can read as near normal on
  SPI-1 or SPI-3 while SPI-6 shows the deficit. The dashboard shows all four
  periods together for this reason.
- EDDI in this data mostly restates the same month's rainfall (median
  correlation with SPI-1 of -0.73 across cells). It is shown as the demand
  view, not as an early warning.
- Several thresholds are still proposed, as marked above.
