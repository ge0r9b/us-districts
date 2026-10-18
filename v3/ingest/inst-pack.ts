import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

export type InstExtraPack = {
  v2_layer: string[] | null;
  v2_key: string[] | null;
  v2_row: string[] | null;
  valid_from_source: string | null;
  inception_source: string | null;
  sources: string[] | null;
};

export type InstImagePack = {
  entity_id: string | null;
  feed_entity_id: string | null;
  role: string;
  attribution: string | null;
  source_url: string | null;
  usage_basis: string | null;
  note: string | null;
  sources: string[];
};

export type InstPack = {
  v: 3;
  extra: Record<string, InstExtraPack>;
  images: Record<string, InstImagePack>;
};

/** Pack key is (feed, feed_id, role). `primary` is the feed's primary flag. Codes stay as in the CSV. */
export type FeedMapPackRow = {
  feed: string;
  feed_id: string;
  role: string;
  primary: boolean;
  entity_id: string | null;
  status: string;
  note: string | null;
};

export type FeedEnum = { code: string; name: string };

export type FeedMapPack = {
  v: 3;
  feeds: FeedEnum[];
  statuses: FeedEnum[];
  rows: FeedMapPackRow[];
};

type PackIndex = Record<string, { sha: string; file: string }>;

export function instPacksRoot(repo: string): string {
  return join(repo, "v3/app/public/packs/inst");
}

export function imagePackKey(entityId: string | null, feedId: string | null, role: string): string {
  return `${entityId ?? ""}|${feedId ?? ""}|${role}`;
}

function sortedRecord<T>(rows: Record<string, T>): Record<string, T> {
  return Object.fromEntries(Object.entries(rows).sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0)));
}

function writeIndex(dir: string, key: string, sha: string, file: string): void {
  const indexPath = join(dir, "index.json");
  const index: PackIndex = existsSync(indexPath) ? (JSON.parse(readFileSync(indexPath, "utf8")) as PackIndex) : {};
  index[key] = { sha, file };
  writeFileSync(indexPath, JSON.stringify(index));
}

/** Later keys win. A foreign pass keeps domestic extras that it does not rewrite. */
export function mergeInstPack(base: InstPack | null, next: InstPack): InstPack {
  if (!base) return next;
  return {
    v: 3,
    extra: { ...base.extra, ...next.extra },
    images: { ...base.images, ...next.images },
  };
}

/** Content-hashed JSON. v2 keys, image attribution, and image sources are not queried in SQL. */
export function writeInstPack(dir: string, pack: InstPack): { sha256: string; publicPath: string; file: string } {
  const body: InstPack = {
    v: 3,
    extra: sortedRecord(pack.extra),
    images: sortedRecord(pack.images),
  };
  const json = JSON.stringify(body);
  const sha256 = createHash("sha256").update(json).digest("hex");
  const file = `${sha256.slice(0, 12)}.json`;
  mkdirSync(dir, { recursive: true });
  writeFileSync(join(dir, file), json);
  writeIndex(dir, "institutions", sha256, file);
  return { sha256, publicPath: `/packs/inst/${file}`, file: join(dir, file) };
}

/** Feed map is a pack. Nothing in this file is inserted into entity_feed_map. */
export function writeFeedMapPack(dir: string, pack: FeedMapPack): { sha256: string; publicPath: string; file: string } {
  const body: FeedMapPack = {
    v: 3,
    feeds: [...pack.feeds].sort((a, b) => (a.code < b.code ? -1 : a.code > b.code ? 1 : 0)),
    statuses: [...pack.statuses].sort((a, b) => (a.code < b.code ? -1 : a.code > b.code ? 1 : 0)),
    rows: [...pack.rows].sort((a, b) => {
      if (a.feed !== b.feed) return a.feed < b.feed ? -1 : 1;
      if (a.feed_id !== b.feed_id) return a.feed_id < b.feed_id ? -1 : 1;
      return a.role < b.role ? -1 : a.role > b.role ? 1 : 0;
    }),
  };
  const json = JSON.stringify(body);
  const sha256 = createHash("sha256").update(json).digest("hex");
  const file = `${sha256.slice(0, 12)}.json`;
  mkdirSync(dir, { recursive: true });
  writeFileSync(join(dir, file), json);
  writeIndex(dir, "feed_map", sha256, file);
  return { sha256, publicPath: `/packs/inst/${file}`, file: join(dir, file) };
}

export function locateInstPack(dir: string): { file: string; publicPath: string; sha: string } | null {
  const indexPath = join(dir, "index.json");
  if (!existsSync(indexPath)) return null;
  const index = JSON.parse(readFileSync(indexPath, "utf8")) as PackIndex;
  const hit = index.institutions;
  if (!hit || !existsSync(join(dir, hit.file))) return null;
  return { file: join(dir, hit.file), publicPath: `/packs/inst/${hit.file}`, sha: hit.sha };
}

export function readInstPack(dir: string): InstPack | null {
  const found = locateInstPack(dir);
  if (!found) return null;
  return JSON.parse(readFileSync(found.file, "utf8")) as InstPack;
}

export function locateFeedMapPack(dir: string): { file: string; publicPath: string; sha: string } | null {
  const indexPath = join(dir, "index.json");
  if (!existsSync(indexPath)) return null;
  const index = JSON.parse(readFileSync(indexPath, "utf8")) as PackIndex;
  const hit = index.feed_map;
  if (!hit || !existsSync(join(dir, hit.file))) return null;
  return { file: join(dir, hit.file), publicPath: `/packs/inst/${hit.file}`, sha: hit.sha };
}

export function readFeedMapPack(dir: string): FeedMapPack | null {
  const found = locateFeedMapPack(dir);
  if (!found) return null;
  return JSON.parse(readFileSync(found.file, "utf8")) as FeedMapPack;
}
