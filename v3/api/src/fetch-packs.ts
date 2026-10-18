import type { PackHit, PackStore } from "./sql.ts";

type IndexFile = Record<string, { sha: string; file: string }>;

async function readIndex(url: string): Promise<IndexFile | null> {
  if (!url) return null;
  try {
    const res = await fetch(url);
    if (!res.ok) return null;
    return (await res.json()) as IndexFile;
  } catch {
    return null;
  }
}

/** Worker pack reads. `base` is PACKS_BASE, for example an R2 public URL, with no trailing slash. */
export function fetchPacks(base: string): PackStore {
  const root = base.replace(/\/$/, "");
  let precincts: Promise<IndexFile | null> | null = null;
  let inst: Promise<IndexFile | null> | null = null;
  const precinctIndex = () => {
    precincts ??= readIndex(root ? `${root}/precinct/index.json` : "");
    return precincts;
  };
  const instIndex = () => {
    inst ??= readIndex(root ? `${root}/inst/index.json` : "");
    return inst;
  };
  return {
    async locatePrecinct(state, year, office) {
      const index = await precinctIndex();
      const hit = index?.[`${state.toUpperCase()}|${year}|${office}`];
      if (!hit) return null;
      return { publicPath: root ? `${root}/precinct/${hit.file}` : `/packs/precinct/${hit.file}`, sha: hit.sha };
    },
    async readPrecinct(state, year, office) {
      const hit = await this.locatePrecinct(state, year, office);
      if (!hit || !root) return null;
      const res = await fetch(hit.publicPath);
      if (!res.ok) return null;
      return res.text();
    },
    async locateInst(): Promise<PackHit | null> {
      const index = await instIndex();
      const hit = index?.institutions;
      if (!hit) return null;
      return { publicPath: root ? `${root}/inst/${hit.file}` : `/packs/inst/${hit.file}`, sha: hit.sha };
    },
  };
}
