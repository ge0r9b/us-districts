import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { locateInstPack } from "../../ingest/inst-pack.ts";
import { locatePack } from "../../ingest/precincts.ts";
import type { PackStore } from "./sql.ts";

const defaultPacksDir = fileURLToPath(new URL("../../app/public/packs/precinct", import.meta.url));
const defaultInstPacksDir = fileURLToPath(new URL("../../app/public/packs/inst", import.meta.url));

/** Node dev server and tests. Not imported by the Worker. */
export function nodePacks(packsDir = defaultPacksDir, instPacksDir = defaultInstPacksDir): PackStore {
  return {
    async locatePrecinct(state, year, office) {
      const hit = locatePack(packsDir, state, year, office);
      return hit ? { publicPath: hit.publicPath, sha: hit.sha } : null;
    },
    async readPrecinct(state, year, office) {
      const hit = locatePack(packsDir, state, year, office);
      if (!hit) return null;
      return readFileSync(hit.file, "utf8");
    },
    async locateInst() {
      const hit = locateInstPack(instPacksDir);
      return hit ? { publicPath: hit.publicPath, sha: hit.sha } : null;
    },
  };
}
