import maplibregl from "maplibre-gl";
import { Protocol } from "pmtiles";
import "maplibre-gl/dist/maplibre-gl.css";
import {
  GEOGRAPHY_LEVELS,
  WARM_TYPES,
  chartMenu,
  deferCamera,
  emptyScopeMessage,
  geographyLevel,
  institutionField,
  legendText,
  lineYears,
  marginColor,
  matchesState,
  pickUnit,
  pointerTap,
  precinctLabel,
  rangeStartVotes,
  resolveChart,
  schoolLabels,
  scopeRows,
  searchInstitutions,
  segmentChanges,
  sliderFrame,
  sliderLabelXs,
  sortRows,
  stateName,
  thumbnailBox,
  tileRangeOk,
  topInstitutionHit,
  warmOrder,
  type CameraView,
  type ChartKind,
  type GeographyLevel,
  type PlaceChain,
} from "@usd/core";
import tokens from "../../design/tokens.json";
import mapStyle from "../../styles/map.json";
import "./style.css";

type Tokens = typeof tokens;
type ResultRow = {
  unit: string;
  legacy: string | null;
  name: string;
  state?: string | null;
  geoid?: string | null;
  county?: string | null;
  votes: number[] | null;
  total: number | null;
  share: number[] | null;
  est: boolean;
  gray: boolean;
};
type ResultsBody = {
  dv: number;
  answers: string[];
  rows: ResultRow[];
};
type LayoutMode = keyof Tokens["layoutMode"];
type Place = {
  level: GeographyLevel;
  stateAbbr: string;
  stateKey: string | null;
  countyName: string | null;
  precinctLabel: string | null;
  dc: boolean;
  crumbs: string[];
  geographyPicked: boolean;
};

const protocol = new Protocol();
maplibregl.addProtocol("pmtiles", protocol.tile);

const root = document.documentElement;
const color = (tokens as Tokens).color;
root.style.setProperty("--bg", color.bg);
root.style.setProperty("--panel", color.panel);
root.style.setProperty("--border", color.border);
root.style.setProperty("--text", color.text);
root.style.setProperty("--muted", color.textMuted);
root.style.setProperty("--dem", color.dem);
root.style.setProperty("--rep", color.rep);
root.style.setProperty("--nodata", color.noDataFill);
root.style.setProperty("--thumb", `${tokens.thumbPx}px`);
root.style.setProperty("--sat", tokens.safeArea.top);
root.style.setProperty("--sar", tokens.safeArea.right);
root.style.setProperty("--sab", tokens.safeArea.bottom);
root.style.setProperty("--sal", tokens.safeArea.left);

const YEARS = [2016, 2020, 2024] as const;
const marginPaint: maplibregl.ExpressionSpecification = [
  "case",
  ["==", ["feature-state", "gray"], 1],
  color.noDataFill,
  [
    "interpolate",
    ["linear"],
    ["coalesce", ["feature-state", "margin"], 0],
    tokens.marginScale.demStop,
    color.dem,
    tokens.marginScale.even,
    color.mapNeutral,
    tokens.marginScale.repStop,
    color.rep,
  ],
];

let yearStart: (typeof YEARS)[number] = 2016;
let yearEnd: (typeof YEARS)[number] = 2016;
let chart: ChartKind = "bar";
let sliderOpen = true;
let fmt: "pct" | "num" = "pct";
let body: ResultsBody | null = null;
const yearBodies = new Map<number, ResultsBody | null>();
let rowIndex = new Map<string, ResultRow>();
let focusKey: string | null = null;
const twins = new Map<string, string>();
let place: Place = {
  level: "state",
  stateAbbr: "",
  stateKey: null,
  countyName: null,
  precinctLabel: null,
  dc: false,
  crumbs: ["United States"],
  geographyPicked: false,
};
let stateEdited = false;
let committed = "United States";
let emptyMessage = "No rows";
let loadSeq = 0;
let tapHandled = false;
let map: maplibregl.Map | undefined;
let pendingCamera: CameraView | null = null;
const warmCache = new Map<string, ResultsBody>();
const LAST_TYPE_KEY = "v3.lastType";

const yearsEl = document.querySelector<HTMLElement>("#years")!;
const geographyEl = document.querySelector<HTMLElement>("#geography")!;
const stateEl = document.querySelector<HTMLInputElement>("#state")!;
const addressEl = document.querySelector<HTMLInputElement>("#address")!;
const placeNote = document.querySelector<HTMLElement>("#place-note")!;
const listEl = document.querySelector<HTMLOListElement>("#list")!;
const fmtBtn = document.querySelector<HTMLButtonElement>("#fmt")!;
const layoutBtn = document.querySelector<HTMLButtonElement>("#layout")!;
const backBtn = document.querySelector<HTMLButtonElement>("#back")!;
const clockBtn = document.querySelector<HTMLButtonElement>("#clock")!;
const chartBtn = document.querySelector<HTMLButtonElement>("#chart")!;
const chartMenuEl = document.querySelector<HTMLElement>("#chart-menu")!;
const chartView = document.querySelector<HTMLElement>("#chart-view")!;
const instInput = document.querySelector<HTMLInputElement>("#institution-q")!;
const instMenu = document.querySelector<HTMLElement>("#inst-menu")!;
const crumbEl = document.querySelector<HTMLElement>("#crumb")!;
const legendEl = document.querySelector<HTMLElement>("#legend")!;
const legendCompactEl = document.querySelector<HTMLElement>("#legend-compact")!;
const thumbsEl = document.querySelector<HTMLElement>("#thumbs")!;
let layout: LayoutMode = "map";
document.body.dataset.layout = tokens.layoutMode[layout];

document.addEventListener("pointerdown", () => {
  tapHandled = false;
});

function bindTap(el: HTMLElement, action: () => void) {
  el.addEventListener("pointerup", (ev) => {
    const decision = pointerTap("pointerup", tapHandled, ev.button);
    if (decision.handled) tapHandled = true;
    if (decision.act) action();
  });
  el.addEventListener("click", (ev) => {
    const decision = pointerTap("click", tapHandled, 0);
    tapHandled = false;
    if (!decision.act) {
      ev.preventDefault();
      ev.stopPropagation();
      return;
    }
    action();
  });
}

function span(): number[] {
  return lineYears(yearStart, yearEnd);
}

function paintCrumbFor(view: { unitType: string; state: string | null }) {
  if (place.geographyPicked) {
    stateEl.value = place.stateAbbr;
    crumbEl.textContent = place.crumbs.join(" · ") || "United States";
    return;
  }
  if (view.unitType === "state" && !view.state) {
    stateEl.value = "";
    crumbEl.textContent = "United States";
    return;
  }
  const abbr = view.state ?? "";
  const name = abbr ? stateName(abbr) : null;
  stateEl.value = abbr;
  crumbEl.textContent = name || abbr || "United States";
}

function viewFor(y: number): { unitType: string; state: string | null } {
  if (!place.geographyPicked) {
    if (y === 2016) return { unitType: "state", state: place.stateAbbr || null };
    return { unitType: "county", state: place.stateAbbr || "PA" };
  }
  if (place.level === "state") return { unitType: "state", state: place.stateAbbr || null };
  if (place.level === "ushouse" || place.level === "school_unified") {
    return { unitType: place.level, state: place.stateAbbr || null };
  }
  return { unitType: place.level, state: place.stateAbbr || (place.level === "precinct" ? "VT" : "PA") };
}

function mapHidden(): boolean {
  return document.body.dataset.layout === "list";
}

function cameraFor(level: GeographyLevel, point: { lon: number; lat: number }): CameraView {
  const zoom = level === "precinct" ? 11 : level === "county" || level === "school_unified" ? 8 : level === "ushouse" ? 6 : 5;
  return { lon: point.lon, lat: point.lat, zoom };
}

function moveCamera(next: CameraView | null) {
  const step = deferCamera(mapHidden(), pendingCamera, next);
  pendingCamera = step.pending;
  if (step.apply && map) map.jumpTo({ center: [step.apply.lon, step.apply.lat], zoom: step.apply.zoom });
}

function applyPlace(next: Place, point?: { lon: number; lat: number } | null, focus: string | null = null) {
  focusKey = focus;
  placeNote.hidden = true;
  placeNote.textContent = "";
  place = {
    ...next,
    crumbs: next.crumbs.length ? next.crumbs : ["United States"],
    stateAbbr: next.stateAbbr.toUpperCase(),
  };
  stateEl.value = place.stateAbbr;
  crumbEl.textContent = place.crumbs.join(" · ");
  if (point) moveCamera(cameraFor(place.level, point));
  paintGeography();
  paintLegend();
  void load();
}

function applyChain(chain: PlaceChain, point?: { lon: number; lat: number }) {
  stateEdited = true;
  const focus = chain.precinctKey || (chain.dc ? null : chain.countyKey) || chain.stateKey;
  applyPlace(
    {
      level: chain.level,
      stateAbbr: chain.stateAbbr ?? "",
      stateKey: chain.stateKey,
      countyName: chain.dc ? null : chain.countyName,
      precinctLabel: chain.precinctLabel,
      dc: chain.dc,
      crumbs: chain.crumbs,
      geographyPicked: true,
    },
    point,
    focus,
  );
}

function climb() {
  if (place.level === "precinct") {
    const dc = place.dc || place.stateAbbr === "DC";
    applyPlace({
      ...place,
      level: dc ? "state" : "county",
      precinctLabel: null,
      countyName: dc ? null : place.countyName,
      crumbs: dc ? ["District of Columbia"] : place.crumbs.slice(0, Math.max(1, place.crumbs.length - 1)),
      geographyPicked: true,
    });
    return;
  }
  if (place.level === "county") {
    const name = place.stateAbbr ? stateName(place.stateAbbr) : null;
    applyPlace({
      ...place,
      level: "state",
      countyName: null,
      precinctLabel: null,
      crumbs: name ? [name] : ["United States"],
      geographyPicked: true,
    });
    return;
  }
  if (place.stateAbbr) {
    stateEdited = false;
    applyPlace({
      level: "state",
      stateAbbr: "",
      stateKey: null,
      countyName: null,
      precinctLabel: null,
      dc: false,
      crumbs: ["United States"],
      geographyPicked: true,
    });
  }
}

function paintGeography() {
  geographyEl.replaceChildren();
  for (const choice of GEOGRAPHY_LEVELS) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "glass" + (place.geographyPicked && geographyLevel(choice.key) === place.level ? " on" : "");
    btn.textContent = choice.label;
    bindTap(btn, () => {
      const next = geographyLevel(choice.key);
      if (!next) return;
      const abbr = stateEdited
        ? place.stateAbbr
        : next === "precinct"
          ? "VT"
          : next === "county" || next === "ushouse" || next === "school_unified"
            ? "PA"
            : "";
      const name = abbr ? stateName(abbr) : null;
      applyPlace({
        level: next,
        stateAbbr: abbr,
        stateKey: null,
        countyName: null,
        precinctLabel: null,
        dc: abbr === "DC",
        crumbs: name ? [name] : ["United States"],
        geographyPicked: true,
      });
    });
    geographyEl.append(btn);
  }
}

function alignSlider() {
  const buttons = Array.from(yearsEl.querySelectorAll<HTMLButtonElement>("button"));
  const xs = sliderLabelXs(buttons.map((btn) => {
    const rect = btn.getBoundingClientRect();
    return { left: rect.left, width: rect.width };
  }));
  buttons.forEach((btn, i) => {
    btn.dataset.labelX = String(Math.round(xs[i] ?? 0));
  });
}

function paintYears() {
  yearsEl.replaceChildren();
  const selected = new Set(span());
  for (const y of YEARS) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.dataset.year = String(y);
    btn.className = "glass" + (selected.has(y) ? " on" : "");
    btn.textContent = `'${String(y).slice(2)}`;
    bindTap(btn, () => {
      if (yearStart === yearEnd && y !== yearStart) {
        yearStart = Math.min(yearStart, y) as (typeof YEARS)[number];
        yearEnd = Math.max(yearEnd, y) as (typeof YEARS)[number];
      } else {
        yearStart = y;
        yearEnd = y;
      }
      chart = resolveChart(chart, span());
      document.body.dataset.chart = chart;
      paintYears();
      paintChartButton();
      void load();
    });
    yearsEl.append(btn);
  }
  requestAnimationFrame(alignSlider);
}

function paintSlider() {
  const frame = sliderFrame(sliderOpen);
  yearsEl.dataset.open = sliderOpen ? "true" : "false";
  yearsEl.style.visibility = frame.rowVisibility;
}

function paintLegend() {
  legendEl.textContent = legendText(yearEnd, false);
  legendCompactEl.textContent = legendText(yearEnd, true);
}

function setThumbs(ready: boolean) {
  const box = thumbnailBox(ready);
  thumbsEl.dataset.ready = ready ? "true" : "false";
  thumbsEl.style.visibility = box.visibility;
  thumbsEl.style.height = `${box.size}px`;
  thumbsEl.style.minHeight = `${box.size}px`;
}

function focusRow(): ResultRow | null {
  if (focusKey) return pickUnit(rowIndex, focusKey) ?? null;
  return body?.rows[0] ?? null;
}

function paintThumbs() {
  const row = focusRow();
  const dem = row?.share?.[0] ?? 0;
  const rep = row?.share?.[1] ?? 0;
  const winnerDem = dem >= rep;
  thumbsEl.replaceChildren();
  for (const kind of winnerDem ? ["dem", "rep"] : ["rep", "dem"]) {
    const icon = document.createElement("span");
    icon.className = `thumb ${kind}`;
    thumbsEl.append(icon);
  }
}

function sortedRows(): ResultRow[] {
  const rows = body?.rows ?? [];
  const shaped = rows.map((row) => ({
    row,
    name: row.name,
    share: row.gray ? null : (row.share?.[0] ?? null),
    votes: row.gray ? null : (row.votes?.[0] ?? null),
    gray: row.gray,
  }));
  return sortRows(shaped, fmt === "num" ? "votes" : "share", "desc").map((item) => item.row);
}

function pct(n: number): string {
  return `${(n * 100).toFixed(1)}%`;
}

function paintList() {
  const rows = sortedRows();
  const schoolName = new Map<string, string>();
  if (place.level === "school_unified") {
    for (const labeled of schoolLabels(rows.map((row) => ({
      geoid: row.geoid || row.unit,
      unit: row.unit,
      name: row.name,
      state: row.state,
      county: row.county,
    })))) {
      schoolName.set(labeled.geoid, labeled.label);
    }
  }
  listEl.replaceChildren();
  if (rows.length === 0) {
    const li = document.createElement("li");
    li.className = "empty";
    li.textContent = emptyMessage;
    listEl.append(li);
    return;
  }
  const maxTotal = Math.max(...rows.map((row) => (row.gray ? 0 : (row.total ?? 0))), 1);
  for (const row of rows) {
    const li = document.createElement("li");
    if (row.unit === focusKey) li.dataset.focus = "true";
    const swatch = document.createElement("span");
    swatch.className = "swatch";
    if (!row.gray && row.share) {
      swatch.style.background = marginColor((row.share[1] ?? 0) - (row.share[0] ?? 0));
    }
    const name = document.createElement("span");
    name.className = "name" + (place.level === "precinct" ? " whole" : "");
    const school = schoolName.get(row.geoid || row.unit);
    name.textContent = place.level === "precinct" ? precinctLabel(row.name) : school ?? row.name;
    const val = document.createElement("span");
    val.className = "val";
    if (row.gray) val.textContent = "—";
    else if (fmt === "num") val.textContent = (row.votes?.[0] ?? 0).toLocaleString("en-US");
    else val.textContent = pct(row.share?.[0] ?? 0);
    const bar = document.createElement("span");
    bar.className = "bar";
    if (!row.gray && row.share) {
      const scale = fmt === "num" ? (row.total ?? 0) / maxTotal : 1;
      const d = document.createElement("i");
      d.className = "d";
      d.style.width = `${(row.share[0] ?? 0) * scale * 100}%`;
      const r = document.createElement("i");
      r.className = "r";
      r.style.width = `${(row.share[1] ?? 0) * scale * 100}%`;
      const o = document.createElement("i");
      o.className = "o";
      o.style.width = `${(row.share[2] ?? 0) * scale * 100}%`;
      bar.append(d, r, o);
    }
    bindTap(li, () => {
      const picked = pickUnit(rowIndex, row.unit);
      if (!picked) return;
      focusKey = picked.unit;
      paintThumbs();
      if (chart !== "bar") paintChart();
    });
    li.append(swatch, name, val, bar);
    listEl.append(li);
  }
}

function marginOf(year: number, unit: string): number | null {
  const row = yearBodies.get(year)?.rows.find((item) => item.unit === unit);
  if (!row || row.gray || !row.share) return null;
  return (row.share[1] ?? 0) - (row.share[0] ?? 0);
}

function paintChartButton() {
  chartBtn.textContent = chart === "pie" ? "Pie" : chart === "line" ? "Line" : "Bar";
  document.body.dataset.chart = chart;
}

function paintChartMenu() {
  chartMenuEl.replaceChildren();
  for (const kind of chartMenu(span())) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "hit" + (kind === chart ? " on" : "");
    btn.textContent = kind;
    bindTap(btn, () => {
      chart = resolveChart(kind, span());
      chartMenuEl.hidden = true;
      paintChartButton();
      paintChart();
    });
    chartMenuEl.append(btn);
  }
}

function paintPie() {
  chartView.replaceChildren();
  const row = focusRow();
  const dem = row && !row.gray ? (row.share?.[0] ?? 0) : 0;
  const rep = row && !row.gray ? (row.share?.[1] ?? 0) : 0;
  const other = row && !row.gray ? (row.share?.[2] ?? 0) : 0;
  const sum = dem + rep + other || 1;
  const d = (dem / sum) * 100;
  const r = (rep / sum) * 100;
  const pie = document.createElement("div");
  pie.className = "pie";
  pie.style.background = `conic-gradient(var(--dem) 0 ${d}%, var(--rep) ${d}% ${d + r}%, #a8a29e ${d + r}% 100%)`;
  chartView.append(pie);
}

function paintLine() {
  chartView.replaceChildren();
  const years = span();
  const unit = focusKey;
  const margins = years.map((year, index) => {
    if (!unit) return null;
    if (index === 0) {
      return rangeStartVotes({
        years,
        unitKey: unit,
        unitType: place.level,
        twins,
        votesAt: (atYear, key) => marginOf(atYear, key),
      });
    }
    return marginOf(year, unit);
  });
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.id = "line";
  svg.setAttribute("viewBox", "0 0 300 100");
  const coords = margins.map((margin, index) => {
    if (margin == null) return null;
    const x = years.length === 1 ? 150 : (index / (years.length - 1)) * 280 + 10;
    const y = 90 - ((Math.max(-0.9, Math.min(0.9, margin)) + 0.9) / 1.8) * 80;
    return `${x},${y}`;
  });
  const line = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
  line.setAttribute("fill", "none");
  line.setAttribute("stroke", "#111");
  line.setAttribute("stroke-width", "2");
  line.setAttribute("points", coords.filter((point): point is string => point != null).join(" "));
  svg.append(line);
  chartView.append(svg);
  for (const change of segmentChanges(years, margins)) {
    const label = document.createElement("p");
    label.className = "seg";
    label.textContent = change.label;
    chartView.append(label);
  }
}

function paintChart() {
  const showList = chart === "bar";
  listEl.hidden = !showList;
  chartView.hidden = showList;
  if (showList) {
    chartView.replaceChildren();
    paintList();
    return;
  }
  if (chart === "pie") paintPie();
  else paintLine();
}

function countyExtras() {
  if (place.level !== "county" || !body) return [];
  return body.rows.map((row) => ({ id: row.unit, label: row.name, group: "Counties" as const }));
}

function paintInstMenu() {
  const found = searchInstitutions(instInput.value, countyExtras());
  instMenu.replaceChildren();
  if (found.message) {
    const miss = document.createElement("p");
    miss.className = "miss";
    miss.textContent = found.message;
    instMenu.append(miss);
  }
  for (const group of found.groups) {
    const heading = document.createElement("p");
    heading.className = "group-label";
    heading.textContent = group.name;
    instMenu.append(heading);
    for (const hit of group.hits) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "hit" + (hit.gray ? " gray" : "");
      btn.append(document.createTextNode(hit.label));
      if (hit.note) {
        const note = document.createElement("span");
        note.className = "note";
        note.textContent = hit.note;
        btn.append(note);
      }
      bindTap(btn, () => {
        committed = hit.label;
        instInput.value = institutionField(hit.label, committed);
        instMenu.hidden = true;
      });
      instMenu.append(btn);
    }
  }
  instMenu.hidden = false;
}

function openInstitution() {
  instInput.focus();
  instInput.select();
  paintInstMenu();
}

function colorMap(target: maplibregl.Map, source: string) {
  const features = target.querySourceFeatures(source);
  const seen = new Set<string | number>();
  for (const feature of features) {
    const id = feature.id;
    if (id == null || seen.has(id)) continue;
    seen.add(id);
    const row = body?.rows.find((item) => item.unit === String(id));
    const gray = !row || row.gray || row.share == null;
    const margin = gray ? 0 : (row.share?.[1] ?? 0) - (row.share?.[0] ?? 0);
    const sourceLayer =
      source === "precinct-2024" ? "precincts" : source === "state-2024" ? "state" : source === "ushouse-2024" ? "districts" : undefined;
    target.setFeatureState(sourceLayer ? { source, sourceLayer, id } : { source, id }, { gray: gray ? 1 : 0, margin });
  }
}

function tilesBase(): string {
  const fromEnv = String(import.meta.env.VITE_TILES_BASE ?? "").replace(/\/$/, "");
  if (fromEnv) return fromEnv;
  return String(import.meta.env.BASE_URL ?? "/").replace(/\/$/, "");
}

function geoBase(): string {
  return String(import.meta.env.BASE_URL ?? "/").replace(/\/$/, "");
}

async function styleFor(): Promise<maplibregl.StyleSpecification> {
  const style = structuredClone(mapStyle) as maplibregl.StyleSpecification;
  const text = JSON.stringify(style).replaceAll("{tiles}", tilesBase()).replaceAll("{geo}", geoBase());
  const parsed = JSON.parse(text) as maplibregl.StyleSpecification;
  const tiles = parsed.sources?.["state-2024"];
  const url = tiles && "url" in tiles ? String(tiles.url).replace(/^pmtiles:\/\//, "") : "";
  let pmtilesOk = false;
  if (url) {
    try {
      const head = await fetch(url, { headers: { range: "bytes=0-15" } });
      if (tileRangeOk(head.status)) {
        const bytes = new Uint8Array(await head.arrayBuffer());
        pmtilesOk = String.fromCharCode(...bytes.slice(0, 7)) === "PMTiles";
      }
    } catch {
      pmtilesOk = false;
    }
  }
  if (!pmtilesOk && parsed.sources && parsed.layers) {
    delete parsed.sources["state-2024"];
    parsed.layers = parsed.layers.filter((layer) => !("source" in layer) || layer.source !== "state-2024");
  }
  return parsed;
}

async function syncOverlay(kind: "precinct" | "ushouse" | null, state: string | null) {
  if (!map?.isStyleLoaded()) return;
  for (const id of ["precinct-2024", "ushouse-2024"]) {
    if (map.getLayer(`${id}-fill`)) map.removeLayer(`${id}-fill`);
    if (map.getSource(id)) map.removeSource(id);
  }
  if (!kind) return;
  const url =
    kind === "precinct"
      ? `${tilesBase()}/tiles/precinct-2024/${state}.pmtiles`
      : `${tilesBase()}/tiles/ushouse-2024@1.pmtiles`;
  const head = await fetch(url, { headers: { range: "bytes=0-15" } });
  if (!tileRangeOk(head.status)) return;
  const bytes = new Uint8Array(await head.arrayBuffer());
  if (String.fromCharCode(...bytes.slice(0, 7)) !== "PMTiles") return;
  const sourceLayer = kind === "precinct" ? "precincts" : "districts";
  const id = kind === "precinct" ? "precinct-2024" : "ushouse-2024";
  map.addSource(id, { type: "vector", url: `pmtiles://${url}`, promoteId: "id" });
  map.addLayer({
    id: `${id}-fill`,
    type: "fill",
    source: id,
    "source-layer": sourceLayer,
    minzoom: kind === "precinct" ? 8 : 0,
    paint: { "fill-color": marginPaint, "fill-opacity": 0.72 },
  });
}

function warmKey(y: number, unitType: string, state: string | null): string {
  return `${y}|${unitType}|${state ?? ""}`;
}

async function fetchApiResults(
  y: number,
  view: { unitType: string; state: string | null },
): Promise<{ ok: true; body: ResultsBody } | { ok: false; message: string }> {
  const params = new URLSearchParams({ contest: `${y}|US|president|`, unit_type: view.unitType });
  if (view.state && matchesState(view.state, view.state)) params.set("state", view.state);
  const res = await fetch(`${import.meta.env.BASE_URL}api/v1/results?${params}`);
  if (!res.ok) {
    const err = (await res.json().catch(() => null)) as { error?: { message?: string } } | null;
    return { ok: false, message: err?.error?.message || "No rows" };
  }
  return { ok: true, body: (await res.json()) as ResultsBody };
}

async function fetchBody(y: number, view: { unitType: string; state: string | null }): Promise<{ ok: true; body: ResultsBody } | { ok: false; message: string }> {
  const key = warmKey(y, view.unitType, view.state);
  const cached = warmCache.get(key);
  if (cached) return { ok: true, body: cached };
  const loaded =
    import.meta.env.VITE_STATIC === "1"
      ? await (await import("./static-mode.ts")).fetchStaticResults(y, view)
      : await fetchApiResults(y, view);
  if (loaded.ok) warmCache.set(key, loaded.body);
  return loaded;
}

function scheduleWarm(state: string | null) {
  const abbr = (state ?? "").trim().toUpperCase();
  if (!abbr) return;
  let last: string | null = null;
  try {
    last = localStorage.getItem(LAST_TYPE_KEY);
  } catch {
    last = null;
  }
  const types = warmOrder(last);
  const run = () => {
    void (async () => {
      for (const unitType of types) {
        if (warmCache.has(warmKey(yearEnd, unitType, abbr))) continue;
        await fetchBody(yearEnd, { unitType, state: abbr });
      }
    })();
  };
  const idle = window.requestIdleCallback;
  if (idle) idle(() => run());
  else setTimeout(run, 1);
}

async function load() {
  const seq = ++loadSeq;
  setThumbs(false);
  const years = span();
  const end = years[years.length - 1] ?? yearEnd;
  const view = viewFor(end);
  paintCrumbFor(view);
  const fetched = await Promise.all(years.map(async (year) => ({ year, result: await fetchBody(year, view) })));
  if (seq !== loadSeq) return;
  yearBodies.clear();
  for (const item of fetched) yearBodies.set(item.year, item.result.ok ? item.result.body : null);
  const endResult = fetched.find((item) => item.year === end)?.result;
  if (!endResult || !endResult.ok) {
    body = null;
    rowIndex = new Map();
    emptyMessage = endResult && !endResult.ok ? endResult.message : "No rows";
    setThumbs(true);
    paintThumbs();
    paintChart();
    await syncOverlay(null, null);
    return;
  }
  const scoped = scopeRows({
    stateAbbr: view.state ?? "",
    unitType: view.unitType,
    rows: endResult.body.rows,
  });
  emptyMessage = emptyScopeMessage(view.unitType, scoped.length) ?? "No rows";
  body = { ...endResult.body, rows: scoped };
  rowIndex = new Map(body.rows.map((row) => [row.unit, row]));
  if ((WARM_TYPES as readonly string[]).includes(view.unitType)) {
    try {
      localStorage.setItem(LAST_TYPE_KEY, view.unitType);
    } catch {
      /* private mode */
    }
  }
  if (focusKey && !rowIndex.has(focusKey)) focusKey = null;
  setThumbs(true);
  paintLegend();
  paintThumbs();
  paintChart();
  const overlay = view.unitType === "precinct" ? "precinct" : view.unitType === "ushouse" ? "ushouse" : null;
  await syncOverlay(overlay, view.state);
  if (map?.isStyleLoaded()) {
    if (map.getSource("precinct-2024")) colorMap(map, "precinct-2024");
    if (map.getSource("ushouse-2024")) colorMap(map, "ushouse-2024");
    if (map.getSource("state-2024")) colorMap(map, "state-2024");
    colorMap(map, activeSource);
  }
  scheduleWarm(view.state);
}

bindTap(fmtBtn, () => {
  fmt = fmt === "pct" ? "num" : "pct";
  fmtBtn.textContent = fmt === "pct" ? "%" : "#";
  fmtBtn.classList.toggle("on", fmt === "num");
  if (chart === "bar") paintList();
});
bindTap(layoutBtn, () => {
  layout = layout === "map" ? "list" : "map";
  document.body.dataset.layout = tokens.layoutMode[layout];
  layoutBtn.textContent = layout === "map" ? "List" : "Map";
  if (layout === "map") moveCamera(null);
});
bindTap(backBtn, climb);
bindTap(clockBtn, () => {
  sliderOpen = !sliderOpen;
  paintSlider();
});
bindTap(chartBtn, () => {
  const open = chartMenuEl.hidden;
  if (open) paintChartMenu();
  chartMenuEl.hidden = !open;
});
bindTap(document.querySelector<HTMLButtonElement>("#uni-inst")!, openInstitution);
bindTap(document.querySelector<HTMLButtonElement>("#uni-geo")!, openInstitution);
bindTap(document.querySelector<HTMLButtonElement>("#uni-chart")!, openInstitution);

stateEl.addEventListener("input", () => {
  const abbr = stateEl.value.toUpperCase().slice(0, 2);
  stateEl.value = abbr;
  stateEdited = abbr.length > 0;
  const name = stateName(abbr);
  applyPlace({
    ...place,
    stateAbbr: abbr,
    stateKey: null,
    dc: abbr === "DC",
    crumbs: name ? [name] : abbr ? [abbr] : ["United States"],
    geographyPicked: place.geographyPicked || abbr.length > 0,
  });
});
addressEl.addEventListener("keydown", (ev) => {
  if (ev.key !== "Enter") return;
  ev.preventDefault();
  void (async () => {
    if (import.meta.env.VITE_STATIC === "1") {
      const hit = await (await import("./static-mode.ts")).lookupPlace(addressEl.value);
      if (!hit) {
        placeNote.hidden = false;
        placeNote.textContent = "No place match";
        return;
      }
      stateEdited = true;
      applyPlace(
        {
          level: hit.level,
          stateAbbr: hit.stateAbbr,
          stateKey: hit.stateKey,
          countyName: hit.countyName,
          precinctLabel: null,
          dc: hit.dc,
          crumbs: hit.crumbs,
          geographyPicked: true,
        },
        null,
        hit.focus,
      );
      return;
    }
    const res = await fetch(`${import.meta.env.BASE_URL}api/v1/geocode?q=${encodeURIComponent(addressEl.value)}`);
    if (!res.ok) {
      placeNote.hidden = false;
      placeNote.textContent = "No place match";
      return;
    }
    const hit = (await res.json()) as { chain: PlaceChain; point: { lon: number; lat: number } };
    if (!hit.chain?.stateAbbr && !hit.chain?.crumbs?.length) {
      placeNote.hidden = false;
      placeNote.textContent = "No place match";
      return;
    }
    applyChain(hit.chain, hit.point);
  })();
});
instInput.addEventListener("input", () => {
  if (!instInput.value.trim()) instInput.value = institutionField("", committed);
  paintInstMenu();
});
instInput.addEventListener("keydown", (ev) => {
  if (ev.key === "Escape") {
    instMenu.hidden = true;
    instInput.value = institutionField(instInput.value, committed);
    return;
  }
  if (ev.key !== "Enter") return;
  ev.preventDefault();
  const hit = topInstitutionHit(instInput.value, countyExtras());
  if (!hit) {
    paintInstMenu();
    return;
  }
  committed = hit.label;
  instInput.value = institutionField(hit.label, committed);
  instMenu.hidden = true;
});
instInput.addEventListener("blur", () => {
  instInput.value = institutionField(instInput.value, committed);
});

paintGeography();
paintYears();
paintSlider();
paintLegend();
paintChartButton();
setThumbs(false);
window.addEventListener("resize", alignSlider);

const activeSource = "state-geojson";
map = new maplibregl.Map({
  container: "map",
  style: { version: 8, sources: {}, layers: [] },
  center: [-98.5, 39.5],
  zoom: 3.2,
  attributionControl: {},
});

void styleFor().then((style) => {
  map.setStyle(style);
  map.once("idle", () => {
    if (map.getSource("state-2024")) colorMap(map, "state-2024");
    colorMap(map, activeSource);
  });
});
map.on("sourcedata", (event) => {
  if (event.sourceId === activeSource && event.isSourceLoaded) colorMap(map, activeSource);
  if (event.sourceId === "precinct-2024" && event.isSourceLoaded) colorMap(map, "precinct-2024");
});

void load();
