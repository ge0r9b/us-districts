import { fileURLToPath } from "node:url";
import { join } from "node:path";
import { createPool, databaseUrl } from "../ingest/db.ts";
import { exportStaticSample } from "../ingest/static-export.ts";

const root = fileURLToPath(new URL("..", import.meta.url));
const pool = createPool(databaseUrl());
try {
  const { dv, files } = await exportStaticSample(pool, {
    packsDir: join(root, "app/public/packs/static"),
    tilesDir: join(root, "app/public/tiles"),
  });
  console.log(`static export dv ${dv}, ${files.length} files`);
  for (const file of files) console.log(`${file.bytes}\t${file.path}`);
} finally {
  await pool.end();
}
