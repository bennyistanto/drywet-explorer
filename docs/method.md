# Method

How the dashboard's numbers are made, written so that someone holding the same
kind of data can prepare it and run the pipeline. Each statement here is either
read from the source files' own attributes, computed by a named script in this
repository, or cited. Choices that are this project's own, and not a published
standard, are marked **choice**. Choices still awaiting confirmation are marked
**proposed**.

Contents: [1 Inputs](#1-what-you-need-before-you-start) ·
[2 Software](#2-software) · [3 Steps](#3-the-steps) ·
[4 Definitions](#4-definitions) · [5 What reaches the browser](#5-what-reaches-the-browser) ·
[6 Known limits](#6-known-limits) · [7 Symbols](#7-symbols)

## 1. What you need before you start

The pipeline does not compute the indices. It starts from index cubes that
already exist, and reduces them to small files a browser can load.

| Input | What it is | Derived from | How | Made with |
|---|---|---|---|---|
| SPI at 1, 3, 6, 12 months | Standardized Precipitation Index | monthly precipitation | n-month running total, fitted with a Gamma distribution over the calibration years, converted to a standard normal score, limited to -3.09 to +3.09 | [`precip-index`](https://github.com/bennyistanto/precip-index) |
| SPEI at 1, 3, 6, 12 months | Standardized Precipitation Evapotranspiration Index | monthly precipitation minus monthly reference evapotranspiration | n-month running total of the difference, fitted with a Pearson type III distribution, same conversion and limits | `precip-index` |
| EDDI at 1, 3, 6, 12 months | Evaporative Demand Drought Index | monthly reference evapotranspiration | trailing n-month sum, ranked per calendar month against the baseline years, turned into a probability with the Tukey plotting position, then into a z-score with the inverse normal | [`nino`](https://github.com/bennyistanto/nino), notebook 01 |
| EDDI category | NOAA class of each EDDI value | EDDI percentile | percentile bounds 0, 2, 5, 10, 20, 30, 70, 80, 90, 95, 98 give EW4 to EW0, Normal, ED0 to ED4 | stored in the EDDI file as `eddi_cat` |
| Admin boundaries, levels 1 to 3 | provinces, kabupaten and kota, kecamatan | national boundary shapefiles | used as they are; codes are read by `pipeline/admin_codes.py` | not made here |
| ENSO tables | RONI and ONI by month, and a list of El Nino and La Nina episodes | NOAA Climate Prediction Center index files | episode = the index at or beyond 0.5 in absolute value for 5 consecutive overlapping 3-month seasons | `nino`, notebook 02 |

### 1.1 The indices, in symbols

Let $P(t)$ be precipitation and $E(t)$ reference evapotranspiration in month
$t$, and $n$ the accumulation period in months (1, 3, 6 or 12).

Accumulation, the same for all three:

$$X_n(t) = \sum_{k=0}^{n-1} x(t-k), \qquad x = P \ \text{(SPI)}, \quad x = P - E \ \text{(SPEI)}, \quad x = E \ \text{(EDDI)}$$

**SPI and SPEI.** For each cell and each calendar month $m$, a distribution
$F_m$ is fitted to the values of $X_n$ in that calendar month over the
calibration years 1991 to 2020: Gamma for SPI, Pearson type III for SPEI. The
index is the standard normal score of the fitted probability:

$$Z(t) = \Phi^{-1}\big(F_{m(t)}(X_n(t))\big), \qquad -3.09 \le Z \le 3.09$$

where $\Phi$ is the standard normal distribution function. The fitting itself,
including how months with no rain are treated, is done by `precip-index` and is
documented there.

**EDDI.** No distribution is fitted. $X_n(t)$ is ranked against the $k = 30$
baseline values of the same calendar month, giving rank $i$ from 1 (lowest) to
$k + 1$, and

$$p = \frac{i - 1/3}{k + 1 + 1/3}, \qquad \mathrm{EDDI}(t) = \Phi^{-1}(p), \qquad \text{percentile} = 100\,\Phi(\mathrm{EDDI})$$

With $k = 30$ the largest possible value is
$\Phi^{-1}\big((31 - 1/3)/(31 + 1/3)\big) = 2.028$, which is why EDDI here never
leaves $\pm 2.028$ and its outermost categories never occur. These formulas are
the ones recorded in the EDDI files' own attributes.

### 1.2 Properties the pipeline relies on

If your data differs, change the code named.

- **One grid for all three indices.** Here it is TerraClimate's 1/24 degree
  grid. Step 0 fixes the grid from the first file and every later step asserts
  that it has not changed.
- **One calibration period for all three.** Here 1991 to 2020. The dashboard
  compares the indices side by side, which is only fair on one baseline.
- **Monthly steps, one continuous record.** Here January 1950 to December 2025,
  912 months (`PERIOD` in `pipeline/conventions.py`).
- **Sign.** SPI and SPEI are negative when dry. EDDI is positive when dry,
  because high evaporative demand is the dry side. The pipeline carries a sign
  $\sigma$ per index (`DRY_SIGN`: $-1$ for SPI and SPEI, $+1$ for EDDI) and
  works with the **dryness** $d = \sigma Z$, which is positive on the dry side
  for every index. No threshold is applied without it.
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
| 8 | `python -m pipeline.step8_members` | step 0, step 1's cell list | `site/data/members/`: the list of cells of every unit, for the page's mode view | seconds |
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
intersection of each cell's box with the polygon. Write $C_u$ for the set of
cells of unit $u$.

The area of a cell between latitudes $\varphi_1 < \varphi_2$ and of width
$\Delta\lambda$ in longitude, on a sphere of radius $R$:

$$a = R^2 \,\Delta\lambda\, (\sin\varphi_2 - \sin\varphi_1)$$

with angles in radians. On this grid a cell is about 21 square kilometres.

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

| Index value $Z$ | Class |
|---|---|
| $Z \ge 2.0$ | extremely wet |
| $1.5 \le Z < 2.0$ | very wet |
| $1.0 \le Z < 1.5$ | moderately wet |
| $-1.0 < Z < 1.0$ | near normal |
| $-1.5 < Z \le -1.0$ | moderately dry |
| $-2.0 < Z \le -1.5$ | severely dry |
| $Z \le -2.0$ | extremely dry |

The table is closed toward the extremes: exactly $-1.0$ is moderately dry and
exactly $+1.0$ moderately wet (`classify_spi` in `pipeline/conventions.py`).
SPEI uses the same table (**proposed**: the guide defines it for SPI only).
EDDI uses the category stored in its own file, defined on the percentile:

| EDDI percentile | Category | On the dashboard |
|---|---|---|
| 98 to 100 | ED4 | never occurs with a 30-year baseline |
| 95 to 98 | ED3 | high demand |
| 90 to 95 | ED2 | high demand |
| 80 to 90 | ED1 | high demand |
| 70 to 80 | ED0 | high demand |
| 30 to 70 | Normal | normal demand |
| 20 to 30, 10 to 20, 5 to 10, 2 to 5 | EW0 to EW3 | low demand |
| 0 to 2 | EW4 | never occurs with a 30-year baseline |

Classes are assigned to the unrounded value of each cell.

### 4.3 Share of area and mean index

For unit $u$ and month $t$, let $V_u(t) \subseteq C_u$ be the cells with a
value. The share of the unit's area in class $c$ and the unit's mean index are

$$s_{u,c}(t) = \frac{\sum_{i \in V_u(t),\ \mathrm{class}_i(t) = c} a_i}{\sum_{i \in V_u(t)} a_i}, \qquad \bar{Z}_u(t) = \frac{\sum_{i \in V_u(t)} a_i\, Z_i(t)}{\sum_{i \in V_u(t)} a_i}$$

The share on the dry side is the sum of $s_{u,c}$ over the dry classes, taken
before rounding. Stored values are rounded once: shares to 1/10,000 for
provinces and kabupaten and to 1/200 for kecamatan, means to 0.001 and 0.01.

### 4.4 Events

An event follows section 6.1 of WMO-No. 1090, which states it for SPI drought.
It is found on the **unit's mean**, as dryness
$d(t) = \sigma\,\bar{Z}_u(t)$ for a dry event and $d(t) = -\sigma\,\bar{Z}_u(t)$
for a wet one (`pipeline/events.py`):

$$\text{start } t_s:\ d(t_s) \ge 1 \text{ with no event running}; \qquad \text{end } t_e:\ \text{the last month before } d < 0 \text{ or a missing value}$$

A month exactly at zero continues the event. For an event from $t_s$ to $t_e$:

$$D = t_e - t_s + 1, \qquad M = \sum_{t = t_s}^{t_e} d(t), \qquad I = \frac{M}{D}, \qquad \text{peak} = \max_{t_s \le t \le t_e} d(t)$$

duration in months, magnitude in index-months, intensity, and peak. The
pipeline also stores the largest share of the unit's area in a class on the
event's side during the event.

- Finding events on the unit's mean, unrounded, is **proposed**. The
  alternative, cell by cell, is what 4.7 does for the map.
- The wet side, SPEI and EDDI use the mirrored rule. That extension is a
  **choice**: the guide defines the rule for SPI drought only.
- **An event of the mean is not persistence at each place.** The mean of a
  large area can stay slightly on one side for a long time while dry and wet
  patches come and go inside it. Measured for Indonesia on SPI-3
  (`analysis/national_event_vs_cells.py`): the national mean stayed on the wet
  side for the 19 months from June 2024 to December 2025, yet only 8% of the
  area was in a wet event of its own throughout, no cell was in a wet class in
  every month, and 45% of the area was in a dry class in at least one of them.
  The dashboard therefore words such an event as the average staying on one
  side, and gives beside it the share of the area in an event of its own (4.7).
  Any share of area is for one month: it is not the same area from month to
  month.
- Being inside an event is not the same as being dry this month. Measured cell
  by cell on SPI, 28% to 35% of all months fall inside a dry event under this
  rule, depending on the scale, since an event lasts until the index recovers
  to zero.
- Duration depends on the rule as much as on the climate. Measured cell by cell
  on SPI-3, the same record gives a mean dry event of 2.8 months under a plain
  threshold run and 6.7 months under this rule
  (`analysis/event_definition_compare.py`).

### 4.5 Less reliable periods

Two flags, both from comparisons made for this project against rain gauges and
a second rainfall product (`analysis/gauges_vs_terraclimate.py`,
`analysis/chirps_vs_terraclimate_step.py`, `analysis/step1984_region.py`).
Flagged months stay in the record and are drawn washed out.

- **Before 1970, everywhere.** At gauge sites the gridded rainfall of the 1950s
  and 1960s reads low against the gauges, so the early record looks drier than
  it was.
- **Before 1984, in northern and central Sumatra and West Kalimantan.** The
  monthly inputs step at January 1984 there. For an index of $n$ months the
  flag runs to December 1983 plus $n - 1$ months, since the index still
  contains pre-1984 months for that long. A unit carries the flag when more
  than half its cell area does (**proposed** threshold).

Comparisons across years on the dashboard (rank in the calendar month, trend,
El Nino and La Nina) use only months after a unit's flagged period.

### 4.6 Space-time pattern: emerging hot spot analysis

`pipeline/hotspot.py`. For each month $t$ the cube is the $T = 12$ months
ending in $t$ (**proposed** window), on the cells of 4.1, holding the dryness
$d_i(\tau) = \sigma Z_i(\tau)$, so that a hot spot is a dry cluster and a cold
spot a wet one.

**1. Getis-Ord Gi\*.** The neighbourhood $N_i(\tau)$ of a cell-month is the 3 by
3 block of cells around $i$ in month $\tau$ and in month $\tau - 1$ (**choice**
for the block; one step back in time is Esri's default), with $w$ the number of
those cell-months that have a value. Getis and Ord's statistic with binary
weights is

$$G_i^*(\tau) = \frac{\sum_{j \in N_i(\tau)} d_j - \bar{X}\, w}{S \sqrt{\dfrac{n\,w - w^2}{n - 1}}}$$

where $\bar{X}$ and $S$ are the mean and standard deviation of a reference
population of size $n$. Esri's tool takes the cube itself as the reference.
Here the reference is the baseline climate, for which a standardised index has
$\bar{X} = 0$ and $S = 1$, and $n$ is large, so that

$$G_i^*(\tau) = \frac{\sum_{j \in N_i(\tau)} d_j}{\sqrt{w}}$$

(**choice**; `REFERENCE` in `pipeline/hotspot.py` switches between the two).

**2. Significance.** A two-sided p-value $p = 2\,(1 - \Phi(|G^*|))$ for every
cell-month of the cube, then the Benjamini-Hochberg correction over all $m$ of
them at $\alpha = 0.10$: with the p-values sorted, $p_{(1)} \le \dots \le p_{(m)}$,
those up to the largest $k$ with

$$p_{(k)} \le \frac{k}{m}\,\alpha$$

are significant (**choice** of procedure; Esri's pages say a correction is
used and do not describe it). A significant cell-month is a hot spot if
$G^* > 0$ and a cold spot if $G^* < 0$.

**3. Trend.** Mann-Kendall on each cell's $T$ values of $G^*$:

$$S_{MK} = \sum_{a < b} \operatorname{sgn}\big(G^*(\tau_b) - G^*(\tau_a)\big), \qquad \operatorname{Var} = \frac{T(T-1)(2T+5)}{18}, \qquad z_{MK} = \frac{S_{MK} \mp 1}{\sqrt{\operatorname{Var}}}$$

(minus for $S_{MK} > 0$, plus for $S_{MK} < 0$, and $z_{MK} = 0$ when
$S_{MK} = 0$). A trend counts at $|z_{MK}| \ge 1.645$, 90% (**choice** of level).

**4. Categories**, from Esri's "How Emerging Hot Spot Analysis works" (ArcGIS
Pro documentation, read 2026-11-21). Let $h$ be the number of the $T$ months in
which the cell is a hot spot. Cold spots mirror these.

| Category | Rule |
|---|---|
| New | hot in the final month and never before |
| Consecutive | one unbroken run of hot months ending in the final month, at least 2 long, never hot before it, $h < 0.9\,T$ |
| Intensifying | $h \ge 0.9\,T$, hot in the final month, trend up |
| Persistent | $h \ge 0.9\,T$, hot in the final month, no trend |
| Diminishing | $h \ge 0.9\,T$, hot in the final month, trend down |
| Sporadic | hot in the final month, $h < 0.9\,T$, on and off, never a cold spot |
| Oscillating | hot in the final month, $h < 0.9\,T$, a cold spot in some earlier month |
| Historical | not hot in the final month, $h \ge 0.9\,T$ |
| No pattern | none of the above, on either side |

Where a cell meets two rules, New and Consecutive are taken first, then the 90%
categories, then Oscillating, then Sporadic (**choice**; the source does not
state an order).

What to know before using it:

- **Window.** With 24 months or more, most cells have been both hot and cold
  inside the window and fall into "oscillating". On SPI-3, 14.7 of 17
  categories are populated on average with 12 months, 8.4 with 36
  (`analysis/ehsa_retest.py`).
- **Reference.** Against the cube's own mean, a near-normal place in a dry year
  was classed as a cold spot, which is why the baseline climate is used.
- **Significance is overstated.** The test treats the 18 values of a
  neighbourhood as independent. Neighbouring cells of an interpolated field are
  not, so about two thirds of cells are in a cluster in a typical month. Read a
  cluster as "this neighbourhood is on the dry (or wet) side of normal", not as
  a rare event.
- It describes the 12 months up to the month shown. It is not a forecast.

### 4.7 Where a cell stands in an event: how long, and status

`pipeline/status.py` and `pipeline/step7_status.py`. The event rule of 4.4 is
applied to **each cell's own dryness** $d_i(t)$ (4.4 applies it to a unit's
mean, so a cell's event is not its unit's event). Let $L_i(t)$ be the number of
months the event running in cell $i$ has lasted at month $t$, and 0 when none
is running:

$$L_i(t) = \begin{cases} L_i(t-1) + 1 & \text{if } L_i(t-1) > 0 \text{ and } d_i(t) \ge 0 \\ 1 & \text{if } L_i(t-1) = 0 \text{ and } d_i(t) \ge 1 \\ 0 & \text{otherwise} \end{cases}$$

(an event that ends in a month cannot start again in that same month). The map
then shows, for each side:

- **How long**: $L_i(t)$ in bins of 1 to 2, 3 to 5, 6 to 11, 12 to 23, and 24
  or more months.
- **Status**:

| State | Rule |
|---|---|
| new | $1 \le L_i(t) \le 2$ |
| deepening | $L_i(t) \ge 3$, $d_i(t) \ge 1$ and $d_i(t) > d_i(t-1)$ |
| persisting | $L_i(t) \ge 3$, $d_i(t) \ge 1$ and $d_i(t) \le d_i(t-1)$ |
| easing | $L_i(t) \ge 3$ and $0 \le d_i(t) < 1$ |
| ended | $L_i(t-1) > 0$ and $L_i(t) = 0$ |

The five states and the bins are this project's own (**proposed**). They are a
plain-rule alternative to 4.6 for the same questions: is it new, is it
lasting, is it getting worse. They describe the record up to the month shown.

### 4.8 What the page shows for each map mode

With "This month", every section under the map is about the classes and about
the events of the selected area as a whole (4.2 to 4.4). With "How long",
"Status" or "Pattern", every section is about that mode instead.

For a set of states $K$ (for example, every state of a running dry event), the
figure for unit $u$ is the share of its cell area in $K$:

$$q_{u,K}(t) = \frac{\sum_{i \in C_u,\ \mathrm{state}_i(t) \in K} a_i}{\sum_{i \in C_u,\ \mathrm{state}_i(t)\ \text{known}} a_i}$$

The page works this out itself, from the per-cell maps and a list of each
unit's cells written by `pipeline/step8_members.py`, which is the same
membership the pipeline uses.

- **Headline figures**: $q$ for a running dry event or dry cluster, for a wet
  one, and for the "strong" part of each: 6 months or more (How long),
  deepening (Status), new or consecutive (Pattern).
- **Spell**: a run of consecutive months with $q_{u,K}(t) > 0.5$ on one side
  (**proposed** level). Spells take the place of events in this view.
- The trend and the El Nino and La Nina comparison are made on $q$, with the
  rules of 4.9 and 4.10.

`checks/check_mode_view.py` computes the headline figures by another route; the
page matched it on all 36 figures compared (`checks/check_mode_view.txt`). The
series over time in this view were not checked month by month.

### 4.9 Trend

For the selected unit, in the page. Let $y_j$ be the mean of the twelve monthly
values of year $Y_j$ (the mean index in the class view, the share $q$ in a mode
view), over the years outside the less reliable periods (4.5). Annual values
are used because monthly values of an accumulated index overlap.

The slope is the Theil-Sen estimate, the median of the slopes between every
pair of years, shown per decade:

$$\beta = \operatorname{median}_{j < k}\ \frac{y_k - y_j}{Y_k - Y_j}$$

and its significance is the Mann-Kendall test of 4.6 on the $y_j$, with a
two-sided p-value. A significant trend says nothing about its cause: part of an
EDDI trend is warming, and for rainfall the earlier decades are less certain
than the recent ones (6).

### 4.10 El Nino and La Nina

`pipeline/step5_enso.py` copies the Relative Oceanic Nino Index (RONI) and its
episode list onto the dashboard's months: 22 El Nino and 22 La Nina episodes in
1950 to 2025. A month's phase is the episode it falls in, otherwise neutral.

With $y(t)$ the unit's value (mean index, or share $q$) and $\mathcal{T}_{m,\phi}$
the months of calendar month $m$ in phase $\phi$ outside the less reliable
periods, the dashboard reports

$$\bar{y}_{m,\phi} = \frac{1}{|\mathcal{T}_{m,\phi}|} \sum_{t \in \mathcal{T}_{m,\phi}} y(t), \qquad \Delta_u = \bar{y}_{\text{El Niño}} - \bar{y}_{\text{La Niña}}$$

the mean by calendar month and phase, and, across units, the difference of the
means over all El Nino and all La Nina months (for an index, multiplied by
$\sigma$ so that positive means drier in El Nino). For each episode it also
gives the unit's most extreme months and how many months reached the event
onset level, or one half of the area in a mode view.

These are counts and differences from the record, with no test of
significance: there are few episodes, and both series are strongly correlated
from one month to the next.

## 5. What reaches the browser

The browser never reads an index cube. It loads: one class code per cell and
month, in files by decade; per unit and month, the share of area per class and
the mean index; per unit, its events and a summary; and lookups from cell to
unit so that a click on the map and the tables use the same assignment.
Kabupaten and kecamatan tables are bundled by province and loaded when a
province is opened.

For the map modes it also loads one code per cell and month for the pattern
(4.6) and one for status and duration together (4.7), and the list of cells of
each unit. The mode view (4.8) is the one place where the page sums over cells
itself: storing those sums for 7,298 kecamatan and 912 months would not fit.

## 6. Known limits

- The record is not homogeneous in time (4.5). Nothing here establishes whether
  the wetter recent decades in the indices are a real trend, a change in the
  inputs, or both.
- Boundaries are present-day and are applied to every year back to 1950.
- All-touched assignment shares border cells between neighbours (4.1).
- Short accumulation periods have little range in a season that is normally
  almost dry: a rainless month in the dry season can read as near normal on
  SPI-1 or SPI-3 while SPI-6 shows the deficit (`analysis/indramayu_1997.py`).
  The dashboard shows all four periods together for this reason.
- EDDI in this data mostly restates the same month's rainfall (median
  correlation with SPI-1 of -0.73 across cells, `analysis/eddi_early_signal.py`).
  It is shown as the demand view, not as an early warning.
- Cluster significance in the pattern mode is overstated (4.6).
- Several thresholds are still proposed, as marked above.

## 7. Symbols

| Symbol | Meaning |
|---|---|
| $t$, $\tau$ | month |
| $n$ | accumulation period in months |
| $Z$ | index value (SPI, SPEI or EDDI) |
| $\sigma$ | sign that turns an index into dryness: $-1$ for SPI and SPEI, $+1$ for EDDI |
| $d = \sigma Z$ | dryness, positive on the dry side |
| $\Phi$ | standard normal distribution function |
| $a_i$ | area of cell $i$ |
| $C_u$, $V_u(t)$ | cells of unit $u$; those of them with a value in month $t$ |
| $s_{u,c}$, $\bar{Z}_u$ | share of the unit's area in class $c$; the unit's mean index |
| $D$, $M$, $I$ | duration, magnitude and intensity of an event |
| $G^*$ | Getis-Ord statistic of a cell-month |
| $T$, $h$ | months in the pattern window; how many of them the cell is a hot spot |
| $L_i(t)$ | months the event running in cell $i$ has lasted |
| $q_{u,K}$ | share of the unit's cell area in the set of states $K$ |
| $\beta$ | Theil-Sen slope |
