interface ImportMetaEnv {
  readonly BASE_URL: string;
  readonly VITE_TILES_BASE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
