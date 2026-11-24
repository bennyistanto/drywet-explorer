// The map: one pixel per grid cell on a canvas, province outlines on top as SVG.
// The grid is regular in latitude and longitude, so the canvas is the grid
// itself, stretched to the page width. A click resolves to a grid cell and from
// there to the province that holds most of that cell (the same lookup the
// pipeline exports), so no geometry test runs in the browser.
//
// Zoom and pan: scroll or pinch to zoom, drag to pan, or use the buttons.
// The view is remembered across redraws (the map is rebuilt whenever the month,
// the layer or the selection changes), as a scale and a position relative to
// the map's size, so it also survives a resize.
import * as d3 from "../../_npm/d3@7.9.2/172963d6.js";

const FLAG_ALPHA = 120; // of 255: flagged cells are drawn washed out
// 32 since 2026-11-24 (was 16): at 16 a kecamatan, often 3 or 4 cells across, was still too small to read when
// the map fits itself to one. At 32 a grid cell is about 35 px wide on a 1,200 px map, and the outlines'
// 333 m simplification shows as a wobble of about 2 px.
const MAX_ZOOM = 32;
const FIT = 0.8;      // a selected unit is zoomed to fill this share of the map's width or height
const FLY_MS = 600;   // how long the move to a newly selected unit takes
// scale, and translation as a fraction of width and height; `key` names the selection the view was last
// fitted to, and `pending` is a fit still on its way (the map can be rebuilt while it is moving)
const view = {k: 1, fx: 0, fy: 0, key: "//", pending: null};
const IDLE = "Hover for the class of a cell. Click a province to select it. Scroll or drag to zoom and pan.";

/**
 * @param grid       meta.grid
 * @param cells      Uint32Array, flat grid index of each drawn cell
 * @param cellFlag   Uint8Array or null: 1 where the cell is flagged in this month
 * @param classes    Uint8Array, class code of each drawn cell this month (0 = no data)
 * @param rgb        Uint8Array lookup, 3 bytes per class code
 * @param outlines   GeoJSON FeatureCollection of provinces
 * @param detail     features drawn thinner beneath them (the units of the open province)
 * @param highlight  features drawn bold on top; the last one is the current selection
 * @param describe   (cellPosition) => text for the hover line
 * @param onPick     (cellPosition, or -1 for sea) => void
 * @param focus      the feature of the current selection, or null when nothing is selected
 * @param focusKey   text that changes when the selection changes ("//" for none). When it changes, the map
 *                   moves to fit `focus`, or back to the full extent when nothing is selected. While it stays
 *                   the same (a new month, another index), the reader's own zoom and pan are kept.
 */
export function drawMap({grid, cells, cellFlag, classes, rgb, outlines, detail = [], highlight = [], describe, onPick, width, focus = null, focusKey = "//"}) {
  const {nx, ny} = grid;
  const height = Math.round((width * ny) / nx);

  const canvas = document.createElement("canvas");
  canvas.width = nx;
  canvas.height = ny;
  canvas.style.cssText = `width:${width}px;height:${height}px;display:block;image-rendering:pixelated;`;
  const ctx = canvas.getContext("2d");
  const img = ctx.createImageData(nx, ny);
  const px = img.data;
  for (let i = 0; i < cells.length; i++) {
    const code = classes[i];
    if (code === 0) continue; // no data stays transparent: never drawn as "normal"
    const p = cells[i] * 4;
    px[p] = rgb[code * 3];
    px[p + 1] = rgb[code * 3 + 1];
    px[p + 2] = rgb[code * 3 + 2];
    px[p + 3] = cellFlag && cellFlag[i] ? FLAG_ALPHA : 255;
  }
  ctx.putImageData(img, 0, 0);

  // lon/lat -> page pixels, matching the canvas exactly (cell edges, not centres)
  const west = grid.lon_first - grid.dlon / 2;
  const north = grid.lat_first - grid.dlat / 2; // dlat is negative: this is the northern edge
  const sx = (lon) => ((lon - west) / (nx * grid.dlon)) * width;
  const sy = (lat) => ((lat - north) / (ny * grid.dlat)) * height;
  const path = d3.geoPath(d3.geoTransform({point(x, y) { this.stream.point(sx(x), sy(y)); }}));

  const svg = d3.create("svg").attr("width", width).attr("height", height)
    .style("position", "absolute").style("left", 0).style("top", 0).style("pointer-events", "none").style("overflow", "visible");
  // three layers of outline: every province, thin; the units inside the open province, thinner;
  // and the selection (a province, and a unit inside it when one is chosen), bold
  // Each path carries its on-screen width in data-w. The map zooms by a CSS transform on the stage, which
  // scales strokes too (vector-effect: non-scaling-stroke does not see a CSS transform on an HTML ancestor),
  // so the zoom handler divides every width by the zoom factor to keep lines the same thickness on screen.
  svg.append("g").selectAll("path").data(detail).join("path")
    .attr("d", path).attr("fill", "none").attr("stroke", "#52514e").attr("data-w", 0.4).attr("stroke-opacity", 0.55);
  svg.append("g").selectAll("path").data(outlines.features).join("path")
    .attr("d", path).attr("fill", "none").attr("stroke", "#52514e").attr("data-w", 0.6).attr("stroke-opacity", 0.8);
  svg.append("g").selectAll("path").data(highlight).join("path")
    .attr("d", path).attr("fill", "none").attr("stroke", "#0b0b0b").attr("data-w", (d, i) => (i === highlight.length - 1 ? 2 : 1.2))
    .attr("stroke-linejoin", "round");
  const lines = svg.selectAll("path");
  const setLineWidths = (k) => lines.attr("stroke-width", function () { return +this.getAttribute("data-w") / k; });
  setLineWidths(1);

  // flat grid index -> position among drawn cells
  const posOf = new Int32Array(nx * ny).fill(-1);
  for (let i = 0; i < cells.length; i++) posOf[cells[i]] = i;
  // the canvas rectangle on screen already includes the zoom transform, so this needs no extra arithmetic
  const cellAt = (event) => {
    const r = canvas.getBoundingClientRect();
    const col = Math.floor(((event.clientX - r.left) / r.width) * nx);
    const row = Math.floor(((event.clientY - r.top) / r.height) * ny);
    if (col < 0 || col >= nx || row < 0 || row >= ny) return -1;
    return posOf[row * nx + col];
  };

  const hover = document.createElement("div");
  hover.className = "map-hover";
  hover.textContent = IDLE;

  const stage = document.createElement("div"); // what zooms and pans
  stage.style.cssText = `position:absolute;left:0;top:0;width:${width}px;height:${height}px;transform-origin:0 0;`;
  stage.append(canvas, svg.node());

  const wrap = document.createElement("div");
  wrap.style.cssText = `position:relative;width:${width}px;height:${height}px;overflow:hidden;cursor:grab;background:#fcfcfb;touch-action:none;`;
  wrap.setAttribute("role", "img");
  wrap.setAttribute("aria-label", "Map of Indonesia coloured by class for the selected month. Use the Province menu to select a province without a pointer.");
  wrap.append(stage);
  wrap.addEventListener("mousemove", (e) => {
    const i = cellAt(e);
    hover.textContent = i < 0 ? "Sea, or outside Indonesia." : describe(i);
  });
  wrap.addEventListener("mouseleave", () => { hover.textContent = IDLE; });
  wrap.addEventListener("click", (e) => {
    if (e.target.closest(".map-buttons")) return;
    onPick(cellAt(e)); // position among drawn cells, or -1 for sea: the page decides what that selects
  });

  // ---- zoom and pan
  const zoom = d3.zoom()
    .scaleExtent([1, MAX_ZOOM])
    .translateExtent([[0, 0], [width, height]])
    .extent([[0, 0], [width, height]])
    .filter((e) => !e.target.closest?.(".map-buttons") && (!e.button || e.type === "wheel"))
    .on("zoom", (e) => {
      const t = e.transform;
      stage.style.transform = `translate(${t.x}px,${t.y}px) scale(${t.k})`;
      setLineWidths(t.k);
      view.k = t.k;
      view.fx = t.x / width;
      view.fy = t.y / height;
      resetBtn.disabled = t.k === 1;
      outBtn.disabled = t.k <= 1;
      inBtn.disabled = t.k >= MAX_ZOOM;
    })
    .on("end", (e) => {
      // a fit has arrived, or the reader has taken over with the wheel, a drag or a button: nothing is pending
      const p = view.pending;
      if (p && (e.sourceEvent || (Math.abs(view.k - p.k) < 1e-6 && Math.abs(view.fx - p.fx) < 1e-6 && Math.abs(view.fy - p.fy) < 1e-6))) view.pending = null;
    });
  const zsel = d3.select(wrap).call(zoom).on("dblclick.zoom", null); // a double click must not fight the select click

  const button = (label, title, fn) => {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = label;
    b.title = title;
    b.setAttribute("aria-label", title);
    b.addEventListener("click", (e) => { e.stopPropagation(); fn(); });
    return b;
  };
  const inBtn = button("+", "Zoom in", () => zsel.transition().duration(150).call(zoom.scaleBy, 1.6));
  const outBtn = button("−", "Zoom out", () => zsel.transition().duration(150).call(zoom.scaleBy, 1 / 1.6));
  const resetBtn = button("Reset", "Reset the map to the full extent", () => zsel.transition().duration(150).call(zoom.transform, d3.zoomIdentity));
  const buttons = document.createElement("div");
  buttons.className = "map-buttons";
  buttons.append(inBtn, outBtn, resetBtn);
  wrap.append(buttons);

  // restore the view the reader had before this redraw
  zsel.call(zoom.transform, d3.zoomIdentity.translate(view.fx * width, view.fy * height).scale(view.k));

  // a new selection: fit the map to it (or return to the full extent when the selection is cleared)
  if (focusKey !== view.key) {
    view.key = focusKey;
    if (focus) {
      const [[x0, y0], [x1, y1]] = path.bounds(focus); // page pixels at zoom 1
      const k = Math.max(1, Math.min(MAX_ZOOM, FIT / Math.max((x1 - x0) / width, (y1 - y0) / height, 1e-9)));
      // centre it, without showing anything beyond the map's edge
      const tx = Math.min(0, Math.max(width - k * width, width / 2 - (k * (x0 + x1)) / 2));
      const ty = Math.min(0, Math.max(height - k * height, height / 2 - (k * (y0 + y1)) / 2));
      view.pending = {k, fx: tx / width, fy: ty / height};
    } else if (focusKey === "//") {
      view.pending = {k: 1, fx: 0, fy: 0};
    }
  }
  if (view.pending) {
    const p = view.pending;
    zsel.transition().duration(FLY_MS).call(zoom.transform, d3.zoomIdentity.translate(p.fx * width, p.fy * height).scale(p.k));
  }

  const root = document.createElement("div");
  root.append(wrap, hover);
  return root;
}

/** Legend as plain HTML: a swatch and a label per class that can occur, then no data and the flag wash. */
export function legend({items, flagged, flagText}) {
  const root = document.createElement("div");
  root.className = "legend";
  const add = (colour, label, extra = "") => {
    const s = document.createElement("span");
    s.className = "legend-item";
    s.innerHTML = `<span class="swatch" style="background:${colour};${extra}"></span>`;
    s.append(label);
    root.append(s);
  };
  for (const it of items) add(it.colour, it.label);
  add("#fcfcfb", "No data", "border:1px dashed #898781;");
  if (flagged) add(items[0].colour, flagText, `opacity:${FLAG_ALPHA / 255};`);
  return root;
}
