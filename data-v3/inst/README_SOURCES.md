# File family: sources (data-v3/inst/sources.csv)

One row per distinct source (document / download / pinned repo commit) that any `data-v3/inst` file rests on. Every row of
every other `data-v3/inst` CSV has `source_id` (a `;`-list when several) pointing here. Built by `tools/inst_sources.py`
(shared by data/inst-officeholders and data/inst-entities; both write the same ids, so the files merge as a union).

| column | meaning |
|---|---|
| `source_id` | `<slug>-<h8>`: `slug` = readable prefix from a fixed URL→slug table (`census-cog2022`, `census-gaz2024-counties`, `openstates-people`, `roster-tx` ...); `h8` = first 8 hex of sha256(`source_url` + `\|` + `commit`). Deterministic, never sequential: the same URL(s) + commit give the same id in every build |
| `source` | name of the source as cited (publisher, dataset, edition) |
| `source_url` | full URL(s), ` ; `-separated when one source spans several pages (House + Senate lists) |
| `license` | as stated by the source: `public domain (US government work)`, `CC0 1.0`, `official state legislature website (public record)` |
| `retrieved_at` | download date (YYYY-MM-DD) |
| `commit` | pinned upstream git commit (OpenStates people, unitedstates/congress-legislators, this repo's data/geo); empty otherwise |
| `sha256` | raw-download hash(es), `file sha; file sha` when the source is several files; empty when hashes are per row (OpenStates person files) |

A new commit or URL is a new source and a new id; the old id stays valid for rows that still use it.
Stability: `inst_oh_sources.py --stability-test` and `inst_entities.py --stability-test` rebuild the ids twice (second pass in
reverse row and table order) and require identical output, then re-derive every id from its own url + commit.
Licence of this file: CC0 1.0 (metadata only). Open public sources only.

SCHEMA.sql mapping: a row loads into `source` (`url` ← `source_url`, `publisher`/`title` ← `source`, `license`,
`retrieved_at`, `sha256`; `commit` and the text `source_id` go to `notes`/a lookup until `source` gets a text key).
