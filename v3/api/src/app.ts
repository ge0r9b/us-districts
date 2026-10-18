import { fileURLToPath } from "node:url";
import { Hono } from "hono";
import { cors } from "hono/cors";
import type pg from "pg";
import {
  applyFormat,
  cacheControl,
  compareAnswerKeys,
  isGray,
  matchesState,
  shares,
  sortRows,
  type SortBy,
  type SortDir,
  type ValueFormat,
} from "@usd/core";
import { geocodeAddress, locatePoint } from "./geocode.ts";
import { precinctResults } from "./precinct-results.ts";
import { locateInstPack } from "../../ingest/inst-pack.ts";
import { locatePack } from "../../ingest/precincts.ts";

const defaultPacksDir = fileURLToPath(new URL("../../app/public/packs/precinct", import.meta.url));
const defaultInstPacksDir = fileURLToPath(new URL("../../app/public/packs/inst", import.meta.url));

export type AppDeps = {
  pool: pg.Pool;
  fetchImpl?: typeof fetch;
  now?: () => number;
  sleep?: (ms: number) => Promise<void>;
  packsDir?: string;
  instPacksDir?: string;
};

type DvRow = { dv: number; built_at: Date | string };

async function readDv(pool: pg.Pool): Promise<DvRow> {
  const r = await pool.query<DvRow>("select dv, built_at from data_version where id = 1");
  return r.rows[0] ?? { dv: 1, built_at: new Date(0).toISOString() };
}

function parseBbox(raw: string | undefined): [number, number, number, number] | null {
  if (!raw) return null;
  const parts = raw.split(",").map((part) => Number(part.trim()));
  if (parts.length !== 4 || parts.some((n) => !Number.isFinite(n))) return null;
  const west = parts[0]!;
  const south = parts[1]!;
  const east = parts[2]!;
  const north = parts[3]!;
  if (south < -90 || north > 90 || south > north || west < -180 || east > 180 || west > east) return null;
  return [west, south, east, north];
}

function iso(value: Date | string): string {
  return value instanceof Date ? value.toISOString() : new Date(value).toISOString();
}

async function manifest(pool: pg.Pool) {
  const version = await readDv(pool);
  const offices = await pool.query<{ key: string; label: string }>(
    `select office_key as key, label from office order by office_key`,
  );
  return {
    dv: version.dv,
    built_at: iso(version.built_at),
    tiles: {
      "state-2024": "/tiles/state-2024@1.pmtiles",
      "county-2024": "/tiles/county-2024@1.pmtiles",
      "ushouse-2024": "/tiles/ushouse-2024@1.pmtiles",
      companies: "/tiles/companies.pmtiles",
      "precinct-2024": "/tiles/precinct-2024/{ST}.pmtiles",
    },
    packs: `/packs/${version.dv}/{contest_key}/{unit_type}.json`,
    precinct_packs: "/packs/precinct/{ST}/{year}/{office}/{sha}.json",
    institution_pack: "/packs/inst/{sha}.json",
    offices: offices.rows.map((row) => ({ key: row.key, label: row.label, scope: row.key === "president" ? "us" : null })),
  };
}

type AnswerRow = {
  contest_key: string;
  answer_key: string;
  label: string;
  is_aggregate: boolean;
  color: string | null;
  candidate_key: string | null;
  party_key: string | null;
  party_color: string | null;
};

function answerJson(row: AnswerRow) {
  return {
    key: row.answer_key,
    label: row.label,
    candidate: row.candidate_key,
    party: row.party_key,
    color: row.color ?? row.party_color,
    ...(row.is_aggregate ? { aggregate: true } : {}),
  };
}

export function createApp(deps: AppDeps) {
  const packsDir = deps.packsDir ?? defaultPacksDir;
  const instPacksDir = deps.instPacksDir ?? defaultInstPacksDir;
  const app = new Hono();
  app.use(
    "*",
    cors({
      origin: "*",
      allowMethods: ["GET", "OPTIONS", "HEAD"],
      allowHeaders: ["Authorization", "Content-Type", "Accept"],
      maxAge: 86400,
    }),
  );

  app.use("/api/v1/*", async (c, next) => {
    const version = await readDv(deps.pool);
    const raw = c.req.query("dv");
    if (raw != null && raw !== "") {
      if (!/^\d+$/.test(raw)) {
        return c.json({ error: { code: "bad_dv", message: "dv must be an integer" }, dv: version.dv }, 400);
      }
      if (Number(raw) !== version.dv) {
        const body = await manifest(deps.pool);
        return c.json(
          { error: { code: "gone", message: "That data version is not current" }, dv: version.dv, manifest: body },
          410,
        );
      }
      c.set("cacheKind", "pinned");
    } else {
      c.set("cacheKind", "open");
    }
    c.set("dv", version.dv);
    await next();
    if (c.req.path.endsWith("/manifest")) c.header("cache-control", cacheControl("manifest"));
    else if (c.req.path.endsWith("/geocode")) c.header("cache-control", cacheControl("geocode"));
    else if (c.req.path.endsWith("/locate")) c.header("cache-control", cacheControl("locate"));
    else c.header("cache-control", cacheControl(c.get("cacheKind") === "pinned" ? "pinned" : "open"));
  });

  app.get("/api/v1/manifest", async (c) => c.json(await manifest(deps.pool)));

  app.get("/api/v1/packs/institutions", (c) => {
    const found = locateInstPack(instPacksDir);
    if (!found) {
      return c.json(
        { error: { code: "pack_not_found", message: "No institution pack" }, dv: c.get("dv") },
        404,
      );
    }
    return c.redirect(found.publicPath, 302);
  });

  app.get("/api/v1/packs/precinct/:state/:year/:office", (c) => {
    const year = Number(c.req.param("year"));
    const found = locatePack(packsDir, c.req.param("state") ?? "", year, c.req.param("office") ?? "");
    if (!found) {
      return c.json(
        { error: { code: "pack_not_found", message: "No precinct pack for that state and contest" }, dv: c.get("dv") },
        404,
      );
    }
    return c.redirect(found.publicPath, 302);
  });

  app.get("/api/v1/contests", async (c) => {
    const year = c.req.query("year");
    const office = c.req.query("office");
    const state = c.req.query("state");
    const stage = c.req.query("stage");
    const kind = c.req.query("kind");
    const limit = Math.min(Number(c.req.query("limit") ?? 100) || 100, 500);
    const contests = await deps.pool.query<{
      contest_key: string;
      year: number;
      stage: string;
      kind: string;
      state_abbr: string | null;
      office_key: string;
      office_label: string;
      election_date: string | null;
    }>(
      `select c.contest_key, c.year, c.stage, c.kind, btrim(c.state_abbr) as state_abbr,
              o.office_key, o.label as office_label, c.election_date::text
       from contest c join office o on o.id = c.office_id
       where ($1::int is null or c.year = $1)
         and ($2::text is null or o.office_key = $2)
         and ($3::text is null or btrim(c.state_abbr) = $3)
         and ($4::text is null or c.stage = $4)
         and ($5::text is null or c.kind = $5)
       order by c.year desc, c.contest_key
       limit $6`,
      [year ? Number(year) : null, office ?? null, state ?? null, stage ?? null, kind ?? null, limit],
    );
    const keys = contests.rows.map((row) => row.contest_key);
    const answers = keys.length
      ? await deps.pool.query<AnswerRow>(
          `select c.contest_key, a.answer_key, a.label, a.is_aggregate, a.color,
                  cand.candidate_key, p.party_key, p.color as party_color
           from answer a
           join contest c on c.id = a.contest_id
           left join candidate cand on cand.id = a.candidate_id
           left join party p on p.id = a.party_id
           where c.contest_key = any($1::text[])`,
          [keys],
        )
      : { rows: [] as AnswerRow[] };
    const slots = keys.length
      ? await deps.pool.query<{ contest_key: string; slot: string; answer_key: string }>(
          `select c.contest_key, s.slot, a.answer_key
           from contest_display_slot s
           join contest c on c.id = s.contest_id
           join answer a on a.id = s.answer_id
           where c.contest_key = any($1::text[])`,
          [keys],
        )
      : { rows: [] as { contest_key: string; slot: string; answer_key: string }[] };
    const dv = c.get("dv") as number;
    return c.json({
      dv,
      items: contests.rows.map((row) => {
        const display: Record<string, string> = {};
        for (const slot of slots.rows.filter((s) => s.contest_key === row.contest_key)) display[slot.slot] = slot.answer_key;
        return {
          key: row.contest_key,
          office: row.office_key,
          label: row.office_label,
          year: row.year,
          date: row.election_date,
          stage: row.stage,
          kind: row.kind,
          state: row.state_abbr === "US" ? null : row.state_abbr,
          district: null,
          display_slots: display,
          answers: answers.rows
            .filter((a) => a.contest_key === row.contest_key)
            .sort((a, b) => compareAnswerKeys(a.answer_key, b.answer_key))
            .map(answerJson),
        };
      }),
      next: null,
    });
  });

  app.get("/api/v1/contests/:key", async (c) => {
    const key = c.req.param("key");
    const one = await deps.pool.query(
      `select c.contest_key from contest c where c.contest_key = $1`,
      [key],
    );
    if (one.rows.length === 0) {
      const dv = c.get("dv") as number;
      return c.json({ error: { code: "contest_not_found", message: "No contest with that key" }, dv }, 404);
    }
    const url = new URL(c.req.url);
    url.pathname = "/api/v1/contests";
    url.searchParams.set("limit", "500");
    const listed = await app.request(`/api/v1/contests?limit=500`);
    const body = (await listed.json()) as { items: { key: string }[]; dv: number };
    const item = body.items.find((row) => row.key === key);
    if (!item) return c.json({ error: { code: "contest_not_found", message: "No contest with that key" }, dv: c.get("dv") }, 404);
    return c.json({ dv: c.get("dv"), ...item });
  });

  app.get("/api/v1/results", async (c) => {
    const contestParams = c.req.queries("contest") ?? [];
    const unitType = c.req.query("unit_type");
    if (contestParams.length === 0 || !unitType) {
      return c.json(
        { error: { code: "bad_request", message: "contest and unit_type are required" }, dv: c.get("dv") },
        400,
      );
    }
    const state = c.req.query("state") ?? null;
    const boundary = c.req.query("boundary_set") ?? "v2-2024";
    const fmt = (c.req.query("fmt") ?? null) as ValueFormat;
    const sortAnswer = c.req.query("sort_answer");
    const by = (c.req.query("sort") === "votes" ? "votes" : "share") as SortBy;
    const dir = (c.req.query("dir") === "asc" ? "asc" : "desc") as SortDir;
    const dv = c.get("dv") as number;
    if (unitType === "precinct") {
      if (!state) {
        return c.json({ error: { code: "bad_request", message: "state is required for precincts" }, dv }, 400);
      }
      const built = precinctResults({
        packsDir,
        contests: contestParams,
        state,
        fmt,
        by,
        dir,
        sortAnswer: sortAnswer ?? null,
        dv,
        boundary,
      });
      return c.json(built.body, built.status as 200);
    }

    const contests = await deps.pool.query<{ contest_key: string }>(
      `select contest_key from contest where contest_key = any($1::text[])`,
      [contestParams],
    );
    if (contests.rows.length !== contestParams.length) {
      return c.json({ error: { code: "contest_not_found", message: "Unknown contest" }, dv }, 404);
    }

    const answerRows = await deps.pool.query<{ contest_key: string; answer_key: string }>(
      `select c.contest_key, a.answer_key
       from answer a join contest c on c.id = a.contest_id
       where c.contest_key = any($1::text[])`,
      [contestParams],
    );
    const answers = [...new Set(answerRows.rows.map((row) => row.answer_key))].sort(compareAnswerKeys);
    const slotRows = await deps.pool.query<{ contest_key: string; slot: string; answer_key: string }>(
      `select c.contest_key, s.slot, a.answer_key
       from contest_display_slot s
       join contest c on c.id = s.contest_id
       join answer a on a.id = s.answer_id
       where c.contest_key = any($1::text[])`,
      [contestParams],
    );

    const data = await deps.pool.query<{
      contest_key: string;
      unit_key: string;
      legacy_key: string | null;
      name: string;
      state_abbr: string | null;
      geoid: string | null;
      votes: Record<string, number> | null;
      mv_total: string | null;
      total_votes: string | null;
      is_estimate: boolean | null;
      coverage: number | null;
    }>(
      `select c.contest_key, u.unit_key, u.legacy_key, u.name, btrim(u.state_abbr) as state_abbr, u.geoid,
              a.votes, a.total::text as mv_total, rt.total_votes::text, a.is_estimate, rt.coverage
       from unit u
       join boundary_set b on b.id = u.boundary_set_id
       join contest c on c.contest_key = any($1::text[])
       left join unit_contest_agg a on a.contest_id = c.id and a.unit_id = u.id
       left join result_total rt on rt.contest_id = c.id and rt.unit_id = u.id
       where b.slug = $2 and u.unit_type = $3
         and ($4::text is null or btrim(u.state_abbr) = $4)`,
      [contestParams, boundary, unitType, state],
    );

    type Cell = {
      contest: string;
      votes: number[] | null;
      total: number | null;
      share: number[] | null;
      est: boolean;
      gray: boolean;
    };
    const byUnit = new Map<string, { unit: string; legacy: string | null; name: string; state: string | null; geoid: string | null; cells: Cell[] }>();
    for (const row of data.rows) {
      if (state && !matchesState(row.state_abbr, state)) continue;
      const has = row.votes != null;
      const total = row.total_votes != null ? Number(row.total_votes) : row.mv_total != null ? Number(row.mv_total) : null;
      const voteList = has ? answers.map((key) => Number(row.votes?.[key] ?? 0)) : null;
      const share = voteList && total != null ? shares(voteList, total) : null;
      const cell: Cell = {
        contest: row.contest_key,
        votes: voteList,
        total,
        share,
        est: row.is_estimate === true,
        gray: isGray(has, row.coverage),
      };
      const existing = byUnit.get(row.unit_key);
      if (existing) existing.cells.push(cell);
      else {
        byUnit.set(row.unit_key, {
          unit: row.unit_key,
          legacy: row.legacy_key,
          name: row.name,
          state: row.state_abbr,
          geoid: row.geoid,
          cells: [cell],
        });
      }
    }

    const sortKey = sortAnswer && answers.includes(sortAnswer) ? sortAnswer : (answers[0] ?? "dem_nominee");
    const sortIndex = Math.max(0, answers.indexOf(sortKey));
    const shaped = [...byUnit.values()].map((row) => {
      const primary = row.cells.find((cell) => cell.contest === contestParams[0]) ?? row.cells[0];
      return {
        ...row,
        share: primary?.share?.[sortIndex] ?? null,
        votes: primary?.votes?.[sortIndex] ?? null,
        gray: primary?.gray ?? true,
      };
    });
    const sorted = sortRows(shaped, by, dir);
    const displayFor = (key: string) => {
      const display: Record<string, string> = {};
      for (const slot of slotRows.rows.filter((s) => s.contest_key === key)) display[slot.slot] = slot.answer_key;
      return display;
    };

    if (contestParams.length === 1) {
      return c.json({
        dv,
        contest: contestParams,
        unit_type: unitType,
        boundary_set: boundary,
        answers,
        display_slots: displayFor(contestParams[0]!),
        rows: sorted.map((row) => {
          const cell = row.cells[0]!;
          const payload = {
            unit: row.unit,
            legacy: row.legacy,
            name: row.name,
            state: row.state,
            geoid: row.geoid,
            votes: cell.votes,
            total: cell.total,
            share: cell.share,
            est: cell.est,
            gray: cell.gray,
          };
          return applyFormat(payload, fmt);
        }),
      });
    }

    return c.json({
      dv,
      contest: contestParams,
      unit_type: unitType,
      boundary_set: boundary,
      answers,
      display_slots: Object.fromEntries(contestParams.map((key) => [key, displayFor(key)])),
      rows: sorted.map((row) => ({
        unit: row.unit,
        legacy: row.legacy,
        name: row.name,
        state: row.state,
        geoid: row.geoid,
        series: row.cells.map((cell) => applyFormat(cell, fmt)),
      })),
    });
  });

  app.get("/api/v1/units/:key", async (c) => {
    const key = c.req.param("key");
    const boundary = c.req.query("boundary_set") ?? "v2-2024";
    const unitType = c.req.query("unit_type") ?? null;
    const found = await deps.pool.query<{
      unit_key: string;
      legacy_key: string | null;
      name: string;
      unit_type: string;
      state_abbr: string | null;
      geoid: string | null;
      lon: number | null;
      lat: number | null;
      parent_key: string | null;
      parent_name: string | null;
    }>(
      `select u.unit_key, u.legacy_key, u.name, u.unit_type, btrim(u.state_abbr) as state_abbr, u.geoid,
              st_x(u.centroid) as lon, st_y(u.centroid) as lat,
              p.unit_key as parent_key, p.name as parent_name
       from unit u
       join boundary_set b on b.id = u.boundary_set_id
       left join unit p on p.id = u.parent_unit_id
       where b.slug = $1 and (u.unit_key = $2 or u.legacy_key = $2)
         and ($3::text is null or u.unit_type = $3)`,
      [boundary, key, unitType],
    );
    const dv = c.get("dv") as number;
    if (found.rows.length === 0) {
      return c.json({ error: { code: "unit_not_found", message: "No unit with that key" }, dv }, 404);
    }
    if (found.rows.length > 1) {
      return c.json({ error: { code: "ambiguous_unit", message: "Pass unit_type" }, dv }, 400);
    }
    const unit = found.rows[0]!;
    let results: unknown = undefined;
    const contest = c.req.query("contest");
    if (contest) {
      const sub = await app.request(
        `/api/v1/results?contest=${encodeURIComponent(contest)}&unit_type=${encodeURIComponent(unit.unit_type)}&boundary_set=${encodeURIComponent(boundary)}&state=${encodeURIComponent(unit.state_abbr ?? "")}`,
      );
      const body = (await sub.json()) as { rows?: { unit: string }[] };
      results = body.rows?.find((row) => row.unit === unit.unit_key) ?? null;
    }
    return c.json({
      dv,
      unit: unit.unit_key,
      legacy: unit.legacy_key,
      name: unit.name,
      unit_type: unit.unit_type,
      state: unit.state_abbr,
      geoid: unit.geoid,
      parent: unit.parent_key ? { unit: unit.parent_key, name: unit.parent_name } : null,
      centroid: unit.lon == null ? null : { lon: unit.lon, lat: unit.lat },
      boundary_set: boundary,
      ...(contest ? { contest, result: results } : {}),
    });
  });

  app.get("/api/v1/locations", async (c) => {
    const box = parseBbox(c.req.query("bbox"));
    const dv = c.get("dv") as number;
    if (!box) return c.json({ error: { code: "bad_bbox", message: "bbox is west,south,east,north" }, dv }, 400);
    const limit = Math.min(Math.max(Number(c.req.query("limit") ?? 500) || 500, 1), 500);
    const rows = await deps.pool.query<{
      location_key: string;
      name: string | null;
      country_code: string | null;
      lon: number;
      lat: number;
    }>(
      `select location_key, name, btrim(country_code) as country_code, st_x(geom) lon, st_y(geom) lat
       from entity_location
       where not retracted
         and geom && st_makeenvelope($1, $2, $3, $4, 4326)
       order by location_key
       limit $5`,
      [...box, limit],
    );
    return c.json({ dv, locations: rows.rows });
  });

  app.get("/api/v1/locations/clusters", async (c) => {
    const box = parseBbox(c.req.query("bbox"));
    const dv = c.get("dv") as number;
    if (!box) return c.json({ error: { code: "bad_bbox", message: "bbox is west,south,east,north" }, dv }, 400);
    const z = Math.min(6, Math.max(0, Number(c.req.query("z") ?? 4) || 4));
    const cell = 360 / 2 ** z;
    const rows = await deps.pool.query<{ n: number; lon: number; lat: number }>(
      `select count(*)::int n,
              st_x(st_centroid(st_collect(geom))) lon,
              st_y(st_centroid(st_collect(geom))) lat
       from entity_location
       where not retracted
         and geom && st_makeenvelope($1, $2, $3, $4, 4326)
       group by st_snaptogrid(geom, $5)
       limit 500`,
      [...box, cell],
    );
    return c.json({ dv, z, clusters: rows.rows });
  });

  app.get("/api/v1/geocode", async (c) => {
    const q = c.req.query("q") ?? "";
    const dv = c.get("dv") as number;
    const result = await geocodeAddress(
      { pool: deps.pool, fetchImpl: deps.fetchImpl, now: deps.now, sleep: deps.sleep },
      q,
      dv,
    );
    if (!result.ok) return c.json({ error: { code: result.code, message: result.message }, dv }, result.status as 400);
    return c.json(result.body);
  });

  app.get("/api/v1/locate", async (c) => {
    const lon = Number(c.req.query("lon"));
    const lat = Number(c.req.query("lat"));
    const dv = c.get("dv") as number;
    if (!Number.isFinite(lon) || !Number.isFinite(lat)) {
      return c.json({ error: { code: "bad_request", message: "lon and lat are required" }, dv }, 400);
    }
    return c.json(await locatePoint(deps.pool, lon, lat, dv));
  });

  return app;
}

declare module "hono" {
  interface ContextVariableMap {
    dv: number;
    cacheKind: "pinned" | "open";
  }
}
