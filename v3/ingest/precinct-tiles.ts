import { mkdirSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import { zxyToTileId } from "pmtiles";
import { lonLatToTile, writeVectorPmtiles } from "./cluster-tiles.ts";
import type { PrecinctFeature } from "./precinct-source.ts";

const ZOOM = 8;
const EXTENT = 4096;
const MAX_POINTS = 48;

export function writePrecinctPmtiles(features: PrecinctFeature[], outPath: string): number {
  const bytes = buildPrecinctArchive(features);
  mkdirSync(dirname(outPath), { recursive: true });
  writeFileSync(outPath, bytes);
  return bytes.length;
}

export function buildPrecinctArchive(features: PrecinctFeature[]): Uint8Array {
  const buckets = new Map<string, PrecinctFeature[]>();
  let minLon = 180;
  let minLat = 90;
  let maxLon = -180;
  let maxLat = -90;
  for (const feature of features) {
    if (feature.coordinates.length === 0) continue;
    const box = boundsOf(feature);
    minLon = Math.min(minLon, box.minLon);
    minLat = Math.min(minLat, box.minLat);
    maxLon = Math.max(maxLon, box.maxLon);
    maxLat = Math.max(maxLat, box.maxLat);
    const nw = lonLatToTile(box.minLon, box.maxLat, ZOOM);
    const se = lonLatToTile(box.maxLon, box.minLat, ZOOM);
    for (let x = nw.x; x <= se.x; x++) {
      for (let y = nw.y; y <= se.y; y++) {
        const key = `${x}:${y}`;
        const list = buckets.get(key);
        if (list) list.push(feature);
        else buckets.set(key, [feature]);
      }
    }
  }
  if (buckets.size === 0) {
    minLon = -180;
    minLat = -85;
    maxLon = 180;
    maxLat = 85;
  }
  const tiles = [...buckets.entries()].map(([key, group]) => {
    const [x, y] = key.split(":").map(Number) as [number, number];
    return { tileId: zxyToTileId(ZOOM, x, y), bytes: encodeTile(group, x, y) };
  });
  return writeVectorPmtiles({
    tiles,
    metadata: JSON.stringify({
      vector_layers: [{ id: "precincts", fields: { id: "String", name: "String", parent: "String" } }],
    }),
    zoom: ZOOM,
    minLon,
    minLat,
    maxLon,
    maxLat,
    clustered: false,
  });
}

function boundsOf(feature: PrecinctFeature): { minLon: number; minLat: number; maxLon: number; maxLat: number } {
  let minLon = 180;
  let minLat = 90;
  let maxLon = -180;
  let maxLat = -90;
  for (const polygon of feature.coordinates) {
    for (const point of polygon[0] ?? []) {
      minLon = Math.min(minLon, point[0] ?? 0);
      maxLon = Math.max(maxLon, point[0] ?? 0);
      minLat = Math.min(minLat, point[1] ?? 0);
      maxLat = Math.max(maxLat, point[1] ?? 0);
    }
  }
  return { minLon, minLat, maxLon, maxLat };
}

function encodeTile(features: PrecinctFeature[], tileX: number, tileY: number): Uint8Array {
  const keys = ["id", "name", "parent"];
  const values: string[] = [];
  const valueIndex = (text: string) => {
    const found = values.indexOf(text);
    if (found >= 0) return found;
    values.push(text);
    return values.length - 1;
  };
  const layers: number[] = [...protoString(1, "precincts")];
  for (const feature of features) {
    const rings = feature.coordinates
      .slice(0, 2)
      .map((polygon) => simplify(polygon[0] ?? []).map((point) => project(point[0] ?? 0, point[1] ?? 0, tileX, tileY)))
      .filter((ring) => ring.length >= 3);
    if (rings.length === 0) continue;
    const tags = [0, valueIndex(feature.id), 1, valueIndex(feature.name), 2, valueIndex(feature.county)];
    const geom = geometry(rings);
    const body = [
      ...varint((1 << 3) | 0),
      ...varint(feature.ordinal + 1),
      ...protoBytes(2, pack(tags)),
      ...varint((3 << 3) | 0),
      ...varint(3),
      ...protoBytes(4, pack(geom)),
    ];
    layers.push(...protoBytes(2, body));
  }
  for (const key of keys) layers.push(...protoString(3, key));
  for (const value of values) layers.push(...protoBytes(4, protoString(1, value)));
  layers.push(...varint((5 << 3) | 0), ...varint(EXTENT), ...varint((15 << 3) | 0), ...varint(2));
  return Uint8Array.from(protoBytes(3, layers));
}

function project(lon: number, lat: number, tileX: number, tileY: number): [number, number] {
  const n = 2 ** ZOOM;
  const fx = ((lon + 180) / 360) * n;
  const rad = (lat * Math.PI) / 180;
  const fy = ((1 - Math.log(Math.tan(rad) + 1 / Math.cos(rad)) / Math.PI) / 2) * n;
  const px = Math.round((fx - tileX) * EXTENT);
  const py = Math.round((fy - tileY) * EXTENT);
  return [Math.min(12288, Math.max(-8192, px)), Math.min(12288, Math.max(-8192, py))];
}

function simplify(ring: number[][]): number[][] {
  const open = ring.length > 1 && same(ring[0]!, ring[ring.length - 1]!) ? ring.slice(0, -1) : ring;
  if (open.length <= MAX_POINTS) return open;
  const step = Math.ceil(open.length / MAX_POINTS);
  const out: number[][] = [];
  for (let i = 0; i < open.length; i += step) out.push(open[i]!);
  return out;
}

function same(a: number[], b: number[]): boolean {
  return a[0] === b[0] && a[1] === b[1];
}

function geometry(rings: [number, number][][]): number[] {
  const geom: number[] = [];
  for (const ring of rings) {
    let cx = 0;
    let cy = 0;
    const [x0, y0] = ring[0]!;
    geom.push(9, zigzag(x0 - cx), zigzag(y0 - cy));
    cx = x0;
    cy = y0;
    const rest = ring.slice(1);
    geom.push((rest.length << 3) | 2);
    for (const [x, y] of rest) {
      geom.push(zigzag(x - cx), zigzag(y - cy));
      cx = x;
      cy = y;
    }
    geom.push(15);
  }
  return geom;
}

function pack(values: number[]): number[] {
  const out: number[] = [];
  for (const value of values) out.push(...varint(value));
  return out;
}

function zigzag(n: number): number {
  return (n << 1) ^ (n >> 31);
}

function protoString(field: number, value: string): number[] {
  return protoBytes(field, [...new TextEncoder().encode(value)]);
}

function protoBytes(field: number, bytes: number[]): number[] {
  return [...varint((field << 3) | 2), ...varint(bytes.length), ...bytes];
}

function varint(value: number): number[] {
  const out: number[] = [];
  let n = value >>> 0;
  while (n >= 0x80) {
    out.push((n & 0x7f) | 0x80);
    n = Math.floor(n / 128);
  }
  out.push(n);
  return out;
}
