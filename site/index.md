---
title: Exploring dry and wet conditions in Indonesia
---

<style>
/* ---------- page ---------- */
.page-head {margin: 0.5rem 0 1.25rem;}
.page-head h1 {margin: 0 0 0.4rem; font-size: 2rem; line-height: 1.15; max-width: none;}
.lede {margin: 0; max-width: none; color: #52514e; font-size: 1rem; line-height: 1.5;}
h2 {margin-top: 2rem;}

/* ---------- control panel: what, where, when ---------- */
.panel {background: var(--theme-background-alt, #fff); border: 1px solid #e1e0d9; border-radius: 12px; padding: 1.1rem 1.25rem; margin: 0 0 1.25rem; display: grid; gap: 1rem;}
.panel-row {display: grid; gap: 1rem 1.5rem; align-items: end;}
.panel-row.what {display: flex; flex-wrap: wrap; align-items: flex-end; gap: 1rem 1.75rem;}
.panel-row.where {grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); padding-top: 1rem; border-top: 1px solid #e1e0d9;}
.panel-row.crumb-row {display: block;}
.panel-row.when {grid-template-columns: auto auto minmax(200px, 1fr); align-items: center; padding-top: 1rem; border-top: 1px solid #e1e0d9;}
/* Inputs lays a form out as a label beside a control, with fixed widths. Here: label above, full width. */
.panel form {display: block; margin: 0; width: auto; max-width: none; min-height: 0; --label-width: auto; --input-width: 100%;}
.panel form > label {display: block; width: auto; margin: 0 0 0.35rem; padding: 0; font-size: 0.72rem; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; color: #52514e;}
/* radios as a segmented control: the circle is hidden, the label is the button */
.panel form > div {display: flex; flex-wrap: nowrap; gap: 0; width: auto;}
.panel form > div > label {position: relative; display: inline-flex; align-items: center; margin: 0; padding: 0.4rem 0.8rem; border: 1px solid #c3c2b7; border-left-width: 0; background: #fcfcfb; color: #0b0b0b; font-size: 0.9rem; line-height: 1.2; cursor: pointer; white-space: nowrap; user-select: none;}
.panel form > div > label:first-child {border-left-width: 1px; border-radius: 8px 0 0 8px;}
.panel form > div > label:last-child {border-radius: 0 8px 8px 0;}
.panel form > div > label > input[type=radio] {position: absolute; opacity: 0; width: 1px; height: 1px; margin: 0; pointer-events: none;}
.panel form > div > label:hover {background: #f0efec;}
.panel form > div > label:has(input:checked) {background: #0b0b0b; border-color: #0b0b0b; color: #fff;}
.panel form > div > label:has(input:focus-visible) {outline: 2px solid #2a78d6; outline-offset: 2px; z-index: 1;}
.panel select {width: 100%; max-width: none; padding: 0.42rem 0.6rem; font: inherit; font-size: 0.9rem; color: #0b0b0b; background: #fcfcfb; border: 1px solid #c3c2b7; border-radius: 8px;}
.panel select:disabled {color: #898781; background: #f0efec;}
.panel select:focus-visible {outline: 2px solid #2a78d6; outline-offset: 2px;}
.crumbs {display: flex; flex-wrap: wrap; align-items: baseline; gap: 0.4rem; margin: 0; font-size: 0.95rem;}
.crumbs a {text-decoration: underline;}
.crumb-sep {color: #898781;}
.crumb-hint {margin-left: 0.6rem;}
/* The label has a fixed width, wide enough for "September 2025", so the buttons and the slider stay put
   when the month name changes length. */
.month-label {font-size: 1.35rem; font-weight: 600; width: 9.6rem; white-space: nowrap;}
/* The slider marks ONE month, so its track is plain on both sides of the handle: a filled track would read
   as a selected period from 1950 to the handle. */
.month-slider {display: flex; align-items: center;}
.month-slider input[type=range] {-webkit-appearance: none; appearance: none; width: 100%; height: 4px; margin: 0; padding: 0; background: #c3c2b7; border-radius: 2px; cursor: pointer;}
.month-slider input[type=range]::-webkit-slider-runnable-track {height: 4px; background: transparent;}
.month-slider input[type=range]::-moz-range-track {height: 4px; background: #c3c2b7; border-radius: 2px;}
.month-slider input[type=range]::-moz-range-progress {background: transparent;}
.month-slider input[type=range]::-webkit-slider-thumb {-webkit-appearance: none; appearance: none; width: 16px; height: 16px; margin-top: -6px; border-radius: 50%; background: #0b0b0b; border: 2px solid #fcfcfb; box-shadow: 0 0 0 1px #0b0b0b;}
.month-slider input[type=range]::-moz-range-thumb {width: 12px; height: 12px; border-radius: 50%; background: #0b0b0b; border: 2px solid #fcfcfb; box-shadow: 0 0 0 1px #0b0b0b;}
.month-slider input[type=range]:focus-visible {outline: 2px solid #2a78d6; outline-offset: 6px;}
.steps {display: inline-flex;}
.steps .step {font: inherit; font-size: 1rem; line-height: 1; min-width: 2.1rem; padding: 0.35rem 0.5rem; border: 1px solid #c3c2b7; border-left-width: 0; background: #fcfcfb; color: #0b0b0b; cursor: pointer;}
.steps .step:first-child {border-left-width: 1px; border-radius: 8px 0 0 8px;}
.steps .step:last-child {border-radius: 0 8px 8px 0;}
.steps .step:hover {background: #f0efec;}
.steps .step:focus-visible {outline: 2px solid #2a78d6; outline-offset: 2px; position: relative; z-index: 1;}
@media (max-width: 640px) {
  .panel-row.when {grid-template-columns: 1fr auto;}
  .month-slider {grid-column: 1 / -1;}
  .panel form > div {flex-direction: column;}
  .panel form > div > label, .panel form > div > label:first-child, .panel form > div > label:last-child {border: 1px solid #c3c2b7; border-top-width: 0; border-radius: 0;}
  .panel form > div > label:first-child {border-top-width: 1px; border-radius: 8px 8px 0 0;}
  .panel form > div > label:last-child {border-radius: 0 0 8px 8px;}
  .panel-row.what > div {flex: 1 1 100%;}
}

/* ---------- map ---------- */
.map-hover {font-size: 0.85rem; color: #52514e; min-height: 1.4em; margin-top: 0.5rem;}
.map-buttons {position: absolute; top: 8px; right: 8px; display: flex; gap: 4px;}
.map-buttons button {font: inherit; font-size: 0.85rem; min-width: 2rem; padding: 0.2rem 0.55rem; border: 1px solid #c3c2b7; border-radius: 6px; background: #fcfcfb; color: #0b0b0b; cursor: pointer;}
.map-buttons button:disabled {color: #898781; cursor: default;}
.map-buttons button:focus-visible {outline: 2px solid #2a78d6; outline-offset: 1px;}
.legend {display: flex; flex-wrap: wrap; gap: 0.35rem 1rem; font-size: 0.8rem; color: #52514e; margin: 0.6rem 0 0.5rem;}
.legend-item {display: inline-flex; align-items: center; gap: 0.35rem;}
.swatch {width: 14px; height: 14px; display: inline-block; border-radius: 2px;}

/* ---------- cards and charts: room between title, note, legend and chart ---------- */
.card {padding: 1.1rem 1.25rem;}
.card h3 {max-width: none; margin: 0 0 0.45rem; font-family: var(--sans-serif); font-size: 1.02rem; font-weight: 600; color: #0b0b0b;}
.card > .fine, .card > div > .fine {margin: 0 0 1rem; max-width: none; line-height: 1.45;}
p.fine {max-width: none;}
.card figure {margin: 0;}
.card figure > div:first-child, .card [class*="-swatches"] {margin: 0 0 0.9rem;}   /* Plot's legend row */
.card figure > svg[class*="-ramp"], .card svg[class*="-ramp"] {margin: 0 0 0.9rem; display: block;}
.card figure + .fine {margin-top: 0.8rem;}
.grid {gap: 1.1rem; grid-auto-rows: auto;}   /* Framework's 1fr rows stretched every card to the tallest one */
.time-brush .handle {cursor: ew-resize;}
.time-brush .selection {cursor: grab;}
.tile-value {font-size: 1.8rem; font-weight: 600; line-height: 1.1; margin-bottom: 0.3rem;}
.tile-label {font-size: 0.8rem; color: #52514e; line-height: 1.4;}
.caution {border-left: 4px solid #eda100; padding: 0.6rem 0.9rem; background: #fdf6e3; font-size: 0.9rem; border-radius: 0 8px 8px 0; margin: 0 0 1.25rem;}
.caution > div + div {margin-top: 0.5rem;}
/* the summary fills the page in two columns on a wide screen: full width, lines still short enough to read */
.narrative {columns: 2 26rem; column-gap: 2.5rem; margin: 0 0 1.25rem;}
.narrative p {max-width: none; margin: 0 0 0.7rem; break-inside: avoid;}
/* values that come from the data */
.dyn {font-weight: 600; font-family: var(--sans-serif); font-size: 0.95em; white-space: nowrap;}
.dyn-n {color: #0b0b0b;}
.dyn-d {color: #a2431a;}
.dyn-w {color: #1d5fb0;}
.jump {font-size: 0.85rem; color: #52514e; margin: 0 0 0.9rem; max-width: none;}
.jump a {margin-left: 0.9rem;}
h2[id] {scroll-margin-top: 1rem;}
.fine {font-size: 0.8rem; color: #52514e;}
.card table {margin-top: 0.4rem; width: 100%; max-width: none;}
.card table td a {white-space: nowrap;}
details {margin: 0.4rem 0;}
details p, details li {max-width: 75ch; font-size: 0.9rem;}
</style>

<header class="page-head">
  <h1>Exploring dry and wet conditions in Indonesia</h1>
  <p class="lede">Month by month from January 1950 to December 2025, for every province, kabupaten or kota, and kecamatan. Three standardised indices, computed on TerraClimate v1.1, show rainfall, the balance of rainfall and evaporative demand, and evaporative demand alone.</p>
</header>

```js
import {files} from "./data/files.js";
import {loadTyped, loadJSON, decodeEvents, percentileOf, ym, monthDate, monthLabel, monthsText} from "./components/load.js";
import {hotspotFiles} from "./data/hotspot_files.js";
import {nationalFiles} from "./data/national_files.js";
import {statusFiles} from "./data/status_files.js";
import {classColours, classRgbTable, legendClasses, classLabel, classLabelRange, sideWord, patternStyle, patternRgbTable, eventStyle, eventRgbTable, eventLegend, DRY, WET, NORMAL, INK} from "./components/palette.js";
import {drawMap, legend} from "./components/map.js";
import {timeInteractions, timeSlider, rangeStore, monthOf} from "./components/timezoom.js";
```

```js
// fixed data: loaded once
const meta = await files.meta.json();
const units = await files.units.json();
const outlines = await files.outlines.json();
const cells = await loadTyped("cells", files.cells, Uint32Array);
const cellUnit = await loadTyped("cellUnit", files.cellUnit, Uint8Array);
const cellStep = await loadTyped("cellStep", files.cellStep, Uint8Array);
const unitById = new Map(units.map((u) => [u.id, u]));
const units2 = await files.units2.json();
const unit2ById = new Map(units2.map((u) => [u.id, u]));
const cellUnit2 = await loadTyped("cellUnit2", files.cellUnit2, Uint16Array);
const cellUnit3 = await loadTyped("cellUnit3", files.cellUnit3, Uint16Array);
const allFlagged = new Uint8Array(cells.length).fill(1);
const LAST = meta.months - 1;
const EARLY_LAST = meta.flags.early_record.last_position;
```

```js
// controls
const indexInput = Inputs.radio(
  new Map([["Rainfall \u00b7 SPI", "spi"], ["Water balance \u00b7 SPEI", "spei"], ["Evaporative demand \u00b7 EDDI", "eddi"]]),
  {label: "Index", value: "spi"}
);
const index = Generators.input(indexInput);
const scaleInput = Inputs.radio(
  new Map([["1 month", 1], ["3 months", 3], ["6 months", 6], ["12 months", 12]]),
  {label: "Accumulated over", value: 3}
);
const scale = Generators.input(scaleInput);
const showInput = Inputs.radio(new Map([["Dry and wet", "both"], ["Dry only", "dry"], ["Wet only", "wet"]]), {label: "Conditions", value: "both"});
const show = Generators.input(showInput);
// what the map draws: this month's class, or the space-time pattern of the months leading up to it (a test)
const mapModeInput = Inputs.radio(new Map([["This month", "class"], ["How long", "howlong"], ["Status", "status"], ["Pattern", "pattern"]]), {label: "Map shows", value: "class"});
const mapMode = Generators.input(mapModeInput);
const hotspot = await hotspotFiles.meta.json();
const statusMeta = await statusFiles.meta.json();
const provInput = Inputs.select([null, ...units.slice().sort((a, b) => a.name.localeCompare(b.name))], {
  label: "Province",
  format: (u) => (u ? u.name : "All of Indonesia"),
  value: null
});
const prov = Generators.input(provInput);
const monthInput = html`<input type="range" min="0" max="${LAST}" step="1" value="${LAST}" style="width: 100%;" aria-label="Month, from January 1950 to December 2025">`;
const month = Generators.input(monthInput);
const stepButton = (label, title, by) => html`<button type="button" class="step" title=${title} aria-label=${title} onclick=${() => setMonth(+monthInput.value + by)}>${label}</button>`;
const monthSteps = html`<span class="steps">${stepButton("\u00ab", "One year earlier", -12)}${stepButton("\u2039", "One month earlier", -1)}${stepButton("\u203a", "One month later", 1)}${stepButton("\u00bb", "One year later", 12)}</span>`;
// one way to change the month, used by the slider and by a click on a chart
function setMonth(t) {
  monthInput.value = Math.max(0, Math.min(LAST, Math.round(t)));
  monthInput.dispatchEvent(new Event("input", {bubbles: true}));
}
// The span of months the charts show, shared by all three and kept when the unit or the layer changes.
// It opens on the last 10 years: 120 monthly bars are readable, 912 are not. The slider under the first
// chart widens or moves it. `rangeStore` holds the same span for the slider (see timezoom.js).
const DEFAULT_YEARS = 10;
rangeStore.value = [LAST - DEFAULT_YEARS * 12 + 1, LAST];
const timeRange = Mutable(rangeStore.value);
function setTimeRange(a, b) {
  const span = Math.max(12, Math.min(LAST + 1, Math.round(b - a + 1))); // never narrower than a year
  const from = Math.max(0, Math.min(LAST + 1 - span, Math.round(a)));
  rangeStore.value = [from, from + span - 1];
  timeRange.value = rangeStore.value;
}
function selectProvince(id) {
  provInput.value = id == null ? null : unitById.get(id);
  provInput.dispatchEvent(new Event("input", {bubbles: true}));
}
```

```js
// the kabupaten menu is rebuilt whenever the province changes, which also clears the kabupaten
const kabChoices = prov
  ? meta.children[prov.id].map((id) => unit2ById.get(id)).filter((u) => u.assigned).sort((a, b) => a.name.localeCompare(b.name))
  : [];
const kabInput = Inputs.select([null, ...kabChoices], {
  label: "Kabupaten or kota",
  format: (u) => (u ? u.name : prov ? `All of ${prov.name}` : "Choose a province first"),
  value: null,
  disabled: !prov
});
const kab = Generators.input(kabInput);
function selectKab(id) {
  kabInput.value = id == null ? null : unit2ById.get(id);
  kabInput.dispatchEvent(new Event("input", {bubbles: true}));
}
```

```js
// the kecamatan list (7,298 names) is fetched the first time a kabupaten is opened
const units3 = kab ? await loadJSON("units3", files.units3) : [];
const unit3ById = new Map(units3.map((u) => [u.id, u]));
const kecChoices = kab ? units3.filter((u) => u.adm2_id === kab.id && u.assigned).sort((a, b) => a.name.localeCompare(b.name)) : [];
const kecInput = Inputs.select([null, ...kecChoices], {
  label: "Kecamatan",
  format: (u) => (u ? u.name : kab ? `All of ${kab.name}` : "Choose a kabupaten or kota first"),
  value: null,
  disabled: !kab
});
const kec = Generators.input(kecInput);
function selectKec(id) {
  kecInput.value = id == null ? null : unit3ById.get(id);
  kecInput.dispatchEvent(new Event("input", {bubbles: true}));
}
```

<section class="panel" aria-label="Controls">
  <div class="panel-row what">
    <div>${indexInput}</div>
    <div>${scaleInput}</div>
    <div>${showInput}</div>
    <div>${mapModeInput}</div>
  </div>
  <div class="panel-row where">
    <div>${provInput}</div>
    <div>${kabInput}</div>
    <div>${kecInput}</div>
  </div>
  <div class="panel-row crumb-row">${crumbs}</div>
  <div class="panel-row when">
    <div class="month-label">${monthLabel(month)}</div>
    ${monthSteps}
    <div class="month-slider">${monthInput}</div>
  </div>
</section>

```js
// Where the reader is. Every level above the current one is a link straight back to it, so a kecamatan can be
// left for its kabupaten in one click, without touching the map or reopening a menu.
const crumbs = (() => {
  const here = (name) => html`<strong>${name}</strong>`;
  const back = (name, fn) => html`<a href="#" onclick=${(e) => { e.preventDefault(); fn(); }}>${name}</a>`;
  const parts = [prov ? back("Indonesia", () => selectProvince(null)) : here("Indonesia")];
  if (prov) parts.push(kab ? back(prov.name, () => selectKab(null)) : here(prov.name));
  if (kab) parts.push(kec ? back(kab.name, () => selectKec(null)) : here(kab.name));
  if (kec) parts.push(here(kec.name));
  return html`<nav class="crumbs" aria-label="Selected area">${parts.map((el, i) => html`${i ? html`<span class="crumb-sep" aria-hidden="true">›</span>` : ""}${el}`)}${prov ? html`<span class="fine crumb-hint">Click a name to go back to it.</span>` : html`<span class="fine crumb-hint">Click a province on the map, or choose one above.</span>`}</nav>`;
})();
```

```js
// the selected layer: its tables load when the index or the scale changes
const tag = `${index}${String(scale).padStart(2, "0")}`;
const layer = meta.layers[tag];
const share = await loadTyped(`${tag}/share`, files.layers[tag].share, Uint16Array);
const mean = await loadTyped(`${tag}/mean`, files.layers[tag].mean, Int16Array);
const eventCols = await loadJSON(`${tag}/events`, files.layers[tag].events);
const summary = await loadJSON(`${tag}/summary`, files.layers[tag].summary);
const NC = layer.classes.length;
const codesOf = (side) => layer.classes.filter((c) => c.side === side).map((c) => c.code);
// A dataset is one table of units: all provinces, or the kabupaten of one province.
// `pos` turns a unit id into its place on the unit axis. Everything below reads through these three functions.
const d1 = {share, mean, events: eventCols, summary, nU: meta.encoding.n_units, pos: (id) => id - 1, enc: meta.encoding};
// Indonesia as one unit: every drawn cell at full area (pipeline/step6_national.py). Same layout as d1, one unit wide.
const nationMeta = await nationalFiles.meta.json();
const nation = nationMeta.unit;
const d0 = await (async () => {
  const f = nationalFiles.layers[tag];
  return {
    share: await loadTyped(`${tag}/national/share`, f.share, Uint16Array),
    mean: await loadTyped(`${tag}/national/mean`, f.mean, Int16Array),
    events: await loadJSON(`${tag}/national/events`, f.events),
    summary: await loadJSON(`${tag}/national/summary`, f.summary),
    nU: 1, pos: () => 0, enc: meta.encoding
  };
})();
// share of a unit's valued area on one side, in percent; null where there is no value
function sideShare(d, t, id, side) {
  if (d.side) { // kecamatan: the dry and wet totals are stored directly, so no rounding errors add up
    const v = d.side[(t * d.nU + d.pos(id)) * 2 + (side === "dry" ? 0 : 1)];
    return v === d.enc.share_missing ? null : (v / d.enc.share_scale) * 100;
  }
  const base = (t * d.nU + d.pos(id)) * NC;
  if (d.share[base] === d.enc.share_missing) return null;
  let s = 0;
  for (const code of codesOf(side)) s += d.share[base + code - 1];
  return Math.min(100, (s / d.enc.share_scale) * 100); // stored shares are rounded one by one
}
function meanAt(d, t, id) {
  const v = d.mean[t * d.nU + d.pos(id)];
  return v === d.enc.mean_missing ? null : v / d.enc.mean_scale;
}
// one summary row, whether the file is a list of records or column arrays
function summaryOf(d, id, side) {
  if (Array.isArray(d.summary)) return d.summary.find((r) => r.id === id && r.side === side);
  const c = d.summary;
  for (let i = 0; i < c.id.length; i++) {
    if (c.id[i] === id && c.side[i] === side) return Object.fromEntries(Object.keys(c).map((k) => [k, c[k][i]]));
  }
  return undefined;
}
function eventsOf(d, id) {
  const out = [];
  for (let i = 0; i < d.events.unit.length; i++) {
    if (d.events.unit[i] !== id) continue;
    const e = {};
    for (const k of Object.keys(d.events)) e[k] = d.events[k][i];
    out.push(e);
  }
  return out;
}
const DRYW = sideWord("dry", index);
const WETW = sideWord("wet", index);
const cap = (w) => w[0].toUpperCase() + w.slice(1);
const DRYCOL = `${cap(DRYW)}, % of area`;
const WETCOL = `${cap(WETW)}, % of area`;
```

```js
// the open province's kabupaten: one bundle of four files, loaded when the province or the layer changes
const d2 = prov
  ? await (async () => {
      const f = files.layers[tag].adm2[prov.id];
      const kids = meta.children[prov.id];
      const place = new Map(kids.map((id, i) => [id, i]));
      return {
        share: await loadTyped(`${tag}/adm2/${prov.id}/share`, f.share, Uint16Array),
        mean: await loadTyped(`${tag}/adm2/${prov.id}/mean`, f.mean, Int16Array),
        events: await loadJSON(`${tag}/adm2/${prov.id}/events`, f.events),
        summary: await loadJSON(`${tag}/adm2/${prov.id}/summary`, f.summary),
        nU: kids.length, pos: (id) => place.get(id), enc: meta.encoding_adm2, kids
      };
    })()
  : null;
const outlines2 = prov ? await loadJSON("outlines2", files.outlines2) : null;
// the open kabupaten's kecamatan come from the province's kecamatan bundle (named dKec: `d3` is the D3 library)
const dKec = kab
  ? await (async () => {
      const f = files.layers[tag].adm3[prov.id];
      const kids = meta.children3[prov.id];
      const place = new Map(kids.map((id, i) => [id, i]));
      const key = `${tag}/adm3/${prov.id}`;
      return {
        side: await loadTyped(`${key}/side`, f.side, Uint8Array),   // dry and wet totals, rounded once
        share: await loadTyped(`${key}/share`, f.share, Uint8Array), // every class, for the share chart
        mean: await loadTyped(`${key}/mean`, f.mean, Int16Array),
        events: decodeEvents(await loadTyped(`${key}/events`, f.events, Uint8Array)),
        summary: await loadJSON(`${key}/summary`, f.summary),
        nU: kids.length, pos: (id) => place.get(id), enc: meta.encoding_adm3, kids
      };
    })()
  : null;
const outlines3 = kab ? await loadJSON(`outlines3/${prov.id}`, files.outlines3[prov.id]) : null;
// the selected unit is the deepest thing chosen; `ds` is the dataset it lives in
const unit = kec ?? kab ?? prov ?? nation;
const ds = kec ? dKec : kab ? d2 : prov ? d1 : d0;
const areaWord = kec ? "the kecamatan" : kab ? (String(kab.type ?? "").startsWith("Kota") ? "the city" : "the kabupaten") : prov ? "the province" : "the country";
const MIN_CELLS = meta.min_cells_note.value;
```

```js
// The selected unit's mean index at all four accumulation periods. A short period can look calm where a
// season is normally almost dry (Indramayu, July to September 1997), so the periods are shown side by side.
const SCALES = [1, 3, 6, 12];
const scaleMeans = unit
  ? await (async () => {
      const out = {};
      for (const sc of SCALES) {
        const tg = `${index}${String(sc).padStart(2, "0")}`;
        const L = files.layers[tg];
        out[sc] = kec ? await loadTyped(`${tg}/adm3/${prov.id}/mean`, L.adm3[prov.id].mean, Int16Array)
          : kab ? await loadTyped(`${tg}/adm2/${prov.id}/mean`, L.adm2[prov.id].mean, Int16Array)
          : prov ? await loadTyped(`${tg}/mean`, L.mean, Int16Array)
          : await loadTyped(`${tg}/national/mean`, nationalFiles.layers[tg].mean, Int16Array);
      }
      return out;
    })()
  : null;
// one value of that table; every period has the same unit axis as `ds`
function scaleMean(sc, t) {
  const v = scaleMeans[sc][t * ds.nU + ds.pos(unit.id)];
  return v === ds.enc.mean_missing ? null : v / ds.enc.mean_scale;
}
const LIMITED_RANGE = -2.0; // PROPOSED: note the season when the index has never reached "extremely dry" in it
```

```js
// this month's map: the decade file holding it, then the month's slice
const decade = Math.floor((1950 + Math.floor(month / 12)) / 10) * 10;
const mapFile = layer.maps[decade];
const block = await loadTyped(`${tag}/map/${decade}`, files.layers[tag].maps[decade], Uint8Array);
const n = meta.grid.n_drawn;
const mapClasses = block.subarray((month - mapFile.first_month) * n, (month - mapFile.first_month + 1) * n);
const earlyNow = month <= EARLY_LAST;
const stepNow = month <= layer.step_1984_last_position;
const cellFlag = earlyNow ? allFlagged : stepNow ? cellStep : null;
const colours = classColours(layer.classes, show);
const classByCode = new Map(layer.classes.map((c) => [c.code, c]));
const hasValue = month >= layer.first_month_with_value;
// pattern mode: the emerging hot spot category of each cell for the window of months ending at this month
const hsLayer = hotspot.layers[tag] ?? null;
const patternOn = mapMode === "pattern" && hsLayer != null;
const hsFile = patternOn ? hsLayer.maps[decade] : null;
const hsBlock = patternOn ? await loadTyped(`${tag}/hotspot/${decade}`, hotspotFiles.layers[tag][decade], Uint8Array) : null;
const patternCodes = patternOn ? hsBlock.subarray((month - hsFile.first_month) * n, (month - hsFile.first_month + 1) * n) : null;
const patternHasResult = patternOn && month >= hsLayer.first_month_with_result;
const HSW = hotspot.parameters.window_months;
// "How long" and "Status": where each cell stands in an event of its own (pipeline/step7_status.py)
const stLayer = statusMeta.layers[tag] ?? null;
const statusOn = (mapMode === "howlong" || mapMode === "status") && stLayer != null;
const stFile = statusOn ? stLayer.maps[decade] : null;
const stBlock = statusOn ? await loadTyped(`${tag}/status/${decade}`, statusFiles.layers[tag][decade], Uint8Array) : null;
const stCodes = statusOn ? stBlock.subarray((month - stFile.first_month) * n, (month - stFile.first_month + 1) * n) : null;
// whatever the mode, the map reads this: one code per drawn cell, a colour table, a legend, and words for a cell
const overlay = patternOn
  ? {
      codes: patternCodes, rgb: patternRgbTable(index, show),
      say: (code) => (code ? patternStyle(code, index).label.toLowerCase() : "no result"),
      // only the categories present on the map this month, dry side first, so the legend is never 17 long for nothing
      items: [10, 11, 12, 13, 14, 15, 16, 17, 9, 8, 7, 6, 5, 4, 3, 2, 1]
        .filter((code) => patternCodes.includes(code))
        .map((code) => patternStyle(code, index, show))
        .map((st) => ({colour: st.colour, label: st.shown === false ? "Other side, not shown" : st.label}))
        .filter((st, i, a) => a.findIndex((o) => o.label === st.label) === i)
    }
  : statusOn
    ? {
        codes: stCodes, rgb: eventRgbTable(mapMode, index, show, statusMeta),
        say: (code) => (code ? eventStyle(code, mapMode, index, "both", statusMeta).label.toLowerCase() : "no value"),
        items: eventLegend(mapMode, index, show, statusMeta)
      }
    : null;
```

<div class="card">

```js
display(
  resize((w) => drawMap({
    grid: meta.grid, cells, cellFlag, classes: overlay ? overlay.codes : mapClasses,
    rgb: overlay ? overlay.rgb : classRgbTable(layer.classes, show), outlines,
    detail: [
      ...(kab ? outlines3.features.filter((f) => unit3ById.get(f.properties.id)?.adm2_id === kab.id) : []),
      ...(prov ? outlines2.features.filter((f) => unit2ById.get(f.properties.id)?.adm1_id === prov.id) : [])
    ],
    highlight: [
      ...(prov ? outlines.features.filter((f) => f.properties.id === prov.id) : []),
      ...(kab ? outlines2.features.filter((f) => f.properties.id === kab.id) : []),
      ...(kec ? outlines3.features.filter((f) => f.properties.id === kec.id) : [])
    ],
    describe: (i) => {
      const u = unitById.get(cellUnit[i]);
      const k = prov && u && u.id === prov.id ? unit2ById.get(cellUnit2[i]) : null;
      const e = kab && k && k.id === kab.id ? unit3ById.get(cellUnit3[i]) : null;
      const c = classByCode.get(mapClasses[i]);
      const what = overlay
        ? `${overlay.say(overlay.codes[i])} (this month: ${c ? classLabel(c, index) : "no data"})`
        : (c ? classLabel(c, index) : "no data");
      return `${u ? u.name : "No province"}${k && k.assigned ? `, ${k.name}` : ""}${e && e.assigned ? `, ${e.name}` : ""}: ${what}${cellFlag && cellFlag[i] ? " (less reliable here in this period)" : ""}`;
    },
    // a click opens a province; inside the open province it picks the kabupaten there; inside the open
    // kabupaten it picks the kecamatan there; the sea goes up one level
    onPick: (i) => {
      const p = i < 0 ? 0 : cellUnit[i];
      if (p === 0) return kec ? selectKec(null) : kab ? selectKab(null) : selectProvince(null);
      if (prov && p === prov.id) {
        const k = unit2ById.get(cellUnit2[i]);
        if (kab && k && k.id === kab.id) {
          const e = unit3ById.get(cellUnit3[i]);
          return selectKec(e && e.assigned && e.adm2_id === kab.id ? e.id : null);
        }
        return selectKab(k && k.assigned && k.adm1_id === prov.id ? k.id : null);
      }
      return selectProvince(p);
    },
    width: w
  }))
);
display(
  legend({
    items: overlay ? overlay.items
      : legendClasses(layer.classes).map((c) => ({colour: colours.get(c.code), label: classLabelRange(c, index)})),
    flagged: !!cellFlag,
    flagText: "Washed out: less reliable in this period"
  })
);
```

<div class="fine">${statusOn ? html`<strong>${mapMode === "howlong" ? "How long." : "Status."}</strong> Each cell is read on its own: an event there begins in the first month its ${layer.label} reaches ${index === "eddi" ? "+1.0 or −1.0" : "−1.0 or +1.0"} and runs until the index crosses zero. ${mapMode === "howlong"
  ? "The colour is the number of months the event has run so far, up to the month shown."
  : `An event is new in its first two months. After that it is deepening when the cell is at or beyond the onset level and further from zero than a month earlier, persisting when it is at or beyond that level but no further, and easing once it is back inside the level without having crossed zero. Ended marks the month an event stops.`} A cell's event is not its ${prov ? "kabupaten's or " : ""}province's event, which is found on the mean of the whole area. The ${mapMode === "howlong" ? "bins" : "five states"} are this dashboard's own and are still open to change. ` : ""}${patternOn ? html`<strong>Pattern.</strong> Each cell is classed from the ${HSW} months ending in ${monthLabel(month)} by emerging hot spot analysis. A ${sideWord("dry", index)} cluster (a hot spot, in the method's words) is a neighbourhood whose values sit on the ${sideWord("dry", index)} side of normal by more than chance would give, and a ${sideWord("wet", index)} cluster (a cold spot) one on the ${sideWord("wet", index)} side. The bar is low: neighbouring cells move together, so a neighbourhood only mildly off normal already counts, and a cluster is not a class. Hover a cell to see its class this month beside its pattern. The categories say whether the clustering is new, has run without a break (consecutive), has held for at least 90% of the months (persistent, intensifying or diminishing), comes and goes (sporadic), or has swung from the other side (oscillating). "Historical" means clustered for at least 90% of the months but not in the last one. ${patternHasResult ? "" : `No result yet: the window needs ${HSW} months of values, so results start in ${monthLabel(hsLayer.first_month_with_result)}.`} The categories and their rules are Esri's. Three things are choices made here and still open: the neighbourhood (3 by 3 cells and the month before), the window length, and measuring against normal where Esri's tool measures against the average of the data itself. ` : ""}${layer.label}, ${monthLabel(month)}. ${layer.measures[0].toUpperCase() + layer.measures.slice(1)} over ${monthsText(scale)}, against a ${layer.baseline.split(" ")[0]} baseline. ${hasValue ? "" : `No values yet: a ${scale}-month index needs ${monthsText(scale)} of data, so it starts in ${monthLabel(layer.first_month_with_value)}.`} ${index === "eddi" ? "For EDDI the warm colours mean high evaporative demand and the cool colours low demand, not wet conditions." : ""}</div>

</div>

```js
// flag notes for the month on screen
const cautions = [];
if (earlyNow) cautions.push("Less reliable period. Before 1970, TerraClimate's annual rainfall is lower than rain gauges at the same places: by about 10% of normal in the 1950s and 4% in the 1960s. Dry conditions in this period are likely overstated.");
if (stepNow && (!prov || unit.step_1984_majority)) cautions.push(`Less reliable period. In northern and central Sumatra and West Kalimantan, TerraClimate's inputs change at the start of 1984. Before that it reads about 20% drier than the three rain gauges checked inside the region. ${Math.round(unit.step_1984_share * 100)}% of ${unit.name}'s cell area is affected${prov ? "" : "; those cells are washed out on the map"}.`);
if (unit && unit.n_cells < MIN_CELLS) cautions.push(`Small area. Only ${unit.n_cells} grid ${unit.n_cells === 1 ? "cell touches" : "cells touch"} ${unit.name}, each about 21 square kilometres, so its percentages move in steps of about ${Math.round(100 / unit.n_cells)} points and include land just outside its boundary.`);
// (not for the country: a mean over all of Indonesia has a narrow range in every month, for a different reason)
if (prov && index !== "eddi" && show !== "wet") {
  // lowest value this unit has ever had in this calendar month, at the chosen period
  let lowest = Infinity, count = 0;
  for (let t = month % 12; t <= LAST; t += 12) {
    const v = scaleMean(scale, t);
    if (v != null) { lowest = Math.min(lowest, v); count++; }
  }
  if (count >= 30 && lowest > LIMITED_RANGE) {
    const monthName = monthLabel(month).split(" ")[0];
    cautions.push(`Limited range in this season. In ${count} ${monthName}s on record, ${layer.label} for ${unit.name} has never gone below ${lowest.toFixed(2)}. Where a season is normally almost dry, a short accumulation period has little room to register a deficit, so a calm reading here does not mean conditions were normal. Compare the longer periods in the chart of all four accumulation periods below, and evaporative demand.`);
  }
}
display(cautions.length ? html`<div class="caution">${cautions.map((c) => html`<div>${c}</div>`)}</div>` : html`<span></span>`);
```

```js
// everything below needs a selected unit: a province, or a kabupaten inside it
const sel = unit
  ? (() => {
      const id = unit.id;
      const ev = eventsOf(ds, id);
      const now = ev.find((e) => e.start <= month && month <= e.end) ?? null;
      const flaggedProv = unit.step_1984_majority;
      const sumDry = summaryOf(ds, id, "dry");
      const sumWet = summaryOf(ds, id, "wet");
      return {id, ev, now, flaggedProv, sumDry, sumWet, dry: sideShare(ds, month, id, "dry"), wet: sideShare(ds, month, id, "wet"), mean: meanAt(ds, month, id)};
    })()
  : null;
```

```js
if (sel) {
  const pct = (v) => (v == null ? "no data" : `${v.toFixed(0)}%`);
  const eventTile = sel.now
    ? html`<div class="tile-value">${monthsText(month - sel.now.start + 1)}</div><div class="tile-label">into a ${sel.now.side === 0 ? DRYW : WETW} event that began in ${monthLabel(sel.now.start)}${sel.now.flagged ? " (less reliable period)" : ""}</div>`
    : html`<div class="tile-value">None</div><div class="tile-label">no event running for ${areaWord} as a whole</div>`;
  display(html`<h2>${unit.name}${kec ? `, ${kab.name}` : ""}${kab ? `, ${prov.name}` : ""}, ${monthLabel(month)}</h2>
  ${kec ? html`<p class="fine"><a href="#" onclick=${(e) => { e.preventDefault(); selectKec(null); }}>Back to ${kab.name}</a></p>`
    : kab ? html`<p class="fine"><a href="#" onclick=${(e) => { e.preventDefault(); selectKab(null); }}>Back to ${prov.name}</a></p>` : ""}
  <p class="jump">On this page: <a href="#over-time">Over time</a><a href="#events">Past events</a><a href="#enso">El Niño and La Niña</a><a href="#how-to-read">How to read this</a></p>
  <div class="grid grid-cols-4">
    <div class="card"><div class="tile-value">${pct(sel.dry)}</div><div class="tile-label">of area in a ${DRYW} class</div></div>
    <div class="card"><div class="tile-value">${pct(sel.wet)}</div><div class="tile-label">of area in a ${WETW} class</div></div>
    <div class="card"><div class="tile-value">${sel.mean == null ? "no data" : sel.mean.toFixed(2)}</div><div class="tile-label">mean ${layer.label} over ${areaWord}</div></div>
    <div class="card">${eventTile}</div>
  </div>`);
} else {
  display(html`<div></div>`); // always display: a block that displays nothing keeps its previous output on screen
}
```

```js
// narrative: every sentence is built from the numbers above and guards its own edge cases
if (sel) {
  const parts = [];
  // A value taken from the data is wrapped in a marker, kind|text, and drawn as a coloured span by `rich`:
  // d = dry side, w = wet side, n = neither. The sentences stay plain strings, so they are easy to read here.
  const mark = (kind, x) => `⟦${kind}|${x}⟧`;
  const N = (x) => mark("n", x), D = (x) => mark("d", x), W = (x) => mark("w", x);
  const V = (v) => mark(v * layer.dry_sign >= 1 ? "d" : v * layer.dry_sign <= -1 ? "w" : "n", v.toFixed(2)); // an index value, by its side
  const rich = (text) => {
    const out = [];
    let last = 0;
    for (const m of text.matchAll(/⟦([ndw])\|([^⟧]*)⟧/g)) {
      out.push(text.slice(last, m.index), html`<span class=${`dyn dyn-${m[1]}`}>${m[2]}</span>`);
      last = m.index + m[0].length;
    }
    out.push(text.slice(last));
    return html`<p>${out}</p>`;
  };
  if (sel.dry == null) {
    parts.push(`${layer.label} has no value for ${unit.name} in ${monthLabel(month)}: a ${scale}-month index starts in ${monthLabel(layer.first_month_with_value)}.`);
  } else {
    parts.push(`In ${monthLabel(month)}, ${D(`${sel.dry.toFixed(0)}%`)} of ${unit.name}'s area was in a ${DRYW} class and ${W(`${sel.wet.toFixed(0)}%`)} in a ${WETW} class on ${layer.label}.`);
    if (sel.now) {
      const side = sel.now.side === 0 ? DRYW : WETW;
      const sofar = month - sel.now.start + 1;
      const K = sel.now.side === 0 ? D : W;
      const tail = sel.now.open
        ? month === LAST ? "It was still running at the end of the record." : `It was still running at the end of the record, ${K(monthsText(sel.now.duration))} after it began.`
        : `It lasted ${K(monthsText(sel.now.duration))} in all, until ${N(monthLabel(sel.now.end))}.`;
      parts.push(`Taken as a whole, ${areaWord} was ${K(monthsText(sofar))} into a ${side} event that began in ${N(monthLabel(sel.now.start))}. ${tail}`);
    } else {
      parts.push(`Taken as a whole, ${areaWord} was not in an event this month.`);
    }
  }
  const s = show === "wet" ? sel.sumWet : sel.sumDry;
  const sw = show === "wet" ? WETW : DRYW;
  if (s && s.n_events_unflagged > 0) {
    const open = s.longest_unflagged_is_open ? " and is still running, so that length is so far" : "";
    const K = show === "wet" ? W : D;
    parts.push(`Outside the less reliable periods, the record holds ${K(s.n_events_unflagged)} ${sw} ${s.n_events_unflagged === 1 ? "event" : "events"} for ${unit.name} at this accumulation period. The longest began in ${N(monthLabel((+s.longest_unflagged_start.slice(0, 4) - 1950) * 12 + (+s.longest_unflagged_start.slice(5, 7) - 1)))} and ran for ${K(monthsText(s.longest_unflagged_months))}${open}.`);
  } else if (s) {
    parts.push(`The record holds no ${sw} event for ${unit.name} outside the less reliable periods at this accumulation period.`);
  }
  // ---- more of the story, each sentence from the data and each guarding its own gaps
  const more = [];
  const ord = (k) => `${k}${k % 100 >= 11 && k % 100 <= 13 ? "th" : ["th", "st", "nd", "rd"][k % 10] ?? "th"}`;
  const pc = (v) => `${v.toFixed(0)}%`;
  const from = reliableFrom(sel.flaggedProv);
  const sinceYear = 1950 + Math.floor(from / 12);
  const monthName = monthLabel(month).split(" ")[0];
  const sgn = layer.dry_sign;
  if (sel.mean != null) {
    // where this month stands among the same calendar month, outside the less reliable periods
    const same = [];
    for (let t = month % 12; t <= LAST; t += 12) {
      if (t < from) continue;
      const v = meanAt(ds, t, sel.id);
      if (v != null) same.push(v * sgn);
    }
    if (month >= from && same.length >= 10) {
      const mine = sel.mean * sgn;
      const rankDry = same.filter((d) => d > mine).length + 1;
      const rankWet = same.filter((d) => d < mine).length + 1;
      const word = rankDry <= rankWet
        ? `${ord(rankDry)} ${index === "eddi" ? "highest in demand" : "driest"}`
        : `${ord(rankWet)} ${index === "eddi" ? "lowest in demand" : "wettest"}`;
      more.push(index === "eddi"
        ? `Its mean ${layer.label} of ${V(sel.mean)} ranks ${rankDry <= rankWet ? D(`${ord(rankDry)} highest`) : W(`${ord(rankWet)} lowest`)} in evaporative demand among the ${N(same.length)} ${monthName}s since ${sinceYear}.`
        : `Its mean ${layer.label} of ${V(sel.mean)} makes this the ${(rankDry <= rankWet ? D : W)(word.replace(/^1st /, ""))} ${monthName} of the ${N(same.length)} since ${sinceYear}.`);
    }
    // change on a month and on a year earlier
    const was = (t) => (t >= 0 ? {dry: sideShare(ds, t, sel.id, "dry"), wet: sideShare(ds, t, sel.id, "wet")} : null);
    const m1 = was(month - 1), y1 = was(month - 12);
    const bits = [];
    if (m1 && m1.dry != null) bits.push(`a month earlier the ${DRYW} share was ${D(pc(m1.dry))} and the ${WETW} share ${W(pc(m1.wet))}`);
    if (y1 && y1.dry != null) bits.push(`a year earlier, ${D(pc(y1.dry))} and ${W(pc(y1.wet))}`);
    if (bits.length) more.push(`${cap(bits.join("; "))}.`);
    // the four accumulation periods
    const per = SCALES.map((sc) => ({sc, v: scaleMean(sc, month)})).filter((x) => x.v != null);
    if (per.length === SCALES.length) {
      const gap = (per[3].v - per[0].v) * sgn; // positive: the 12-month value is further to the dry side
      const lean = gap > 0.5 ? ` The 12-month reading is ${index === "eddi" ? "higher in demand" : "drier"} than the 1-month one.`
        : gap < -0.5 ? ` The 12-month reading is ${index === "eddi" ? "lower in demand" : "wetter"} than the 1-month one.` : "";
      more.push(`Mean ${index.toUpperCase()} over 1, 3, 6 and 12 months was ${per.map((x) => V(x.v)).join(", ").replace(/, ([^,]*)$/, " and $1")}.${lean}`);
    }
  }
  // the places inside
  const inside = !prov ? {d: d1, list: units, many: "provinces", one: "province"}
    : !kab ? {d: d2, list: d2.kids.map((id) => unit2ById.get(id)).filter((u) => u && u.assigned), many: "kabupaten and kota", one: "kabupaten or kota"}
    : !kec ? {d: dKec, list: dKec.kids.map((id) => unit3ById.get(id)).filter((u) => u && u.adm2_id === kab.id && u.assigned), many: "kecamatan", one: "kecamatan"}
    : null;
  if (inside && sel.dry != null) {
    const side = show === "wet" ? "wet" : "dry";
    const w = side === "wet" ? WETW : DRYW;
    const ranked = inside.list.map((u) => ({name: u.name, v: sideShare(inside.d, month, u.id, side)})).filter((x) => x.v != null).sort((x, y) => y.v - x.v);
    const over = ranked.filter((x) => x.v > 50);
    const K = side === "wet" ? W : D;
    const names = (arr) => arr.map((x) => `${N(x.name)} (${K(pc(x.v))})`).join(", ").replace(/, ([^,]*)$/, " and $1");
    if (ranked.length > 1) {
      more.push(over.length
        ? `${K(over.length)} of ${N(ranked.length)} ${inside.many} had more than half their area in a ${w} class, led by ${names(over.slice(0, 3))}.`
        : ranked[0].v > 0
          ? `No ${inside.one} had more than half its area in a ${w} class; the highest was ${N(ranked[0].name)} at ${K(pc(ranked[0].v))}.`
          : `No ${inside.one} had any area in a ${w} class.`);
    }
  }
  // ENSO: the state of the Pacific this month, and what this calendar month has looked like in each phase
  const ep = enso.events.find((e) => e.start <= month && month <= e.end);
  const pacific = ep
    ? `the ${N(ord(month - ep.start + 1))} month of a ${N(`${ep.strength} ${phaseName(ep.phase)}`)} episode that began in ${N(monthLabel(ep.start))}`
    : "in neither an El Niño nor a La Niña episode";
  const byPhase = PHASES.map((ph) => {
    let sum = 0, k = 0;
    for (let t = month % 12; t <= LAST; t += 12) {
      if (t < from || enso.phase[t] !== ph.p) continue;
      const v = meanAt(ds, t, sel.id);
      if (v != null) { sum += v; k++; }
    }
    return {name: ph.name, k, mean: k ? sum / k : null};
  }).filter((x) => x.k >= 3);
  const usual = byPhase.length >= 2
    ? ` Since ${sinceYear}, ${unit.name}'s mean ${layer.label} in ${monthName} has averaged ${byPhase.map((x) => `${V(x.mean)} in ${x.name === "Neutral" ? "neutral" : x.name} months (${x.k})`).join(", ").replace(/, ([^,]*)$/, " and $1")}.`
    : "";
  more.push(`In the tropical Pacific the Relative Oceanic Niño Index stood at ${N(enso.roni[month].toFixed(2))}, ${pacific}.${usual}`);
  display(html`<div class="narrative">${parts.map(rich)}${more.map(rich)}</div>`);
} else {
  display(html`<div></div>`); // always display: a block that displays nothing keeps its previous output on screen
}
```

```js
// province panel, or the all-provinces table when none is selected
if (!prov) {
  const rows = units.map((u) => ({
    Province: u.name,
    "Island group": u.island_group,
    [DRYCOL]: sideShare(d1, month, u.id, "dry"),
    [WETCOL]: sideShare(d1, month, u.id, "wet"),
    "Mean index": meanAt(d1, month, u.id)
  }));
  display(html`<h2>Inside Indonesia: the provinces, ${monthLabel(month)}</h2>`);
  display(hasValue
    ? Inputs.table(rows, {
        sort: DRYCOL, reverse: true, rows: 38, select: false,
        format: {[DRYCOL]: (d) => (d == null ? "no data" : d.toFixed(0)), [WETCOL]: (d) => (d == null ? "no data" : d.toFixed(0)), "Mean index": (d) => (d == null ? "no data" : d.toFixed(2))}
      })
    : html`<p>No values for this month at this accumulation period.</p>`);
  display(html`<p class="fine">Share of each province's cell area in a ${DRYW} or ${WETW} class this month. A province's figure uses every grid cell its boundary touches. Choose a province for its history.</p>`);
} else {
  display(html`<div></div>`); // always display: a block that displays nothing keeps its previous output on screen
}
```

```js
// the open province's kabupaten and kota this month: a way in for readers who do not know where one is on the map
if (prov && !kab) {
  const rows = d2.kids.map((id) => unit2ById.get(id)).filter((u) => u.assigned).map((u) => ({
    "Kabupaten or kota": u.name,
    [DRYCOL]: sideShare(d2, month, u.id, "dry"),
    [WETCOL]: sideShare(d2, month, u.id, "wet"),
    "Mean index": meanAt(d2, month, u.id),
    "Grid cells": u.n_cells
  }));
  display(html`<h2>Inside ${prov.name}, ${monthLabel(month)}</h2>`);
  display(hasValue
    ? Inputs.table(rows, {
        sort: DRYCOL, reverse: true, rows: Math.min(rows.length, 40), select: false,
        format: {[DRYCOL]: (d) => (d == null ? "no data" : d.toFixed(0)), [WETCOL]: (d) => (d == null ? "no data" : d.toFixed(0)), "Mean index": (d) => (d == null ? "no data" : d.toFixed(2))}
      })
    : html`<p>No values for this month at this accumulation period.</p>`);
  display(html`<p class="fine">${rows.length} kabupaten and kota. Click one on the map, or choose it from the menu, for its history. Those touching fewer than ${MIN_CELLS} grid cells give coarse percentages.</p>`);
} else {
  display(html`<div></div>`); // always display: a block that displays nothing keeps its previous output on screen
}
```

```js
// the open kabupaten's kecamatan this month
if (kab && !kec) {
  const rows = dKec.kids.map((id) => unit3ById.get(id)).filter((u) => u && u.adm2_id === kab.id && u.assigned).map((u) => ({
    Kecamatan: u.name,
    [DRYCOL]: sideShare(dKec, month, u.id, "dry"),
    [WETCOL]: sideShare(dKec, month, u.id, "wet"),
    "Mean index": meanAt(dKec, month, u.id),
    "Grid cells": u.n_cells
  }));
  display(html`<h2>Inside ${kab.name}, ${monthLabel(month)}</h2>`);
  display(hasValue
    ? Inputs.table(rows, {
        sort: DRYCOL, reverse: true, rows: Math.min(Math.max(rows.length, 1), 40), select: false,
        format: {[DRYCOL]: (d) => (d == null ? "no data" : d.toFixed(0)), [WETCOL]: (d) => (d == null ? "no data" : d.toFixed(0)), "Mean index": (d) => (d == null ? "no data" : d.toFixed(2))}
      })
    : html`<p>No values for this month at this accumulation period.</p>`);
  display(html`<p class="fine">${rows.length} kecamatan. Click one on the map, or choose it from the menu, for its history. A kecamatan usually touches only a handful of grid cells, most of them shared with its neighbours: read its percentages as rough.</p>`);
} else {
  display(html`<div></div>`); // always display: a block that displays nothing keeps its previous output on screen
}
```

```js
// chart data for the selected unit
const series = sel
  ? (() => {
      // One bar per month, divided among the classes and always adding to 100%: wet classes at the bottom,
      // near normal in the middle, dry classes on top. `bands` runs from the bottom of the bar to the top.
      // With "Dry only" or "Wet only", everything on the other side is merged into one neutral band.
      const rest = (label, others) => ({label, colour: NORMAL, get: (t) => Math.max(0, 100 - others.reduce((sum, o) => sum + o.get(t), 0))});
      const at = (t) => (t * ds.nU + ds.pos(sel.id)) * NC;
      const hasValue1 = (t) => ds.share[at(t)] !== ds.enc.share_missing;
      const band = (c) => ({label: classLabelRange(c, index), colour: colours.get(c.code), get: (t) => (ds.share[at(t) + c.code - 1] / ds.enc.share_scale) * 100});
      const occurring = layer.classes.filter((c) => c.occurs);
      const wet = occurring.filter((c) => c.side === "wet").sort((x, y) => y.rank - x.rank).map(band);   // most severe at the bottom
      const normal = occurring.filter((c) => c.side === "normal").map(band);
      const dry = occurring.filter((c) => c.side === "dry").sort((x, y) => x.rank - y.rank).map(band);   // most severe at the top
      const bands = show === "dry" ? [rest(`Not ${DRYW}`, dry), ...dry]
        : show === "wet" ? [...wet, rest(`Not ${WETW}`, wet)]
        : [...wet, ...normal, ...dry];
      const rows = [];
      for (let t = 0; t <= LAST; t++) {
        if (!hasValue1(t)) continue; // no value: no bar, never a bar of "normal"
        let y = 0;
        for (const bnd of bands) {
          const v = bnd.get(t);
          if (v > 0) rows.push({t, date: monthDate(t), date2: monthDate(t + 1), label: bnd.label, value: v, y1: y, y2: Math.min(100, y + v)});
          y += v;
        }
      }
      // legend in the order the bands appear in a bar, top first
      const legendItems = bands.slice().reverse().map(({label, colour}) => ({label, colour}));
      const means = [];
      for (let t = 0; t <= LAST; t++) {
        const v = meanAt(ds, t, sel.id);
        if (v != null) means.push({t, date: monthDate(t), value: v});
      }
      const flags = [{t0: 0, t1: EARLY_LAST, x1: monthDate(0), x2: monthDate(EARLY_LAST + 1), what: "Before 1970"}];
      if (sel.flaggedProv) flags.push({t0: EARLY_LAST + 1, t1: layer.step_1984_last_position, x1: monthDate(EARLY_LAST + 1), x2: monthDate(layer.step_1984_last_position + 1), what: "Before the 1984 change"});
      return {legendItems, rows, means, flags};
    })()
  : null;
```

```js
// Years on show: an overview of the whole record with a window to drag. Built here, in a block that does
// not read `timeRange`, so moving the window never rebuilds the slider under the reader's pointer.
if (sel) {
  display(html`<h2 id="over-time">Over time</h2><div class="card">
    <div class="fine"><strong>Years shown in the charts.</strong> Drag the window to move it, or drag one of its edges to show more or fewer years. The shape behind it is ${unit.name}'s mean ${layer.label} since 1950: warm below the line for ${DRYW}, cool above for ${WETW}.</div>
    ${resize((w) => timeSlider({
      width: w, last: LAST, minSpan: 12,
      values: series.means.map((d) => ({t: d.t, wet: -d.value * layer.dry_sign})),
      colours: {dry: DRY[1], wet: WET[1], ink: INK.muted, axis: INK.axis, window: "#2a78d6"},
      onChange: (a, b) => setTimeRange(a, b)
    }))}
  </div>`);
} else {
  display(html`<div></div>`); // always display: a block that displays nothing keeps its previous output on screen
}
```

```js
if (sel) {
  const [t0, t1] = timeRange;
  const xDomain = [monthDate(t0), monthDate(t1 + 1)];
  const inRange = (d) => d.t >= t0 - 1 && d.t <= t1 + 1; // one month of margin so lines run to the frame
  const rows = series.rows.filter(inRange);
  const means = series.means.filter(inRange);
  const events = sel.ev.filter((e) => e.end >= t0 && e.start <= t1 && (show === "both" || (show === "dry") === (e.side === 0)));
  const domain = series.legendItems.map((d) => d.label);
  const range = series.legendItems.map((d) => d.colour);
  const flagsShown = series.flags.filter((f) => f.t1 >= t0 && f.t0 <= t1);
  const flagMarks = (y1, y2) => [
    Plot.rect(flagsShown, {x1: "x1", x2: "x2", y1, y2, fill: "#898781", fillOpacity: 0.12, clip: true}),
    Plot.text(flagsShown, {x: (f) => monthDate(Math.max(f.t0, t0)), y: y2, text: "what", textAnchor: "start", dx: 4, dy: 10, fill: INK.muted, fontSize: 10})
  ];
  // click a chart: the map and everything else move to that month. The years on show are set by the slider.
  const hooks = {onPick: (date) => setMonth(monthOf(date))};
  // all four accumulation periods, as one coloured strip per period. Colour is the mean index on a continuous
  // dry-to-wet scale, not a class: `wet` is the index with its sign arranged so that positive is always the wet
  // (or low demand) side, whatever the index.
  const stripLabel = (sc) => `${sc === scale ? "\u25B8 " : ""}${monthsText(sc)}`;
  const strip = [];
  for (const sc of SCALES) {
    for (let t = Math.max(0, t0 - 1); t <= Math.min(LAST, t1 + 1); t++) {
      const v = scaleMean(sc, t);
      if (v != null) strip.push({t, date: monthDate(t), date2: monthDate(t + 1), label: stripLabel(sc), value: v, wet: -v * layer.dry_sign, pct: percentileOf(v)});
    }
  }
  const stripColour = d3.interpolateRgbBasis([...DRY.slice().reverse(), NORMAL, ...WET]);
  // EDDI is drawn here as a percentile, 0 to 100 (100 = highest demand), as the EDDI user guide presents it.
  // The value is the percentile equivalent of the unit's mean EDDI: 100 x the standard normal probability of it,
  // which is how the source files define the percentile. SPI and SPEI keep the index value.
  const asPercentile = index === "eddi";
  const ordinal = (n) => `${n}${n % 100 >= 11 && n % 100 <= 13 ? "th" : ["th", "st", "nd", "rd"][n % 10] ?? "th"}`;
  const stripScale = asPercentile
    ? {type: "linear", domain: [0, 100], clamp: true, interpolate: (u) => stripColour(1 - u), legend: true, ticks: [0, 10, 30, 50, 70, 90, 100],
       label: "EDDI percentile (0 = lowest evaporative demand, 100 = highest)"}
    : {type: "linear", domain: [-2.5, 2.5], clamp: true, interpolate: stripColour, legend: true,
       label: `Mean ${index.toUpperCase()} (dry to the left)`, tickFormat: (d) => `${(-d * layer.dry_sign).toFixed(1).replace("-0.0", "0.0")}`};
  display(html`<div class="grid grid-cols-1">
  <div class="card">
    <h3>Share of area by class</h3>
    <div class="fine">Each bar is one month: how ${unit.name}'s cell area divides among the classes. Every bar adds to 100%, with ${DRYW} classes at the top and ${WETW} classes at the bottom. Washed-out bars fall in less reliable periods. Showing ${monthLabel(t0)} to ${monthLabel(t1)}${month < t0 || month > t1 ? `; the selected month, ${monthLabel(month)}, is outside these years` : ""}. Click a chart to move the map to that month.</div>
    ${resize((w) => timeInteractions(Plot.plot({
      width: w, height: 280, marginLeft: 44,
      x: {type: "utc", label: null, domain: xDomain},
      y: {label: "% of area", domain: [0, 100], grid: true},
      color: {domain, range, legend: true},
      marks: [
        Plot.rect(rows, {x1: "date", x2: "date2", y1: "y1", y2: "y2", fill: "label", clip: true}),
        // less reliable periods are washed out on top of the bars, as they are on the map
        Plot.rect(flagsShown, {x1: "x1", x2: "x2", y1: 0, y2: 100, fill: "#fcfcfb", fillOpacity: 0.55, clip: true}),
        Plot.text(flagsShown, {x: (f) => monthDate(Math.max(f.t0, t0)), y: 100, text: "what", textAnchor: "start", dx: 4, dy: 10, fill: INK.primary, fontSize: 10}),
        Plot.ruleX(month >= t0 && month <= t1 ? [monthDate(month)] : [], {stroke: INK.primary, strokeWidth: 1.5}),
        Plot.tip(rows, Plot.pointerX({x: "date", y: (d) => (d.y1 + d.y2) / 2, title: (d) => `${d.date.toISOString().slice(0, 7)}\n${d.label}: ${d.value.toFixed(0)}%`}))
      ]
    }), hooks))}
  </div>
  <div class="card">
    <h3>Mean ${layer.label} over ${areaWord}, with events</h3>
    <div class="fine">Bars mark events: an event begins in the first month the mean reaches ${index === "eddi" ? "+1.0 or -1.0" : "-1.0 or +1.0"} and ends when it crosses zero. ${index === "eddi" ? "Positive is high evaporative demand." : "Negative is dry."} Faded bars fall in less reliable periods.</div>
    ${resize((w) => timeInteractions(Plot.plot({
      width: w, height: 240, marginLeft: 44,
      x: {type: "utc", label: null, domain: xDomain},
      y: {label: layer.label, domain: [-3.2, 3.2], grid: true},
      marks: [
        ...flagMarks(-3.2, 3.2),
        Plot.rect(events, {
          x1: (e) => monthDate(e.start), x2: (e) => monthDate(e.end + 1),
          y1: (e) => ((e.side === 0) === (layer.dry_sign < 0) ? -3.2 : 2.9), y2: (e) => ((e.side === 0) === (layer.dry_sign < 0) ? -2.9 : 3.2),
          fill: (e) => (e.side === 0 ? DRY[3] : WET[3]), fillOpacity: (e) => (e.flagged ? 0.3 : 1), clip: true,
          title: (e) => `${e.side === 0 ? DRYW : WETW} event\n${ym(e.start)} to ${ym(e.end)}${e.open ? " (still running)" : ""}\n${monthsText(e.duration)}, peak ${e.peak.toFixed(2)}\n${e.flagged ? "less reliable period" : ""}`
        }),
        Plot.ruleY([-1, 1], {stroke: INK.axis, strokeDasharray: "3,3"}),
        Plot.ruleY([0], {stroke: INK.axis}),
        Plot.lineY(means, {x: "date", y: "value", stroke: INK.secondary, strokeWidth: 1, clip: true}),
        Plot.ruleX(month >= t0 && month <= t1 ? [monthDate(month)] : [], {stroke: INK.primary, strokeWidth: 1.5}),
        Plot.tip(means, Plot.pointerX({x: "date", y: "value", title: (d) => `${d.date.toISOString().slice(0, 7)}\n${layer.label} ${d.value.toFixed(2)}`}))
      ]
    }), hooks))}
  </div>
  <div class="card">
    <h3>All four accumulation periods, ${index.toUpperCase()}</h3>
    <div class="fine">Mean ${index.toUpperCase()} over ${areaWord} at 1, 3, 6 and 12 months, month by month. The marked row is the period selected above. A short period can read as calm in a season that is normally almost dry while a longer one shows the deficit. ${index === "eddi" ? "EDDI is shown as a percentile from 0 to 100, as its user guide presents it: 100 is the highest evaporative demand, and the guide's drought categories start at 70 (ED0), 80, 90, 95 and 98 (ED4). Hover for the percentile and the index value together." : "Warm colours are dry."}</div>
    ${resize((w) => timeInteractions(Plot.plot({
      width: w, height: 170, marginLeft: 84,
      x: {type: "utc", label: null, domain: xDomain},
      y: {label: null, domain: SCALES.map(stripLabel)},
      color: stripScale,
      marks: [
        Plot.rect(strip, {
          x1: "date", x2: "date2", y: "label", fill: asPercentile ? "pct" : "wet", clip: true,
          title: (d) => {
            const period = d.label.replace("\u25B8 ", "").split(" ")[0];
            return asPercentile
              ? `${d.date.toISOString().slice(0, 7)}\nEDDI-${period}: ${ordinal(Math.round(d.pct))} percentile\nindex value ${d.value.toFixed(2)}`
              : `${d.date.toISOString().slice(0, 7)}\n${index.toUpperCase()}-${period}: ${d.value.toFixed(2)}`;
          }
        }),
        Plot.ruleX(month >= t0 && month <= t1 ? [monthDate(month)] : [], {stroke: INK.primary, strokeWidth: 1.5})
      ]
    }), hooks))}
  </div>
  </div>`);
} else {
  display(html`<div></div>`); // always display: a block that displays nothing keeps its previous output on screen
}
```

```js
// Trend: the unit's index averaged by calendar year, on the years outside the less reliable periods.
// Theil-Sen slope (the median of the slopes between every pair of years) and the Mann-Kendall test, both on
// those annual values. Computed here from at most 56 numbers of the unit's stored mean series.
if (sel) {
  const from = reliableFrom(sel.flaggedProv);
  const y0 = 1950 + Math.ceil(from / 12);
  const years = [];
  for (let y = y0; y <= 2025; y++) {
    let sum = 0, k = 0;
    for (let m = 0; m < 12; m++) { const v = meanAt(ds, (y - 1950) * 12 + m, sel.id); if (v != null) { sum += v; k++; } }
    if (k === 12) years.push({year: y, date: new Date(Date.UTC(y, 6, 1)), value: sum / 12});
  }
  const nY = years.length;
  let card = html`<div class="card"><h3>Trend</h3><div class="fine">Too few complete years outside the less reliable periods to estimate a trend.</div></div>`;
  if (nY >= 20) {
    const slopes = [];
    let S = 0;
    for (let i = 0; i < nY - 1; i++) for (let j = i + 1; j < nY; j++) {
      slopes.push((years[j].value - years[i].value) / (years[j].year - years[i].year));
      S += Math.sign(years[j].value - years[i].value);
    }
    slopes.sort((a, b) => a - b);
    const slope = d3.median(slopes);
    const mid = d3.median(years, (d) => d.value) - slope * d3.median(years, (d) => d.year);
    const sd = Math.sqrt((nY * (nY - 1) * (2 * nY + 5)) / 18);
    const z = S > 0 ? (S - 1) / sd : S < 0 ? (S + 1) / sd : 0;
    const pval = 2 * (1 - percentileOf(Math.abs(z)) / 100);
    const perDecade = slope * 10;
    const toward = perDecade * layer.dry_sign > 0 ? (index === "eddi" ? "higher evaporative demand" : "drier conditions") : (index === "eddi" ? "lower evaporative demand" : "wetter conditions");
    const line = [{date: years[0].date, value: mid + slope * years[0].year}, {date: years[nY - 1].date, value: mid + slope * years[nY - 1].year}];
    const first = d3.mean(years.slice(0, 10), (d) => d.value), last = d3.mean(years.slice(-10), (d) => d.value);
    card = html`<div class="card">
      <h3>Trend: annual mean ${layer.label}, ${y0} to 2025</h3>
      <div class="fine">Each bar is the mean of the twelve monthly values of a year. Over these ${nY} years the annual mean moved by ${perDecade >= 0 ? "+" : "−"}${Math.abs(perDecade).toFixed(2)} per decade, toward ${toward} (Theil-Sen slope; Mann-Kendall p ${pval < 0.001 ? "below 0.001" : `= ${pval.toFixed(3)}`}). The first ten of these years average ${first.toFixed(2)} and the last ten ${last.toFixed(2)}. ${pval < 0.05 ? "A trend this size is unlikely to be chance alone, but that does not say what caused it." : "A trend this size could be chance."} ${index === "eddi" ? "Evaporative demand rises with temperature, so part of an EDDI trend is warming." : "The recent wetter years also appear in rain gauges and in a second rainfall product checked for this project; the earlier decades are less certain."} Years in the less reliable periods are left out.</div>
      ${resize((w) => Plot.plot({
        width: w, height: 220, marginLeft: 44,
        x: {type: "utc", label: null},
        y: {label: `Annual mean ${layer.label}`, grid: true, nice: true},
        marks: [
          Plot.rectY(years, {x1: (d) => new Date(Date.UTC(d.year, 0, 15)), x2: (d) => new Date(Date.UTC(d.year, 11, 15)), y: "value",
            fill: (d) => (d.value * layer.dry_sign > 0 ? DRY[2] : WET[2]), title: (d) => `${d.year}: ${d.value.toFixed(2)}`}),
          Plot.ruleY([0], {stroke: INK.axis}),
          Plot.line(line, {x: "date", y: "value", stroke: INK.primary, strokeWidth: 1.5, strokeDasharray: pval < 0.05 ? null : "4,3"})
        ]
      }))}
    </div>`;
  }
  display(card);
} else {
  display(html`<div></div>`); // always display: a block that displays nothing keeps its previous output on screen
}
```

```js
if (sel) {
  const row = (s, word) => s ? html`<tr>
    <td>${word[0].toUpperCase() + word.slice(1)}</td>
    <td>${s.n_events}</td><td>${s.n_events_unflagged}</td>
    <td>${s.longest_months == null ? "none" : `${monthsText(s.longest_months)} from ${s.longest_start}${s.longest_is_open ? ", so far" : ""}`}</td>
    <td>${s.longest_unflagged_months == null ? "none" : `${monthsText(s.longest_unflagged_months)} from ${s.longest_unflagged_start}${s.longest_unflagged_is_open ? ", so far" : ""}`}</td>
    <td>${s.share_of_months_in_events == null ? "no data" : `${(s.share_of_months_in_events * 100).toFixed(0)}%`}</td></tr>` : html`<span></span>`;
  display(html`<h2 id="events">Past events</h2><div class="card"><h3>Events on record, ${unit.name}, ${layer.label}</h3>
  <table><thead><tr><th>Side</th><th>Events</th><th>Outside less reliable periods</th><th>Longest</th><th>Longest outside less reliable periods</th><th>Share of months inside an event</th></tr></thead>
  <tbody>${show === "wet" ? "" : row(sel.sumDry, DRYW)}${show === "dry" ? "" : row(sel.sumWet, WETW)}</tbody></table>
  <div class="fine">Being inside an event is not the same as being ${DRYW} this month: an event runs from the first month at the onset level until the index crosses zero.</div></div>`);
} else {
  display(html`<div></div>`); // always display: a block that displays nothing keeps its previous output on screen
}
```

```js
// How severe were the events: the run-theory measures of every event of the selected unit.
//   duration   months from the first month at the onset level to the last month before the index crosses zero
//   magnitude  sum of the absolute mean index over those months (index-months)
//   intensity  magnitude divided by duration
//   peak       the most extreme monthly mean during the event
// All are computed in pipeline/events.py on the unit's mean index and only read here.
if (sel) {
  const sideOf = (e) => (e.side === 0 ? "dry" : "wet");
  const wordOf = (e) => (e.side === 0 ? DRYW : WETW);
  const evs = sel.ev
    .filter((e) => show === "both" || show === sideOf(e))
    .map((e) => ({...e, word: wordOf(e), intensity: e.magnitude / e.duration, decade: 1950 + Math.floor(e.start / 120) * 10, current: sel.now != null && e.start === sel.now.start && e.side === sel.now.side}));
  const ranked = evs.slice().sort((a, b) => b.magnitude - a.magnitude);
  const rankOf = new Map(ranked.map((e, i) => [e, i + 1]));
  const top = ranked.slice(0, 10);
  const goTo = (e) => (ev) => {
    ev.preventDefault();
    const span = timeRange[1] - timeRange[0] + 1;
    const mid = Math.round((e.start + e.end) / 2);
    setTimeRange(mid - Math.floor(span / 2), mid - Math.floor(span / 2) + span - 1);
    setMonth(e.start);
  };
  const sideColour = {domain: [cap(DRYW), cap(WETW)], range: [DRY[3], WET[3]]};
  const decades = d3.range(1950, 2030, 10);
  const perDecade = [];
  for (const dcd of decades) for (const side of ["dry", "wet"]) {
    if (show !== "both" && show !== side) continue;
    for (const fl of [0, 1]) {
      const k = evs.filter((e) => e.decade === dcd && sideOf(e) === side && e.flagged === fl).length;
      if (k) perDecade.push({decade: `${dcd}s`, side: cap(side === "dry" ? DRYW : WETW), flagged: fl, n: k});
    }
  }
  const nowRank = sel.now ? evs.find((e) => e.current) : null;
  display(evs.length ? html`<div class="card">
    <h3>How severe: every event of ${unit.name}, ${layer.label}</h3>
    <div class="fine">Each dot is one event. Duration is counted in months; magnitude is the sum of the absolute mean index over those months, so a long mild event and a short sharp one can have the same magnitude. Faded dots fall in less reliable periods.${nowRank ? ` The ringed dot is the event running in ${monthLabel(month)}: it ranks ${rankOf.get(nowRank)} of ${evs.length} by magnitude${nowRank.open ? ", and is still running at the end of the record" : ""}.` : ""}</div>
    ${resize((w) => Plot.plot({
      width: w, height: 300, marginLeft: 48, marginBottom: 40,
      x: {label: "Duration, months", grid: true, nice: true},
      y: {label: "Magnitude, index-months", grid: true, nice: true},
      color: {...sideColour, legend: true},
      marks: [
        Plot.dot(evs, {x: "duration", y: "magnitude", fill: (e) => cap(e.word), fillOpacity: (e) => (e.flagged ? 0.25 : 0.85), r: 4, stroke: "#fcfcfb", strokeWidth: 0.5}),
        Plot.dot(evs.filter((e) => e.current), {x: "duration", y: "magnitude", r: 8, stroke: INK.primary, strokeWidth: 1.5}),
        Plot.tip(evs, Plot.pointer({x: "duration", y: "magnitude", title: (e) => `${cap(e.word)} event\n${ym(e.start)} to ${ym(e.end)}${e.open ? " (still running)" : ""}\n${monthsText(e.duration)}, magnitude ${e.magnitude.toFixed(1)}\npeak ${e.peak.toFixed(2)}, intensity ${e.intensity.toFixed(2)}${e.flagged ? "\nless reliable period" : ""}`}))
      ]
    }))}
    <h3 style="margin-top: 1.4rem;">The ${top.length} largest by magnitude</h3>
    <div class="fine">Click a start month to move the map and the charts to it. Peak is the most extreme monthly mean during the event, shown without its sign; intensity is magnitude divided by duration; peak share is the largest share of the area in a class on the event's own side in any month of the event.</div>
    <table><thead><tr><th>Rank</th><th>Side</th><th>From</th><th>To</th><th>Duration</th><th>Magnitude</th><th>Intensity</th><th>Peak</th><th>Peak share of area</th><th>Note</th></tr></thead>
    <tbody>${top.map((e, i) => html`<tr style=${e.current ? "font-weight: 600;" : ""}>
      <td>${i + 1}</td><td>${cap(e.word)}</td>
      <td><a href="#" onclick=${goTo(e)}>${ym(e.start)}</a></td><td>${e.open ? "running" : ym(e.end)}</td>
      <td>${monthsText(e.duration)}</td><td>${e.magnitude.toFixed(1)}</td><td>${e.intensity.toFixed(2)}</td><td>${e.peak.toFixed(2)}</td>
      <td>${e.max_share == null ? "no data" : `${(e.max_share * 100).toFixed(0)}%`}</td>
      <td>${[e.flagged ? "less reliable period" : "", e.open ? "still running, figures so far" : ""].filter(Boolean).join("; ")}</td></tr>`)}</tbody></table>
    <h3 style="margin-top: 1.4rem;">Events that started in each decade</h3>
    <div class="fine">A count, not a rate of return: ${evs.length} events in 76 years is too few to estimate one. The 2020s hold six years only. Faded bars are events in less reliable periods.</div>
    ${resize((w) => Plot.plot({
      width: w, height: 200, marginLeft: 48,
      x: {label: null, domain: decades.map((d) => `${d}s`)},
      fx: {label: null, domain: show === "both" ? [cap(DRYW), cap(WETW)] : [cap(show === "dry" ? DRYW : WETW)]},
      y: {label: "Events", grid: true, interval: 1},
      color: sideColour,
      marks: [
        Plot.barY(perDecade, {x: "decade", fx: "side", y: "n", fill: "side", fillOpacity: (d) => (d.flagged ? 0.3 : 1), order: (d) => d.flagged, title: (d) => `${d.decade}: ${d.n} ${d.side.toLowerCase()} event${d.n === 1 ? "" : "s"}${d.flagged ? " in a less reliable period" : ""}`}),
        Plot.ruleY([0])
      ]
    }))}
  </div>` : html`<div class="card"><h3>How severe</h3><div class="fine">No event on record for ${unit.name} at this index and period.</div></div>`);
} else {
  display(html`<div></div>`); // always display: a block that displays nothing keeps its previous output on screen
}
```

```js
// ENSO: the Relative Oceanic Nino Index and its El Nino and La Nina episodes, built by pipeline/step5_enso.py
// from the tables of the `nino` repo (NOAA CPC files). phase: +1 El Nino, -1 La Nina, 0 neutral.
const enso = await FileAttachment("./data/enso.json").json();
const PHASES = [{p: 1, name: "El Niño", colour: "#c0392b"}, {p: 0, name: "Neutral", colour: "#898781"}, {p: -1, name: "La Niña", colour: "#2563c9"}];
const phaseName = (p) => PHASES.find((x) => x.p === p).name;
const phaseScale = {domain: PHASES.map((x) => x.name), range: PHASES.map((x) => x.colour)};
const MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
// first month outside the less reliable periods, for a unit: comparisons with ENSO use only months from here on
const reliableFrom = (flagged) => (flagged ? layer.step_1984_last_position : EARLY_LAST) + 1;
```

<h2 id="enso">El Niño and La Niña</h2>

```js
// ENSO and the selected unit
if (sel) {
  const [t0, t1] = timeRange;
  const xDomain = [monthDate(t0), monthDate(t1 + 1)];
  const from = reliableFrom(sel.flaggedProv);
  const sgn = layer.dry_sign;                       // index x sgn is positive on the dry side
  const dryLevel = (v) => v * sgn >= 1, wetLevel = (v) => v * sgn <= -1;
  // A. RONI over the years on show
  const roni = [];
  for (let t = Math.max(0, t0 - 1); t <= Math.min(LAST, t1 + 1); t++) roni.push({t, date: monthDate(t), value: enso.roni[t], phase: phaseName(enso.phase[t])});
  const episodes = enso.events.filter((e) => e.end >= t0 && e.start <= t1);
  // B. the unit's mean index by calendar month and phase
  const acc = new Map();
  for (let t = from; t <= LAST; t++) {
    const v = meanAt(ds, t, sel.id);
    if (v == null) continue;
    const key = `${t % 12}|${enso.phase[t]}`;
    const a = acc.get(key) ?? {m: t % 12, p: enso.phase[t], sum: 0, n: 0};
    a.sum += v; a.n += 1;
    acc.set(key, a);
  }
  const composite = [...acc.values()].map((a) => ({month: MONTH_NAMES[a.m], m: a.m, phase: phaseName(a.p), mean: a.sum / a.n, n: a.n})).sort((a, b) => a.m - b.m);
  // C. every episode: what the unit did during it
  const rows = enso.events.filter((e) => e.end >= from).map((e) => {
    let driest = null, wettest = null, nDry = 0, nWet = 0, n = 0;
    for (let t = Math.max(e.start, from); t <= e.end; t++) {
      const v = meanAt(ds, t, sel.id);
      if (v == null) continue;
      n++;
      if (driest == null || v * sgn > driest.v * sgn) driest = {v, t};
      if (wettest == null || v * sgn < wettest.v * sgn) wettest = {v, t};
      if (dryLevel(v)) nDry++;
      if (wetLevel(v)) nWet++;
    }
    return {...e, driest, wettest, nDry, nWet, n};
  }).filter((r) => r.n > 0).reverse();
  const tally = (p, key) => { const r = rows.filter((x) => x.phase === p); return `${r.filter((x) => x[key] > 0).length} of ${r.length}`; };
  const goTo = (e) => (ev) => {
    ev.preventDefault();
    const span = timeRange[1] - timeRange[0] + 1;
    const mid = Math.round((e.start + e.end) / 2);
    setTimeRange(mid - Math.floor(span / 2), mid - Math.floor(span / 2) + span - 1);
    setMonth(e.peak <= LAST ? e.peak : e.start);
  };
  const hooks = {onPick: (date) => setMonth(monthOf(date))};
  const f2 = (x) => x.toFixed(2).replace(/^-0\.00$/, "0.00");
  const lvl = (x) => (x * sgn).toFixed(1).replace("-", "−");
  display(html`<div class="card">
    <h3>El Niño and La Niña: ${unit.name}, ${layer.label}</h3>
    <div class="fine">The Relative Oceanic Niño Index (RONI) measures how warm or cold the central equatorial Pacific is against the rest of the tropics. An episode is five or more overlapping three-month seasons at or beyond +0.5 (El Niño, red) or −0.5 (La Niña, blue). The years shown are the ones the charts above show; click to move the map to a month.</div>
    ${resize((w) => timeInteractions(Plot.plot({
      width: w, height: 170, marginLeft: 44,
      x: {type: "utc", label: null, domain: xDomain},
      y: {label: "RONI, °C", domain: [-2.6, 2.6], grid: true},
      color: {...phaseScale, legend: true},
      marks: [
        Plot.rect(episodes, {x1: (e) => monthDate(e.start), x2: (e) => monthDate(e.end + 1), y1: -2.6, y2: 2.6, fill: (e) => phaseName(e.phase), fillOpacity: 0.14, clip: true,
          title: (e) => `${phaseName(e.phase)}, ${e.strength}\n${ym(e.start)} to ${e.runs_past_record ? "beyond 2025-12" : ym(e.end)}\npeak RONI ${e.peak_value}`}),
        Plot.ruleY([-0.5, 0.5], {stroke: INK.axis, strokeDasharray: "3,3"}),
        Plot.ruleY([0], {stroke: INK.axis}),
        Plot.lineY(roni, {x: "date", y: "value", stroke: INK.secondary, strokeWidth: 1.2, clip: true}),
        Plot.ruleX(month >= t0 && month <= t1 ? [monthDate(month)] : [], {stroke: INK.primary, strokeWidth: 1.5}),
        Plot.tip(roni, Plot.pointerX({x: "date", y: "value", title: (d) => `${d.date.toISOString().slice(0, 7)}\nRONI ${d.value.toFixed(2)}, ${d.phase}`}))
      ]
    }), hooks))}
    <h3 style="margin-top: 1.4rem;">Mean ${layer.label} by calendar month, in each phase</h3>
    <div class="fine">Each point is the average of ${areaWord}'s mean ${layer.label} over every month of that name that fell in the phase, from ${monthLabel(from)} on (earlier months are in a less reliable period). Where the red and blue lines part, the phase has gone with a different outcome here; where they run together, it has not. ${scale > 1 ? `A ${scale}-month value covers the ${scale} months ending in the month named.` : ""} ${index === "eddi" ? "Positive is high evaporative demand." : "Negative is dry."} Hover for the number of months behind a point: some are few.</div>
    ${resize((w) => Plot.plot({
      width: w, height: 260, marginLeft: 48,
      x: {label: null, domain: MONTH_NAMES, type: "point"},
      y: {label: `Mean ${layer.label}`, grid: true, nice: true},
      color: phaseScale,
      marks: [
        Plot.ruleY([0], {stroke: INK.axis}),
        Plot.lineY(composite, {x: "month", y: "mean", stroke: "phase", strokeWidth: 2}),
        Plot.dot(composite, {x: "month", y: "mean", fill: "phase", r: 3.5, stroke: "#fcfcfb"}),
        Plot.text(composite.filter((d) => d.m === 11), {x: "month", y: "mean", text: "phase", fill: "phase", dx: 8, textAnchor: "start", fontSize: 11}),
        Plot.tip(composite, Plot.pointer({x: "month", y: "mean", title: (d) => `${d.month}, ${d.phase}\nmean ${d.mean.toFixed(2)} over ${d.n} month${d.n === 1 ? "" : "s"}`}))
      ],
      marginRight: 60
    }))}
    <h3 style="margin-top: 1.4rem;">Episode by episode</h3>
    <div class="fine">Since ${monthLabel(from)}: in ${tally(1, "nDry")} El Niño episodes ${areaWord}'s mean reached the ${DRYW} onset level (${lvl(1)}) in at least one month, and in ${tally(1, "nWet")} the ${WETW} one. In La Niña episodes: ${DRYW} in ${tally(-1, "nDry")}, ${WETW} in ${tally(-1, "nWet")}. These are counts of what happened, not a forecast. Click an episode to go to its peak.</div>
    <div style="max-height: 340px; overflow-y: auto;">
    <table><thead><tr><th>Episode</th><th>From</th><th>To</th><th>Peak RONI</th><th>Strength</th><th>${index === "eddi" ? "Highest demand" : "Driest month"}</th><th>Months at ${DRYW} level</th><th>${index === "eddi" ? "Lowest demand" : "Wettest month"}</th><th>Months at ${WETW} level</th></tr></thead>
    <tbody>${rows.map((r) => html`<tr>
      <td style=${`color: ${PHASES.find((x) => x.p === r.phase).colour}; font-weight: 600;`}>${phaseName(r.phase)}</td>
      <td><a href="#" onclick=${goTo(r)}>${ym(r.start)}</a></td><td>${r.runs_past_record ? "running" : ym(r.end)}</td>
      <td>${r.peak_value.toFixed(2)}</td><td>${r.strength}</td>
      <td>${f2(r.driest.v)} in ${ym(r.driest.t)}</td><td>${r.nDry} of ${r.n}</td>
      <td>${f2(r.wettest.v)} in ${ym(r.wettest.t)}</td><td>${r.nWet} of ${r.n}</td></tr>`)}</tbody></table>
    </div>
  </div>`);
} else {
  display(html`<div></div>`); // always display: a block that displays nothing keeps its previous output on screen
}
```

```js
// ENSO across the units on show: provinces at national level, the kabupaten of an open province.
// For each unit: its mean index over El Nino months minus its mean over La Nina months, on the dry side
// (positive = drier in El Nino). Months in less reliable periods are left out, per unit.
{
  const level = !prov ? {d: d1, list: units, word: "province"} : !kab ? {d: d2, list: d2.kids.map((id) => unit2ById.get(id)).filter((u) => u && u.assigned), word: "kabupaten or kota"} : null;
  if (level) {
    const sgn = layer.dry_sign;
    const rows = [];
    for (const u of level.list) {
      const from = reliableFrom(u.step_1984_majority);
      let sE = 0, nE = 0, sL = 0, nL = 0;
      for (let t = from; t <= LAST; t++) {
        const p = enso.phase[t];
        if (p === 0) continue;
        const v = meanAt(level.d, t, u.id);
        if (v == null) continue;
        if (p === 1) { sE += v; nE++; } else { sL += v; nL++; }
      }
      if (nE && nL) rows.push({name: u.name, id: u.id, el: sE / nE, la: sL / nL, diff: (sE / nE - sL / nL) * sgn, nE, nL});
    }
    rows.sort((a, b) => b.diff - a.diff);
    const pick = (r) => (!prov ? selectProvince(r.id) : selectKab(r.id));
    display(html`<div class="card">
      <h3>Where El Niño and La Niña differ most: ${layer.label}, by ${level.word}${prov ? ` in ${prov.name}` : ""}</h3>
      <div class="fine">For each ${level.word}: its mean ${layer.label} over all El Niño months minus its mean over all La Niña months, with the sign arranged so that a bar to the right means ${index === "eddi" ? "higher evaporative demand" : "drier"} in El Niño. All calendar months are pooled, so a place whose response is confined to one season shows a shorter bar than that season alone would give; select a ${level.word} for the month-by-month view. Months in less reliable periods are left out. A difference, not a test of significance: there are ${enso.counts.el_nino_events} El Niño and ${enso.counts.la_nina_events} La Niña episodes in the whole record.</div>
      ${resize((w) => {
        const p = Plot.plot({
          width: w, height: Math.max(180, rows.length * 16 + 50), marginLeft: 190, marginRight: 40,
          x: {label: `El Niño minus La Niña, ${layer.label} (right = ${index === "eddi" ? "higher demand" : "drier"} in El Niño)`, grid: true, nice: true},
          y: {label: null, domain: rows.map((r) => r.name)},
          marks: [
            Plot.barX(rows, {y: "name", x: "diff", fill: (r) => (r.diff >= 0 ? DRY[3] : WET[3]),
              title: (r) => `${r.name}\nEl Niño months: mean ${r.el.toFixed(2)} (${r.nE})\nLa Niña months: mean ${r.la.toFixed(2)} (${r.nL})`}),
            Plot.ruleX([0], {stroke: INK.axis})
          ]
        });
        return p;
      })}
      <div class="fine" style="margin-top: 0.6rem;">Open one: ${rows.slice(0, 5).map((r, i) => html`${i ? ", " : ""}<a href="#" onclick=${(e) => { e.preventDefault(); pick(r); }}>${r.name}</a>`)} (the five largest).</div>
    </div>`);
  } else {
    display(html`<div></div>`);
  }
}
```

<h2 id="how-to-read">How to read this</h2>

<details><summary>The three indices</summary>

- **SPI** standardises rainfall. Negative is dry.
- **SPEI** standardises rainfall minus potential evapotranspiration. Negative is dry. Here it uses the SPI class table, which is a working choice, not a published standard for SPEI.
- **EDDI** standardises evaporative demand alone. **Positive is high demand.** Its cool side is low demand, which is not the same as wet. Its outermost categories cannot occur with a 30-year baseline and are left out of the legend.

SPEI shares rainfall with SPI and evaporative demand with EDDI, so two of them agreeing is not independent confirmation.

</details>

<details><summary>Accumulation period</summary>

A short period has little room to move where the season is normally almost dry. In Indramayu, August and September 1997 had 3 mm and 1 mm of rain in a strong El Nino year, yet the 3-month SPI stayed above -1: the 1991 to 2020 median for those two months is 10 mm and 6 mm, and nearly half the baseline years had under 5 mm. The 6-month SPI and evaporative demand both show that season as dry. The WMO guide makes the same point: 1-month and 3-month SPI "may be misleading in regions where it is normally dry". The chart of all four accumulation periods is there for this reason.

The period is the window of months being summed, not how long a dry or wet spell has lasted. The World Meteorological Organization's guide describes 3-month SPI as "a seasonal estimation of precipitation" and 12-month SPI as reflecting "long-term precipitation patterns" ([WMO-No. 1090](https://library.wmo.int/records/item/39629-standardized-precipitation-index-user-guide), 2012). That wording is for SPI; it is used here as a plain label for the other two indices.

</details>

<details><summary>Classes, share of area and events</summary>

- SPI classes follow WMO-No. 1090, Table 1: moderately dry from -1.0, severely dry from -1.5, extremely dry from -2.0, and the mirror image for wet. EDDI categories are the ones stored with the data.
- **The share chart** shows one bar per month, divided among all the classes and adding to 100%.
- **Share of area** counts every 1/24 degree grid cell (about 21 square kilometres) that a boundary touches, each at its full area. Cells on a boundary count on both sides. For a small kabupaten or kota, and for almost every kecamatan, this means a handful of cells, much of them shared with neighbours, so its percentages are coarse.
- **Events** follow WMO-No. 1090 section 6.1: an event starts in the first month the index reaches -1.0 and ends when it becomes positive. Here the rule is applied to the mean index over the province, kabupaten or kecamatan, and it is extended to wet events and to SPEI and EDDI, which the guide does not cover.

</details>

<details><summary>Less reliable periods</summary>

Two parts of the record are kept but marked.

- **Before 1970, everywhere.** At the cells that hold rain gauges, TerraClimate's annual rainfall, measured against each one's own 1991 to 2020 normal, is about 10% of normal lower than the gauges in the 1950s and 4% lower in the 1960s. The 1950s gauges are almost all in Java.
- **Before 1984, in northern and central Sumatra and West Kalimantan.** TerraClimate's rainfall and evaporative demand both shift at the start of 1984 there. Three gauges inside the region read near normal in 1970 to 1983 where TerraClimate reads about 20% low. The edge of the region is gradual, there is no gauge check for West Kalimantan, and the cause has not been established.

Counts and longest events are given both for the whole record and outside these periods.

</details>

<div class="fine">Data built ${meta.created.slice(0, 10)}. Baseline 1991 to 2020. Boundaries are present-day and are projected back to 1950.</div>
