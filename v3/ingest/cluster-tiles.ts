import { mkdirSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import { zxyToTileId } from "pmtiles";

export type ClusterPoint = { lon: number; lat: number };

const ZOOM = 4;
const EXTENT = 4096;
const HEADER_BYTES = 127;

/**
 * PMTiles v3 of one zoom, one point per tile, property `count`.
 * The directory layout matches the pmtiles reader: a count, then tile-id deltas,
 * run lengths, lengths, and offsets stored as offset+1 (0 means continue).
 * Tile bytes are uncompressed MVT. This is the companies cluster, not a tippecanoe extract.
 */
export function buildClusterArchive(points: ClusterPoint[], zoom = ZOOM): Uint8Array {
  const groups = new Map<string, { x: number; y: number; lon: number; lat: number; n: number }>();
  for (const point of points) {
    if (!Number.isFinite(point.lon) || !Number.isFinite(point.lat)) continue;
    const xy = lonLatToTile(point.lon, point.lat, zoom);
    const key = `${xy.x},${xy.y}`;
    const prev = groups.get(key);
    if (prev) {
      prev.lon += point.lon;
      prev.lat += point.lat;
      prev.n += 1;
    } else groups.set(key, { x: xy.x, y: xy.y, lon: point.lon, lat: point.lat, n: 1 });
  }
  const tiles = [...groups.values()]
    .map((group) => {
      const lon = group.lon / group.n;
      const lat = group.lat / group.n;
      const tileId = zxyToTileId(zoom, group.x, group.y);
      const [px, py] = lonLatToPixel(lon, lat, zoom, group.x, group.y);
      return { tileId, bytes: mvtCluster(px, py, group.n), lon, lat };
    })
    .sort((a, b) => a.tileId - b.tileId);

  const entries: { tileId: number; runLength: number; length: number; offset: number }[] = [];
  const tileParts: Uint8Array[] = [];
  let cursor = 0;
  for (const tile of tiles) {
    entries.push({ tileId: tile.tileId, runLength: 1, length: tile.bytes.length, offset: cursor });
    tileParts.push(tile.bytes);
    cursor += tile.bytes.length;
  }
  const directory = encodeDirectory(entries);
  const metadata = new TextEncoder().encode(
    JSON.stringify({ vector_layers: [{ id: "clusters", fields: { count: "Number" } }] }),
  );
  const rootOffset = HEADER_BYTES;
  const metaOffset = rootOffset + directory.length;
  const tileOffset = metaOffset + metadata.length;
  let minLon = 180;
  let minLat = 90;
  let maxLon = -180;
  let maxLat = -90;
  for (const tile of tiles) {
    minLon = Math.min(minLon, tile.lon);
    minLat = Math.min(minLat, tile.lat);
    maxLon = Math.max(maxLon, tile.lon);
    maxLat = Math.max(maxLat, tile.lat);
  }
  if (tiles.length === 0) {
    minLon = -180;
    minLat = -85;
    maxLon = 180;
    maxLat = 85;
  }
  const header = encodeHeader({
    rootOffset,
    rootLength: directory.length,
    metaOffset,
    metaLength: metadata.length,
    tileOffset,
    tileLength: cursor,
    addressed: tiles.length,
    zoom,
    minLon,
    minLat,
    maxLon,
    maxLat,
  });
  const out = new Uint8Array(tileOffset + cursor);
  out.set(header, 0);
  out.set(directory, rootOffset);
  out.set(metadata, metaOffset);
  let at = tileOffset;
  for (const part of tileParts) {
    out.set(part, at);
    at += part.length;
  }
  return out;
}

export function writeClusterPmtiles(points: ClusterPoint[], outPath: string): number {
  const bytes = buildClusterArchive(points);
  mkdirSync(dirname(outPath), { recursive: true });
  writeFileSync(outPath, bytes);
  return bytes.length;
}

export function lonLatToTile(lon: number, lat: number, zoom: number): { x: number; y: number } {
  const n = 2 ** zoom;
  const x = Math.min(n - 1, Math.max(0, Math.floor(((lon + 180) / 360) * n)));
  const rad = (lat * Math.PI) / 180;
  const y = Math.min(n - 1, Math.max(0, Math.floor(((1 - Math.log(Math.tan(rad) + 1 / Math.cos(rad)) / Math.PI) / 2) * n)));
  return { x, y };
}

function lonLatToPixel(lon: number, lat: number, zoom: number, x: number, y: number): [number, number] {
  const n = 2 ** zoom;
  const fx = ((lon + 180) / 360) * n;
  const rad = (lat * Math.PI) / 180;
  const fy = ((1 - Math.log(Math.tan(rad) + 1 / Math.cos(rad)) / Math.PI) / 2) * n;
  const px = Math.round((fx - x) * EXTENT);
  const py = Math.round((fy - y) * EXTENT);
  return [Math.min(EXTENT, Math.max(0, px)), Math.min(EXTENT, Math.max(0, py))];
}

function encodeHeader(h: {
  rootOffset: number;
  rootLength: number;
  metaOffset: number;
  metaLength: number;
  tileOffset: number;
  tileLength: number;
  addressed: number;
  zoom: number;
  minLon: number;
  minLat: number;
  maxLon: number;
  maxLat: number;
}): Uint8Array {
  const buf = new Uint8Array(HEADER_BYTES);
  const view = new DataView(buf.buffer);
  buf.set(new TextEncoder().encode("PMTiles"), 0);
  view.setUint8(7, 3);
  setUint64(view, 8, h.rootOffset);
  setUint64(view, 16, h.rootLength);
  setUint64(view, 24, h.metaOffset);
  setUint64(view, 32, h.metaLength);
  setUint64(view, 40, 0);
  setUint64(view, 48, 0);
  setUint64(view, 56, h.tileOffset);
  setUint64(view, 64, h.tileLength);
  setUint64(view, 72, h.addressed);
  setUint64(view, 80, h.addressed);
  setUint64(view, 88, h.addressed);
  view.setUint8(96, 1);
  view.setUint8(97, 1);
  view.setUint8(98, 1);
  view.setUint8(99, 1);
  view.setUint8(100, h.zoom);
  view.setUint8(101, h.zoom);
  view.setInt32(102, Math.round(h.minLon * 1e7), true);
  view.setInt32(106, Math.round(h.minLat * 1e7), true);
  view.setInt32(110, Math.round(h.maxLon * 1e7), true);
  view.setInt32(114, Math.round(h.maxLat * 1e7), true);
  view.setUint8(118, h.zoom);
  view.setInt32(119, Math.round(((h.minLon + h.maxLon) / 2) * 1e7), true);
  view.setInt32(123, Math.round(((h.minLat + h.maxLat) / 2) * 1e7), true);
  return buf;
}

function setUint64(view: DataView, offset: number, value: number): void {
  view.setUint32(offset, value >>> 0, true);
  view.setUint32(offset + 4, Math.floor(value / 2 ** 32), true);
}

function encodeDirectory(entries: { tileId: number; runLength: number; length: number; offset: number }[]): Uint8Array {
  const out: number[] = [];
  writeVarint(entries.length, out);
  let last = 0;
  for (const entry of entries) {
    writeVarint(entry.tileId - last, out);
    last = entry.tileId;
  }
  for (const entry of entries) writeVarint(entry.runLength, out);
  for (const entry of entries) writeVarint(entry.length, out);
  for (const entry of entries) writeVarint(entry.offset + 1, out);
  return Uint8Array.from(out);
}

function writeVarint(value: number, out: number[]): void {
  let n = value;
  while (n >= 0x80) {
    out.push((n & 0x7f) | 0x80);
    n = Math.floor(n / 128);
  }
  out.push(n);
}

function mvtCluster(x: number, y: number, count: number): Uint8Array {
  const tags = [...varintBytes((2 << 3) | 2), ...varintBytes(2), ...varintBytes(0), ...varintBytes(0)];
  const geom = [...varintBytes((4 << 3) | 2), ...varintBytes(3), ...varintBytes(9), ...varintBytes(zigzag(x)), ...varintBytes(zigzag(y))];
  const feature = [...protoVarint((3 << 3) | 0), ...varintBytes(1), ...tags, ...geom];
  const value = [...protoVarint((4 << 3) | 0), ...varintBytes(count)];
  const layer = [
    ...protoString(1, "clusters"),
    ...protoBytes(2, feature),
    ...protoString(3, "count"),
    ...protoBytes(4, value),
    ...protoVarint((5 << 3) | 0),
    ...varintBytes(EXTENT),
    ...protoVarint((15 << 3) | 0),
    ...varintBytes(2),
  ];
  return Uint8Array.from(protoBytes(3, layer));
}

function protoString(field: number, value: string): number[] {
  return protoBytes(field, [...new TextEncoder().encode(value)]);
}

function protoBytes(field: number, bytes: number[]): number[] {
  return [...protoVarint((field << 3) | 2), ...varintBytes(bytes.length), ...bytes];
}

function protoVarint(n: number): number[] {
  return varintBytes(n);
}

function varintBytes(value: number): number[] {
  const out: number[] = [];
  writeVarint(value, out);
  return out;
}

function zigzag(n: number): number {
  return (n << 1) ^ (n >> 31);
}
