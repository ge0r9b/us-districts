/** v2 integer-delta rings → GeoJSON MultiPolygon coordinates (lon, lat). */

function isFlat(a: unknown[]): boolean {
  return a.length > 0 && typeof a[0] === "number";
}

/** polygons → rings of flat delta arrays. National layers nest polygon → ring → numbers. */
export function polygonsOf(node: unknown): number[][][] {
  if (!Array.isArray(node) || node.length === 0) return [];
  if (isFlat(node)) return [[node as number[]]];
  const first = node[0];
  if (!Array.isArray(first)) return [];
  if (isFlat(first)) return [node as number[][]];
  return (node as unknown[][]).map((poly) => {
    if (!Array.isArray(poly)) return [];
    if (isFlat(poly)) return [poly as unknown as number[]];
    return poly as number[][];
  });
}

export function decodeRing(flat: number[], scale: number): number[][] {
  if (flat.length < 2) return [];
  const out: number[][] = [];
  let x = flat[0]! / scale;
  let y = flat[1]! / scale;
  const push = (px: number, py: number) => {
    out.push([Math.round(px * 1e6) / 1e6, Math.round(py * 1e6) / 1e6]);
  };
  push(x, y);
  for (let i = 2; i + 1 < flat.length; i += 2) {
    x += flat[i]! / scale;
    y += flat[i + 1]! / scale;
    push(x, y);
  }
  const a = out[0];
  const b = out[out.length - 1];
  if (a && b && (a[0] !== b[0] || a[1] !== b[1])) out.push([a[0]!, a[1]!]);
  return out;
}

export function multiPolygon(node: unknown, scale: number): { type: "MultiPolygon"; coordinates: number[][][][] } | null {
  const polygons = polygonsOf(node)
    .map((rings) => rings.map((ring) => decodeRing(ring, scale)).filter((ring) => ring.length >= 4))
    .filter((rings) => rings.length > 0);
  if (polygons.length === 0) return null;
  return { type: "MultiPolygon", coordinates: polygons };
}

/** Strip a v2 loader wrapper and JSON.parse the payload. Never eval. */
export function unwrapJson(source: string): unknown {
  const obj = source.indexOf("{");
  const arr = source.indexOf("[");
  let start = -1;
  if (obj === -1) start = arr;
  else if (arr === -1) start = obj;
  else start = Math.min(obj, arr);
  const end = Math.max(source.lastIndexOf("}"), source.lastIndexOf("]"));
  if (start < 0 || end < start) throw new Error("no JSON payload in v2 file");
  return JSON.parse(source.slice(start, end + 1));
}
