// Loading the binary files written by pipeline/step3_export.py.
// They are gzip-compressed, little-endian. A server may or may not already have
// decompressed a .gz file in transit, so the gzip magic bytes are checked first.

const cache = new Map();

async function bytes(file) {
  const buf = new Uint8Array(await file.arrayBuffer());
  if (buf.length > 2 && buf[0] === 0x1f && buf[1] === 0x8b) {
    const stream = new Blob([buf]).stream().pipeThrough(new DecompressionStream("gzip"));
    return new Uint8Array(await new Response(stream).arrayBuffer());
  }
  return buf;
}

/** Typed array from a file. `key` must be unique per file; results are cached. */
export function loadTyped(key, file, Type) {
  if (!cache.has(key)) {
    cache.set(
      key,
      bytes(file).then((u8) => {
        if (u8.byteLength % Type.BYTES_PER_ELEMENT !== 0) throw new Error(`${key}: length is not a multiple of the element size`);
        return new Type(u8.buffer, u8.byteOffset, u8.byteLength / Type.BYTES_PER_ELEMENT);
      })
    );
  }
  return cache.get(key);
}

/**
 * Kecamatan events arrive packed (see meta.encoding_adm3.events): a uint32 count, then one
 * column after another. This unpacks them into the same columnar shape the JSON event files have,
 * so the page reads every level through one function.
 */
export function decodeEvents(u8) {
  const n = new DataView(u8.buffer, u8.byteOffset, 4).getUint32(0, true);
  let at = 4;
  const u16 = () => { const a = new Uint16Array(u8.slice(at, at + 2 * n).buffer); at += 2 * n; return a; }; // slice copies, so the view is aligned
  const u8col = () => { const a = u8.subarray(at, at + n); at += n; return a; };
  const unit = u16(), start = u16(), end = u16(), mag = u16(), peak = u16(), share = u8col(), flags = u8col();
  if (at !== u8.byteLength) throw new Error("packed events: unexpected length");
  const out = {unit, start, end, duration: new Uint16Array(n), magnitude: new Float32Array(n), peak: new Float32Array(n),
               max_share: new Array(n), side: new Uint8Array(n), open: new Uint8Array(n), flagged: new Uint8Array(n)};
  for (let i = 0; i < n; i++) {
    out.duration[i] = end[i] - start[i] + 1;
    out.magnitude[i] = mag[i] / 100;
    out.peak[i] = peak[i] / 1000;
    out.max_share[i] = share[i] === 255 ? null : share[i] / 200;
    out.side[i] = flags[i] & 1;
    out.open[i] = (flags[i] >> 1) & 1;
    out.flagged[i] = (flags[i] >> 2) & 1;
  }
  return out;
}

export function loadJSON(key, file) {
  if (!cache.has(key)) cache.set(key, file.json());
  return cache.get(key);
}

/**
 * Standard normal cumulative probability, as a percentage 0 to 100.
 * EDDI's percentile is defined from its value this way in the source files:
 * "percentile = 100 * scipy.stats.norm.cdf(eddi)". (Abramowitz and Stegun 7.1.26; error under 1e-5 of a percent point.)
 */
export function percentileOf(z) {
  const x = Math.abs(z) / Math.SQRT2;
  const t = 1 / (1 + 0.3275911 * x);
  const erf = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * Math.exp(-x * x);
  return 50 * (1 + (z < 0 ? -erf : erf));
}

/** Month position (0 = first month of the record) to "YYYY-MM", a Date, or a readable label. */
const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
export const ym = (t, y0 = 1950) => `${y0 + Math.floor(t / 12)}-${String((t % 12) + 1).padStart(2, "0")}`;
export const monthDate = (t, y0 = 1950) => new Date(Date.UTC(y0, t, 1));
export const monthLabel = (t, y0 = 1950) => `${MONTHS[t % 12]} ${y0 + Math.floor(t / 12)}`;
export const monthsText = (n) => (n === 1 ? "1 month" : `${n} months`);
