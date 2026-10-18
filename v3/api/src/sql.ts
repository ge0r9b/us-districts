/** Web-shaped query. A Node `pg` pool and a Neon `Client` both satisfy it. */
export type Sql = {
  query<T extends Record<string, unknown> = Record<string, unknown>>(
    text: string,
    params?: unknown[],
  ): Promise<{ rows: T[] }>;
};

export type PackHit = { publicPath: string; sha: string };

/** Pack bytes are injected. The request path does not touch the filesystem. */
export type PackStore = {
  locatePrecinct(state: string, year: number, office: string): Promise<PackHit | null>;
  readPrecinct(state: string, year: number, office: string): Promise<string | null>;
  locateInst(): Promise<PackHit | null>;
};
