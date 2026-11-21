# Exploring dry and wet conditions in Indonesia

An interactive dashboard of dry and wet conditions across Indonesia, month by
month from January 1950 to December 2025, for every province, kabupaten or
kota, and kecamatan.

## What the dashboard can tell you

For any province, kabupaten or kota, or kecamatan, and for Indonesia as a whole:

- **How much of the area is dry or wet right now**, and how that month ranks
  against the same month in earlier years.
- **How long the current dry or wet event has lasted**, and whether it is still
  deepening, holding, or easing.
- **How long droughts lasted here in the past, and which were the worst**: every
  event since 1950 with its duration, magnitude and peak.
- **Where inside the area it is worst**: the kabupaten or kecamatan ranked for
  the month you are looking at.
- **What El Niño and La Niña years have looked like here**, month by month and
  episode by episode.
- **Whether the cause is lack of rain or high evaporative demand**, by switching
  between the rainfall, water balance and demand indices.
- **Whether conditions have been trending drier or wetter** over the decades.

It describes the record up to December 2025. It is not a forecast.

![The dashboard: controls, map and legend](docs/img/dashboard.png)

<!-- Figure: a screenshot of the top of the main page (controls and map), saved as docs/img/dashboard.png -->

## What it can do

Live at https://bennyistanto.github.io/drywet-explorer/

**Choose what to look at.** Five controls sit above the map. Each has a small
"i" button that explains it.

| Control | Choices | What it sets |
|---|---|---|
| Index | Rainfall (SPI), Water balance (SPEI), Evaporative demand (EDDI) | which side of the water balance is measured |
| Accumulated over | 1, 3, 6 or 12 months | how many months the index looks back over |
| Conditions | Dry and wet, Dry only, Wet only | which side is drawn in colour |
| Map shows | This month, How long, Status, Pattern | what each grid cell is coloured by, and what the page under the map is about |
| Place and month | province, kabupaten or kota, kecamatan; January 1950 to December 2025 | where and when |

The three indices are standardised against 1991 to 2020 and computed on
TerraClimate:

| Index | Measures | Dry side |
|---|---|---|
| SPI | rainfall | negative |
| SPEI | rainfall minus evaporative demand | negative |
| EDDI | evaporative demand | positive |

**Drill down on the map.** Click a province, then a kabupaten or kota inside
it, then a kecamatan. With nothing chosen the figures are for Indonesia as a
whole. Click any chart with a time axis to move the map to that month.

**Read the story under the map.** Every section follows the "Map shows"
choice:

| Map shows | Each cell is coloured by | The page under the map tells you |
|---|---|---|
| **This month** | the class of the index, from extremely dry to extremely wet | how much of the place is in each class; whether the place as a whole is in a dry or wet event and for how long; every past event with its duration, magnitude, intensity and peak; the trend of the index |
| **How long** | the months the dry or wet event running in that cell has lasted | how much of the place is in an event and how much has been for 6 months or more; when long-running events covered more than half of it |
| **Status** | what that event is doing: new, deepening, persisting, easing, ended | how much of the place is in an event and how much of it is still deepening; whether conditions are setting in or letting up |
| **Pattern** | the space-time pattern of the last 12 months (emerging hot spot analysis): new, consecutive, persistent, intensifying, diminishing, sporadic, oscillating | how much of the place sits in a dry or wet cluster, and how much of that is new |

Whatever the choice, the page gives, for the selected place:

- four headline figures and a written summary built from the data, with the
  measured values set in colour;
- the places inside it, ranked;
- the share of area over time, for a span of years you choose;
- the long-term trend, on the years the record can be trusted;
- the past: events (This month) or spells (the other three);
- **El Nino and La Nina**: the state of the Pacific that month, what the place
  has averaged in each phase by calendar month, every episode since 1970, and
  where the two phases differ most.

## Read this before trusting a number

- Months before 1970, and before 1984 in parts of Sumatra and Kalimantan, are
  less reliable and are drawn washed out.
- A small unit rests on few grid cells, and border cells are shared between
  neighbours.
- An event is not the same as being dry this month.
- An event of a large area is an event of its average. It does not mean every
  place inside stayed dry or wet, or that the same places did. Use "How long"
  or "Status" to see what each place did.

[docs/method.md](docs/method.md) gives every definition, the inputs you need to
reproduce this with your own data, and the known limits.

## Run it

The index cubes are not in this repository. Set their paths in
`pipeline/config.py`, then:

```
python -m pipeline.step0_grid
python -m pipeline.step0_boundaries
python -m pipeline.step1_classes
python -m pipeline.step3_export
python -m pipeline.step4_hotspot
python -m pipeline.step5_enso
python -m pipeline.step6_national
python -m pipeline.step7_status
python -m pipeline.step8_members
npm install
npm run build
npm run serve
```

and open http://localhost:3211. `python -m pytest tests -q` runs the tests.

`npm run deploy` publishes the built site to the `gh-pages` branch; see the
notes at the top of `tools/deploy.ps1`.

## Built with

Python for the pipeline and [Observable Framework](https://observablehq.com/framework/)
for the page. The indices were computed with
[`precip-index`](https://github.com/bennyistanto/precip-index) (SPI, SPEI) and
[`nino`](https://github.com/bennyistanto/nino) (EDDI, ENSO tables).

## Data

TerraClimate v1.1 for the monthly climate fields. Administrative boundaries
from Badan Informasi Geospasial. ENSO indices from the NOAA Climate Prediction
Center.

## Author

Developed by [Benny Istanto](https://benny.istan.to) as a casual weekend
project.

## License

See [LICENSE](LICENSE).
