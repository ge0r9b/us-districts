import { defineConfig } from "vite";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  root: fileURLToPath(new URL("./app", import.meta.url)),
  publicDir: fileURLToPath(new URL("./app/public", import.meta.url)),
  resolve: {
    alias: {
      "@usd/core": fileURLToPath(new URL("./packages/core/src/index.ts", import.meta.url)),
    },
  },
  server: {
    host: "127.0.0.1",
    port: 8860,
    strictPort: true,
    fs: { allow: [root] },
    proxy: {
      "/api": "http://127.0.0.1:8861",
    },
  },
  preview: {
    host: "127.0.0.1",
    port: 8860,
    strictPort: true,
    proxy: {
      "/api": "http://127.0.0.1:8861",
    },
  },
  build: {
    outDir: fileURLToPath(new URL("./dist", import.meta.url)),
    emptyOutDir: true,
  },
  // root is referenced so the config file stays anchored at v3/
  cacheDir: `${root}/node_modules/.vite`,
});
