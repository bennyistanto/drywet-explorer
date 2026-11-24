// Colour by the job it does: polarity. Two arms and a neutral midpoint.
// Dry is always the warm arm and wet (or low demand) always the cool arm, for
// every index, so a colour never changes meaning when the index changes.
// Colour is chosen from each class's `side` and `rank` (distance from normal),
// never from its code: SPI and EDDI codes run in opposite directions.

export const DRY = ["#f3cfae", "#e9a56f", "#d9783c", "#b24d1c", "#74290c"]; // light to dark
export const WET = ["#b7d3f6", "#86b6ef", "#5598e7", "#256abf", "#104281"]; // light to dark
export const NORMAL = "#e7e6e1";
export const INK = {primary: "#0b0b0b", secondary: "#52514e", muted: "#898781", grid: "#e1e0d9", axis: "#c3c2b7"};

function hexToRgb(hex) {
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

/** Colour of each class of a layer, as {code -> hex}. `show` is "both", "dry" or "wet". */
export function classColours(classes, show = "both") {
  const maxRank = Math.max(...classes.map((c) => c.rank));
  const out = new Map();
  for (const c of classes) {
    let hex = NORMAL;
    if (c.side !== "normal" && (show === "both" || show === c.side)) {
      const ramp = c.side === "dry" ? DRY : WET;
      hex = ramp[Math.round(((c.rank - 1) / Math.max(maxRank - 1, 1)) * (ramp.length - 1))];
    }
    out.set(c.code, hex);
  }
  return out;
}

/** The same, as a lookup table of RGB triples indexed by class code (0 = no data, left transparent). */
export function classRgbTable(classes, show = "both") {
  const colours = classColours(classes, show);
  const table = new Uint8Array(3 * 256);
  for (const [code, hex] of colours) table.set(hexToRgb(hex), code * 3);
  return table;
}

/** Classes that can actually occur, ordered from the driest to the wettest (or highest to lowest demand). */
export function legendClasses(classes) {
  const dry = classes.filter((c) => c.side === "dry").sort((a, b) => b.rank - a.rank);
  const normal = classes.filter((c) => c.side === "normal");
  const wet = classes.filter((c) => c.side === "wet").sort((a, b) => a.rank - b.rank);
  return [...dry, ...normal, ...wet].filter((c) => c.occurs);
}

/** Plain-language class label. EDDI's stored labels (ED2, EW1) are codes, so they are spelled out. */
export function classLabel(c, index) {
  if (index !== "eddi") return c.label;
  if (c.side === "normal") return "Normal demand";
  const level = c.label.slice(2);
  return c.side === "dry" ? `High demand, ED${level}` : `Low demand, EW${level}`;
}

// Emerging hot spot categories (a test). Hot spots are clusters of dry values and keep the warm family; cold
// spots are clusters of wet values and keep the cool family. Within a family the eight categories need to be
// told apart, so hue shifts a little: this is a categorical legend, not a ramp.
const HOT = {1: "#f2c12e", 2: "#f08a24", 3: "#7b1113", 4: "#c0392b", 5: "#e8a798", 6: "#c98b5e", 7: "#9c6b98", 8: "#d9cdb8"};
const COLD = {1: "#7fe0d4", 2: "#2bb3a3", 3: "#0b2a66", 4: "#2563c9", 5: "#a9c4f0", 6: "#6f9bb8", 7: "#7d6bb8", 8: "#cfd8e3"};
const PATTERN_WORD = {1: "new", 2: "consecutive", 3: "intensifying", 4: "persistent", 5: "diminishing", 6: "sporadic", 7: "oscillating", 8: "historical"};

/** Colour and label of one stored hot spot code (category + 9). `show` greys the side not asked for. */
export function patternStyle(code, index, show = "both") {
  const cat = code - 9;
  if (cat === 0) return {colour: NORMAL, label: "No pattern"};
  const side = cat > 0 ? "dry" : "wet";
  const k = Math.abs(cat);
  const shown = show === "both" || show === side;
  // Hot and cold are measured against normal (mean 0 of the standardised index), so a hot spot is a
  // neighbourhood on the dry side of normal and a cold spot one on the wet side: they can carry those names.
  const word = sideWord(side, index);
  return {colour: shown ? (cat > 0 ? HOT : COLD)[k] : NORMAL, label: `${word[0].toUpperCase()}${word.slice(1)} cluster: ${PATTERN_WORD[k]}`, side, shown};
}

export function patternRgbTable(index, show = "both") {
  const table = new Uint8Array(3 * 256);
  for (let code = 1; code <= 17; code++) table.set(hexToRgb(patternStyle(code, index, show).colour), code * 3);
  return table;
}

// Event status and duration of each cell (pipeline/status.py). One stored code carries both:
// 0 no value, 1 no event, else 2 + side * 25 + state * 5 + bin (side 0 dry, 1 wet; state 4 is "ended").
const STATE_DRY = ["#f2c12e", "#7b1113", "#c0392b", "#e8a798", "#d9cdb8"];   // new, deepening, persisting, easing, ended
const STATE_WET = ["#7fe0d4", "#0b2a66", "#2563c9", "#a9c4f0", "#cfd8e3"];

/** Colour and label of one stored status code. mode: "status" or "howlong". meta: status.json. */
export function eventStyle(code, mode, index, show, meta) {
  if (code === 0) return {colour: null, label: "No value"};
  const k = code - 2;
  const side = code < 2 ? null : Math.floor(k / 25) === 0 ? "dry" : "wet";
  const state = code < 2 ? -1 : Math.floor((k % 25) / 5);
  const bin = k % 5;
  if (code === 1 || (mode === "howlong" && state === 4)) return {colour: NORMAL, label: "No event running"};
  const shown = show === "both" || show === side;
  const word = sideWord(side, index);
  const name = `${word[0].toUpperCase()}${word.slice(1)}`;
  if (mode === "howlong") return {colour: shown ? (side === "dry" ? DRY : WET)[bin] : NORMAL, label: `${name} event, ${meta.bins[bin].label}`, side, shown};
  return {colour: shown ? (side === "dry" ? STATE_DRY : STATE_WET)[state] : NORMAL, label: `${name} event: ${meta.states[state]}`, side, shown};
}

export function eventRgbTable(mode, index, show, meta) {
  const table = new Uint8Array(3 * 256);
  for (let code = 1; code <= 51; code++) table.set(hexToRgb(eventStyle(code, mode, index, show, meta).colour), code * 3);
  return table;
}

/** Legend for a status mode: the dry side from the most to the least advanced, no event, then the wet side. */
export function eventLegend(mode, index, show, meta) {
  const items = [];
  const order = mode === "howlong" ? [4, 3, 2, 1, 0] : [1, 2, 0, 3, 4];
  const codeOf = (side, j) => 2 + side * 25 + (mode === "howlong" ? j : j * 5);
  for (const j of order) items.push(eventStyle(codeOf(0, j), mode, index, show, meta));
  items.push(eventStyle(1, mode, index, show, meta));
  for (const j of order.slice().reverse()) items.push(eventStyle(codeOf(1, j), mode, index, show, meta));
  return items.map((s) => ({colour: s.colour, label: s.shown === false ? "Other side, not shown" : s.label}))
    .filter((s, i, a) => a.findIndex((o) => o.label === s.label) === i);
}

// Driver: which of the three indices is beyond the threshold in a cell (pipeline/step9_driver.py).
// Stored code: 0 no value, else 1 + spi + 3 * spei + 9 * eddi, each 0 neither, 1 dry side, 2 wet side.
// The grouping below is the legend: on each side, rain and demand together, rain alone, demand alone, or the
// water balance alone. SPEI rarely stands alone (about 1% of months), so it does not get groups of its own.
const DRIVER_DRY = ["#7b1113", "#e08a2e", "#f2c12e", "#d9cdb8"];   // both, rain alone, demand alone, balance only
const DRIVER_WET = ["#0b2a66", "#2563c9", "#7fe0d4", "#cfd8e3"];
const DRIVER_MIXED = "#9c6b98";
const DRIVER_LABEL = {
  dry: ["Dry: rain deficit and high demand", "Dry: rain deficit, demand not high", "Dry: high demand, rainfall not low", "Dry: water balance only"],
  wet: ["Wet: excess rain and low demand", "Wet: excess rain, demand not low", "Wet: low demand, rainfall not high", "Wet: water balance only"]
};
export const DRIVER_NONE = "No index at the threshold";
const DRIVER_MIXED_LABEL = "Mixed: dry on one index, wet on another";
const OTHER_SIDE = "Other side, not shown";

/** Group of a stored driver code on each side: 0 both, 1 rain alone, 2 demand alone, 3 balance only, -1 none. */
export function driverGroups(code) {
  const k = code - 1, spi = k % 3, spei = Math.floor(k / 3) % 3, eddi = Math.floor(k / 9);
  const g = (v) => (spi === v && eddi === v ? 0 : spi === v ? 1 : eddi === v ? 2 : spei === v ? 3 : -1);
  return {dry: g(1), wet: g(2), spi, spei, eddi};
}

/** Colour and label of one stored driver code (1..27). `show` is "both", "dry" or "wet". */
export function driverStyle(code, show = "both") {
  if (code === 0) return {colour: null, label: "No value"};
  const {dry, wet} = driverGroups(code);
  if (dry < 0 && wet < 0) return {colour: NORMAL, label: DRIVER_NONE};
  if (show === "both" && dry >= 0 && wet >= 0) return {colour: DRIVER_MIXED, label: DRIVER_MIXED_LABEL};
  if (show !== "wet" && dry >= 0) return {colour: DRIVER_DRY[dry], label: DRIVER_LABEL.dry[dry]};
  if (show !== "dry" && wet >= 0) return {colour: DRIVER_WET[wet], label: DRIVER_LABEL.wet[wet]};
  return {colour: NORMAL, label: OTHER_SIDE};
}

export function driverRgbTable(show = "both") {
  const table = new Uint8Array(3 * 256);
  for (let code = 1; code <= 27; code++) table.set(hexToRgb(driverStyle(code, show).colour), code * 3);
  return table;
}

/** Legend for the driver map: the dry side, nothing at the threshold, mixed, then the wet side. */
export function driverLegend(show = "both") {
  const items = [];
  if (show !== "wet") DRIVER_LABEL.dry.forEach((label, i) => items.push({colour: DRIVER_DRY[i], label}));
  items.push({colour: NORMAL, label: DRIVER_NONE});
  if (show === "both") items.push({colour: DRIVER_MIXED, label: DRIVER_MIXED_LABEL});
  else items.push({colour: NORMAL, label: OTHER_SIDE});
  if (show !== "dry") DRIVER_LABEL.wet.slice().reverse().forEach((label, i) => items.push({colour: DRIVER_WET[3 - i], label}));
  return items;
}

function driverScheme(show) {
  const items = driverLegend(show);
  const groupOf = new Uint8Array(256).fill(255);
  for (let code = 1; code <= 27; code++) groupOf[code] = items.findIndex((it) => it.label === driverStyle(code, show).label);
  const is = {
    dry: (c) => driverGroups(c).dry >= 0, wet: (c) => driverGroups(c).wet >= 0,
    dryStrong: (c) => driverGroups(c).dry === 0, wetStrong: (c) => driverGroups(c).wet === 0
  };
  const words = {
    title: "What is driving it", dry: "dry on at least one index", wet: "wet on at least one index",
    strong: "rain and demand together", strongText: "with rainfall and demand both beyond the threshold",
    dryCol: "dry, any index", wetCol: "wet, any index", thing: "signal"
  };
  // positions in `items` of the four drivers on each side, for the sentence that names them
  const at = (labels) => labels.map((l) => items.findIndex((it) => it.label === l));
  return {items, groupOf, is, words, driver: {dry: at(DRIVER_LABEL.dry), wet: at(DRIVER_LABEL.wet), mixed: at([DRIVER_MIXED_LABEL])[0]}};
}

/**
 * Everything the panels under the map need to summarise a map mode over a unit's cells.
 * mode: "howlong", "status", "pattern" or "driver". Returns
 *   items    the legend entries in order, each {colour, label}
 *   groupOf  Uint8Array: stored cell code -> position in items (255 = no value, left out of every share)
 *   is       predicates on a stored code, used for the headline figures: dry, wet (in an event or a cluster on
 *            that side, this month), dryStrong, wetStrong (see `strong`)
 *   words    the nouns and the meaning of "strong" for this mode
 */
export function modeScheme(mode, index, show, meta) {
  if (mode === "driver") return driverScheme(show);
  const pattern = mode === "pattern";
  const styleOf = (code) => (pattern ? patternStyle(code, index, show) : eventStyle(code, mode, index, show, meta));
  const order = pattern ? [10, 11, 12, 13, 14, 15, 16, 17, 9, 8, 7, 6, 5, 4, 3, 2, 1] : null;
  const labelOf = (s) => (s.shown === false ? "Other side, not shown" : s.label);
  const items = pattern
    ? order.map(styleOf).map((s) => ({colour: s.colour, label: labelOf(s)})).filter((s, i, a) => a.findIndex((o) => o.label === s.label) === i)
    : eventLegend(mode, index, show, meta);
  const groupOf = new Uint8Array(256).fill(255);
  for (let code = 1; code <= (pattern ? 17 : 51); code++) groupOf[code] = items.findIndex((it) => it.label === labelOf(styleOf(code)));
  const ev = (code) => { const k = code - 2; return {side: Math.floor(k / 25), state: Math.floor((k % 25) / 5), bin: k % 5}; };
  const dryW = sideWord("dry", index), wetW = sideWord("wet", index);
  const is = pattern
    ? {
        dry: (c) => c >= 10 && c <= 16, wet: (c) => c >= 2 && c <= 8,           // a cluster in the final month (historical is not)
        dryStrong: (c) => c === 10 || c === 11, wetStrong: (c) => c === 8 || c === 7
      }
    : mode === "howlong"
      ? {
          dry: (c) => c >= 2 && ev(c).side === 0 && ev(c).state !== 4, wet: (c) => c >= 2 && ev(c).side === 1 && ev(c).state !== 4,
          dryStrong: (c) => c >= 2 && ev(c).side === 0 && ev(c).state !== 4 && ev(c).bin >= 2,
          wetStrong: (c) => c >= 2 && ev(c).side === 1 && ev(c).state !== 4 && ev(c).bin >= 2
        }
      : {
          dry: (c) => c >= 2 && ev(c).side === 0 && ev(c).state !== 4, wet: (c) => c >= 2 && ev(c).side === 1 && ev(c).state !== 4,
          dryStrong: (c) => c >= 2 && ev(c).side === 0 && ev(c).state === 1, wetStrong: (c) => c >= 2 && ev(c).side === 1 && ev(c).state === 1
        };
  const words = pattern
    ? {title: "Space-time pattern", dry: `in a ${dryW} cluster`, wet: `in a ${wetW} cluster`, strong: "new or consecutive", strongText: "that was new or consecutive", dryCol: `${dryW} cluster`, wetCol: `${wetW} cluster`, thing: "cluster"}
    : mode === "howlong"
      ? {title: "How long events have run", dry: `in a ${dryW} event`, wet: `in a ${wetW} event`, strong: "6 months or more", strongText: "that had run 6 months or more", dryCol: `${dryW} event`, wetCol: `${wetW} event`, thing: "event"}
      : {title: "Status of events", dry: `in a ${dryW} event`, wet: `in a ${wetW} event`, strong: "deepening", strongText: "that was deepening", dryCol: `${dryW} event`, wetCol: `${wetW} event`, thing: "event"};
  return {items, groupOf, is, words};
}

/**
 * The value range of a class, as text, so that a legend says what a colour stands for.
 * SPI and SPEI: the index ranges of WMO-No. 1090, Table 1. EDDI: the percentile range of the NOAA category,
 * from the bounds stored in the EDDI files (0, 2, 5, 10, 20, 30, 70, 80, 90, 95, 98; EDDI User Guide v1.0).
 */
const SPI_RANGE = {1: ["1.0", "1.49"], 2: ["1.5", "1.99"], 3: ["2.0", null]};
const EDDI_PCT = {EW4: [0, 2], EW3: [2, 5], EW2: [5, 10], EW1: [10, 20], EW0: [20, 30], Normal: [30, 70], ED0: [70, 80], ED1: [80, 90], ED2: [90, 95], ED3: [95, 98], ED4: [98, 100]};
export function classRange(c, index) {
  if (index === "eddi") {
    const b = EDDI_PCT[c.label];
    return b ? `percentile ${b[0]} to ${b[1]}` : "";
  }
  if (c.side === "normal") return "−0.99 to 0.99";
  const r = SPI_RANGE[c.rank];
  if (!r) return "";
  const sign = c.side === "dry" ? "−" : "";
  return r[1] ? `${sign}${r[0]} to ${sign}${r[1]}` : c.side === "dry" ? `−${r[0]} or less` : `${r[0]} or more`;
}

/** Class label with its range in brackets: "moderately dry (-1.0 to -1.49)". */
export function classLabelRange(c, index) {
  const r = classRange(c, index);
  return r ? `${classLabel(c, index)} (${r})` : classLabel(c, index);
}

export const sideWord = (side, index) => (index === "eddi" ? (side === "dry" ? "high demand" : "low demand") : side);
