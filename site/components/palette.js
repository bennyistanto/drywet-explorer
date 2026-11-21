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

export const sideWord = (side, index) => (index === "eddi" ? (side === "dry" ? "high demand" : "low demand") : side);
