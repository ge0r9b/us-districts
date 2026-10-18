import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { gzipSync } from "node:zlib";
import { fileURLToPath } from "node:url";

const dist = fileURLToPath(new URL("../dist", import.meta.url));
const budget = 300 * 1024;

function jsFiles(dir: string): string[] {
  const out: string[] = [];
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) out.push(...jsFiles(path));
    else if (name.endsWith(".js")) out.push(path);
  }
  return out;
}

const files = jsFiles(dist);
let total = 0;
for (const file of files) total += gzipSync(readFileSync(file)).length;
const kb = (total / 1024).toFixed(1);
console.log(`js gzip ${kb} KB across ${files.length} files (budget 300 KB)`);
if (total > budget) {
  console.error(`bundle is over the 300 KB gzip budget (${kb} KB)`);
  process.exit(1);
}
