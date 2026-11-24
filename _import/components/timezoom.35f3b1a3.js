// Time controls for the charts.
//
//   timeInteractions(plot, {onPick})  a click on a chart picks that month
//   timeSlider({...})                 an overview of the whole record with a draggable window:
//                                     drag the window to move it, drag an edge to widen or narrow it
//
// The span of months on show lives in `rangeStore`, a plain object. The slider reads it when it is
// built and writes it when the reader lets go; the page's reactive value is set through `onChange`.
// The slider must NOT be rebuilt because the range changed, or a drag would be cut off half way,
// so the page builds it in a block that does not depend on the range.
import * as d3 from "../../_npm/d3@7.9.2/172963d6.js";

export const rangeStore = {value: null}; // [first month position, last month position]

const DRAG_MIN = 5; // pixels: more than this between press and release is not a click

/** Date -> month position, 0 = January of y0. */
export const monthOf = (date, y0 = 1950) => (date.getUTCFullYear() - y0) * 12 + date.getUTCMonth();

export function timeInteractions(plot, {onPick}) {
  // with a legend, Plot returns a <figure> holding legend svgs and the chart svg: take the widest
  const svg = plot.tagName.toLowerCase() === "svg"
    ? plot
    : Array.from(plot.querySelectorAll("svg")).sort((a, b) => b.width.baseVal.value - a.width.baseVal.value)[0];
  const x = plot.scale("x");
  const [r0, r1] = x.range;
  svg.style.cursor = "pointer";
  // pointer position in the svg's own coordinates (the svg may be displayed narrower than its width attribute)
  const local = (e) => {
    const r = svg.getBoundingClientRect();
    return Math.min(r1, Math.max(r0, (e.clientX - r.left) / (r.width / svg.width.baseVal.value)));
  };
  let down = null;
  svg.addEventListener("pointerdown", (e) => { if (e.button === 0) down = e.clientX; });
  svg.addEventListener("pointerup", (e) => {
    if (down != null && Math.abs(e.clientX - down) < DRAG_MIN) onPick(x.invert(local(e)));
    down = null;
  });
  svg.addEventListener("pointercancel", () => { down = null; });
  return plot;
}

/**
 * Overview of the whole record with a window that selects the months the charts show.
 * @param width     pixels
 * @param last      last month position (first is 0)
 * @param values    [{t, wet}] the unit's mean index, signed so that positive is the wet side
 * @param minSpan   narrowest window allowed, in months
 * @param colours   {dry, wet, ink, axis}
 * @param onChange  (firstMonth, lastMonth) => void, called when the reader lets go
 */
export function timeSlider({width, last, values, minSpan = 12, colours, onChange, y0 = 1950}) {
  const height = 64, top = 4, bottom = 18, left = 44, right = 12;
  const x = d3.scaleLinear([0, last + 1], [left, width - right]);
  const y = d3.scaleLinear([-2.5, 2.5], [height - bottom, top]).clamp(true);
  const svg = d3.create("svg").attr("width", width).attr("height", height).attr("role", "group")
    .attr("aria-label", "Years shown in the charts. Drag the window to move it, or drag an edge to change its length.")
    .style("display", "block").style("max-width", "100%");

  // the unit's mean index over the whole record: warm below zero (dry side), cool above
  const area = (sign, fill) => svg.append("path").attr("fill", fill).attr("d", d3.area()
    .x((d) => x(d.t + 0.5)).y0(y(0)).y1((d) => y(sign > 0 ? Math.max(0, d.wet) : Math.min(0, d.wet)))(values));
  area(1, colours.wet);
  area(-1, colours.dry);
  svg.append("line").attr("x1", left).attr("x2", width - right).attr("y1", y(0)).attr("y2", y(0)).attr("stroke", colours.axis);
  const decades = d3.range(0, last + 1, 120);
  svg.append("g").selectAll("text").data(decades).join("text")
    .attr("x", (t) => x(t)).attr("y", height - 4).attr("font-size", 10).attr("fill", colours.ink).attr("text-anchor", "middle")
    .text((t) => y0 + t / 12);
  svg.append("g").selectAll("line").data(decades).join("line")
    .attr("x1", (t) => x(t)).attr("x2", (t) => x(t)).attr("y1", top).attr("y2", height - bottom).attr("stroke", colours.axis).attr("stroke-opacity", 0.5);

  const clamp = (a, b) => {
    let span = Math.max(minSpan, Math.min(last + 1, Math.round(b - a)));
    let from = Math.max(0, Math.min(last + 1 - span, Math.round(a)));
    return [from, from + span - 1];
  };
  const brush = d3.brushX().extent([[left, top], [width - right, height - bottom]]).handleSize(10);
  const g = svg.append("g").attr("class", "time-brush");
  const show = ([a, b]) => g.call(brush.move, [x(a), x(b + 1)]);
  brush.on("end", (event) => {
    if (!event.sourceEvent) return;               // our own brush.move below, not the reader
    if (!event.selection) return show(rangeStore.value); // a click outside the window would clear it: put it back
    const [a, b] = clamp(x.invert(event.selection[0]), x.invert(event.selection[1]));
    rangeStore.value = [a, b];
    show([a, b]);                                  // snap to whole months and to the minimum length
    onChange(a, b);
  });
  g.call(brush);
  g.select(".selection").attr("fill", colours.window).attr("fill-opacity", 0.18).attr("stroke", colours.window);
  g.selectAll(".handle").attr("fill", colours.window).attr("fill-opacity", 0.7).attr("rx", 3);
  show(rangeStore.value ?? [0, last]);
  return svg.node();
}
