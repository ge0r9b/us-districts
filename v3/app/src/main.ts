import maplibregl from "maplibre-gl";
import { Protocol } from "pmtiles";
import "maplibre-gl/dist/maplibre-gl.css";
import { sortRows } from "@usd/core";
import tokens from "../../design/tokens.json";
import mapStyle from "../../styles/map.json";
import "./style.css";

type Tokens = typeof tokens;
type ResultRow = {
  unit: string;
  legacy: string | null;
  name: string;
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

const YEARS = [2016, 2020, 2024] as const;
let year: (typeof YEARS)[number] = 2016;
let fmt: "pct" | "num" = "pct";
let body: ResultsBody | null = null;

const yearsEl = document.querySelector<HTMLElement>("#years")!;
const listEl = document.querySelector<HTMLOListElement>("#list")!;
const fmtBtn = document.querySelector<HTMLButtonElement>("#fmt")!;

function viewFor(y: number): { unitType: string; state: string | null } {
  if (y === 2016) return { unitType: "state", state: null };
  return { unitType: "county", state: "PA" };
}

function paintYears() {
  yearsEl.replaceChildren();
  for (const y of YEARS) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "glass" + (y === year ? " on" : "");
    btn.textContent = String(y);
    btn.addEventListener("click", () => {
      year = y;
      paintYears();
      void load();
    });
    yearsEl.append(btn);
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
  listEl.replaceChildren();
  if (rows.length === 0) {
    const li = document.createElement("li");
    li.className = "empty";
    li.textContent = "No rows";
    listEl.append(li);
    return;
  }
  for (const row of rows) {
    const li = document.createElement("li");
    const swatch = document.createElement("span");
    swatch.className = "swatch";
    const dem = row.share?.[0] ?? 0;
    const rep = row.share?.[1] ?? 0;
    if (!row.gray) swatch.style.background = dem >= rep ? color.dem : color.rep;
    const name = document.createElement("span");
    name.className = "name";
    name.textContent = row.name;
    const val = document.createElement("span");
    val.className = "val";
    if (row.gray) val.textContent = "—";
    else if (fmt === "num") val.textContent = (row.votes?.[0] ?? 0).toLocaleString("en-US");
    else val.textContent = pct(row.share?.[0] ?? 0);
    const bar = document.createElement("span");
    bar.className = "bar";
    if (!row.gray && row.share) {
      const d = document.createElement("i");
      d.className = "d";
      d.style.width = `${(row.share[0] ?? 0) * 100}%`;
      const r = document.createElement("i");
      r.className = "r";
      r.style.width = `${(row.share[1] ?? 0) * 100}%`;
      const o = document.createElement("i");
      o.className = "o";
      o.style.width = `${(row.share[2] ?? 0) * 100}%`;
      bar.append(d, r, o);
    }
    li.append(swatch, name, val, bar);
    listEl.append(li);
  }
}

function colorMap(map: maplibregl.Map, source: string) {
  const features = map.querySourceFeatures(source);
  const seen = new Set<string | number>();
  for (const feature of features) {
    const id = feature.id;
    if (id == null || seen.has(id)) continue;
    seen.add(id);
    const row = body?.rows.find((item) => item.unit === String(id));
    const gray = !row || row.gray || row.share == null;
    const margin = gray ? 0 : (row.share?.[1] ?? 0) - (row.share?.[0] ?? 0);
    map.setFeatureState({ source, id }, { gray: gray ? 1 : 0, margin });
  }
}

async function styleFor(origin: string): Promise<maplibregl.StyleSpecification> {
  const style = structuredClone(mapStyle) as maplibregl.StyleSpecification;
  const text = JSON.stringify(style).replaceAll("{origin}", origin);
  const parsed = JSON.parse(text) as maplibregl.StyleSpecification;
  const tiles = parsed.sources?.["state-2024"];
  const url = tiles && "url" in tiles ? String(tiles.url).replace(/^pmtiles:\/\//, "") : "";
  let pmtilesOk = false;
  if (url) {
    try {
      const head = await fetch(url, { headers: { range: "bytes=0-15" } });
      if (head.ok || head.status === 206) {
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

async function load() {
  const view = viewFor(year);
  const params = new URLSearchParams({
    contest: `${year}|US|president|`,
    unit_type: view.unitType,
  });
  if (view.state) params.set("state", view.state);
  const res = await fetch(`/api/v1/results?${params}`);
  if (!res.ok) {
    body = null;
    paintList();
    return;
  }
  body = (await res.json()) as ResultsBody;
  paintList();
  if (map.isStyleLoaded()) colorMap(map, activeSource);
}

fmtBtn.addEventListener("click", () => {
  fmt = fmt === "pct" ? "num" : "pct";
  fmtBtn.textContent = fmt === "pct" ? "%" : "#";
  fmtBtn.classList.toggle("on", fmt === "num");
  paintList();
});

paintYears();

const origin = location.origin;
const activeSource = "state-geojson";
const map = new maplibregl.Map({
  container: "map",
  style: { version: 8, sources: {}, layers: [] },
  center: [-98.5, 39.5],
  zoom: 3.2,
  attributionControl: {},
});

void styleFor(origin).then((style) => {
  map.setStyle(style);
  map.once("idle", () => {
    colorMap(map, activeSource);
  });
});
map.on("sourcedata", (event) => {
  if (event.sourceId === activeSource && event.isSourceLoaded) colorMap(map, activeSource);
});

void load();
