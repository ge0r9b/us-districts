# Repo rules (us-districts)

Orchestrator: **Grok Bot**. It assigns work, reviews and merges, and is the only one who edits `v2/index.html` or bumps `window.BUILD`.

## Lanes
| Bot | Owns | Branch / clone |
|---|---|---|
| Grok Bot (orchestrator + features) | `v2/index.html`, `tests/`, BUILD, releases/tags | main, /workspace/w/us-districts-app |
| Geo & Institution Data | boundary + institution data under `data/` (and `data-v3/geo/`) | `data/geo`, /workspace/w/lanes/geo-data |
| Election Data | results data under `data/` (and `data-v3/results/`), candidate directory | `data/election`, /workspace/w/lanes/election-data |
| Bug Tester | `BUGS.md` only; never edits the app | `qa/bugs`, /workspace/w/lanes/qa |
| v3 Full Stack | `v3/`, `docs/v3/` only | `v3/plan`, /workspace/w/lanes/v3 |

## Rules
1. Work only in your own clone and branch. Never in another lane's folder.
2. Touch only the files your lane owns. Need a change elsewhere? Ask the orchestrator.
3. Small commits; `git pull --rebase` before every push; never force-push main.
4. Data: official sources first, then VEST / MEDSL / OpenElections. Never estimate or invent numbers. Log gaps with reasons. Keep raw downloads untouched; cite every source.
5. v2 stays a static app. v1 (root) and `/test` are never changed. v3 does not deploy or merge to main until v2.0 is tagged and the user approves.
6. Local test ports: orchestrator 8843; Bug Tester 8850-8859; others 8860-8899. Never 8765.
7. Instant response time is the top priority in every UI change.
