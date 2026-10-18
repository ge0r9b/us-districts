# Repository: ge0r9b/v3

Moved from **ge0r9b/us-districts** on **2026-10-18**. The full history came over, including the shared v2 history, so provenance stays traceable. **v2 lives at ge0r9b/us-districts**; this repo holds v3 only.

## Branches copied (source heads at the time of the move)
| Branch | Source sha in us-districts |
|---|---|
| `v3/plan` | `1057e73e8864c5ea6d1eb468281520bf3b937de5` (plus this note) |
| `v3/build` | `20e8b3d2c74c4828c826000c1bc25f77dc505106` |
| `main` | started from `v3/plan` at `1057e73`, plus this note |
| `data/election` | `0e058f78bb4eaa60da90762727f74d3ec760d128` |
| `data/geo` | `a92f2b0421b7ebe35d737481353280e25357c58d` |
| `data/companies` | `70220112e3bad478cc2ec8bbd8371f2382108c1f` |
| `data/governments` | `bd0ce1a98874f74acca1f806ead45c033f2aad80` |
| `data/people` | `7dbfd95af8559ca5169bfb764d212f47e1f84155` |
| `data/inst-entities` | `f0f1f6de52e18b829696ece1e70327a187667215` |
| `data/inst-canada` | `b8acf3448bd6d7e995c27c1496397826669fb07d` |
| `data/inst-officeholders` | `ffdf738b171f4f3cdb317e0f41a5b5d2ca84892f` |
| `data/inst-audit` | `5072d0d8672fd34b80b8730f9f1c5e25940320f0` |
| `data/inst-fixes` | `b68c7be5b6ad24bf2ac945b7423330d7b161d18d` |
| `data/inst-gray2` | `b22c129b594437a5427d821e584a224fc1f1e698` |

No v3 tags existed in us-districts, so none were copied. v2 tags stay in us-districts.

## Data branches are mirrors
The `data/*` branches here are **read-only mirrors** of the same branches in us-districts. The data bots still write to **us-districts** until each one is repointed to this repo. Until then, a box script (`/workspace/w/v3-mirror.sh`) fast-forwards them from us-districts. Do not commit to the `data/*` branches here while they are mirrors: a diverged branch stops the fast-forward.
