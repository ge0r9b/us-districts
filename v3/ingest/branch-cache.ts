import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const STAMP = ".commit";

/** Fetch the named origin branches. A failure leaves whatever ref is already local. */
export function fetchOrigin(root: string, branches: string[]): void {
  if (branches.length === 0) return;
  try {
    execFileSync("git", ["fetch", "--no-tags", "origin", ...branches], {
      cwd: root,
      stdio: "pipe",
      timeout: 120_000,
    });
  } catch {
    // The ref may already be on disk from an earlier fetch.
  }
}

export function originCommit(root: string, branch: string): string {
  try {
    return execFileSync("git", ["rev-parse", `origin/${branch}`], { cwd: root, encoding: "utf8" }).trim();
  } catch {
    return "";
  }
}

export function cachedCommit(dir: string): string {
  const path = join(dir, STAMP);
  if (!existsSync(path)) return "";
  return readFileSync(path, "utf8").trim();
}

export function stampCommit(dir: string, commit: string): void {
  if (!commit) return;
  mkdirSync(dir, { recursive: true });
  writeFileSync(join(dir, STAMP), `${commit}\n`);
}

/** True when a marker is missing, or the stamped commit is not the origin commit. */
export function needsRefresh(dir: string, commit: string, markers: string[]): boolean {
  if (markers.some((rel) => !existsSync(join(dir, rel)))) return true;
  if (!commit) return false;
  return cachedCommit(dir) !== commit;
}
