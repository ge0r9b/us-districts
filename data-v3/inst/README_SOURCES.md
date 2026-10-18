# File family: sources (data-v3/inst/sources.csv)

One row per distinct source (document / download / pinned repo commit) that any `data-v3/inst` file rests on. Every row of
every other `data-v3/inst` CSV (entities, relations, images, gaps, geoid xwalk, v2 rows, body files, pack/entity_feed_map)
has a `source_set` pointing here through `source_sets.csv` (Full Stack ruling on 04227d3; until then each row carried the
`;`-list of `source_id`s itself). `source_urls.csv` keeps `source_id` (it describes the sources themselves).

## source_sets.csv
| column | meaning |
|---|---|
| `source_set` | 8-hex key: first 8 hex of sha256 of the exact `;`-joined, ordered list of the row's `source_id`s. Derived only from the sources' deterministic ids, so it is the same in every build and independent of row order; the builder asserts no two lists share a key |
| `ord` | position of the source in the row's list (1 = first cited) |
| `source_id` | key of `sources.csv` |

A row's sources = `source_sets` rows with its `source_set`, ordered by `ord`; an empty `source_set` means no source cited
(none today in the entity tables).

## sources.csv Built by `tools/inst_sources.py`
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

A new commit or URL is a new source and a new id; the old id stays valid for rows that still use it. A row citing a new
source list gets a new `source_set` key; existing keys never change meaning.
Stability: `inst_oh_sources.py --stability-test` and `inst_entities.py --stability-test` rebuild the ids (and so the
`source_set` keys) twice (second pass in
reverse row and table order) and require identical output, then re-derive every id from its own url + commit.
Licence of this file: CC0 1.0 (metadata only). Open public sources only.

SCHEMA.sql mapping: a row loads into `source` (`url` ← `source_url`, `publisher`/`title` ← `source`, `license`,
`retrieved_at`, `sha256`; `commit` and the text `source_id` go to `notes`/a lookup until `source` gets a text key);
`source_sets.csv` is the link table (`source_set`, `ord`, `source_id`), loaded with the other `db` files of
`load_manifest.csv`.
