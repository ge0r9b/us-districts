# Native apps (v4/v5) and what v3 must do now

Roadmap: native macOS and iOS apps, built in Cursor, around v4/v5 (ARCHITECTURE.md §9). v3 stays API-first so those apps can be built without a rewrite.

## Full parity rule

**Goal (the user, relayed via Trailblazer on 2026-10-18 at 11:51 AM EDT):** "v4 native apps should fully match the browser app."

What this means for every v3 feature:

1. **Logic and data go through one of two shared paths.** Each feature's logic and data reach the UI through:
   - the versioned API, **`/api/v1`** (API.md), or
   - a **framework-free shared core** module: plain TypeScript with no DOM, React/Preact or browser globals.

   Examples of shared-core code: result math (shares, deltas, d/r slots), filters, sort and list rules, the time-slider state, formatting, and URL state ↔ app state. The native apps call the same API, and they either run the shared core (JavaScriptCore) or port it against its test fixtures.
2. **No browser-only logic.** The UI layer only renders and handles input. A rule that lives only in a component, a CSS selector or a DOM handler is a bug against this rule.
3. **UI rules are design tokens.** Colours (party, margin ramps), sizes (the 30 px thumbnails, badges), spacing, type scale, z-order and animation timings live in a token file (JSON). That file is exported to CSS variables for the web, and to Swift for native.
4. **The map uses PMTiles plus a style that MapLibre Native can load.** Only style-spec features that MapLibre Native supports are used: no custom JS layers and no DOM overlays carrying data. Feature-state colouring is driven by the same core and API data.

### PR checklist item

- [ ] **Does this feature work through `/api/v1` or the shared core with no DOM-only logic?**

### Allowed browser-only items (each has a native equivalent)

| Browser-only item | Why it stays in the web shell | Native equivalent |
|---|---|---|
| URL / deep-link handling (`history`, query string) | Web navigation. Parsing and serialising the state is shared core; only reading and writing `location` is web-only | Universal Links / custom URL scheme, using the same shared-core state codec |
| Service worker caching (packs, PMTiles, API GETs) | Offline and instant repeat loads on the web | `URLCache` / on-disk cache with the same cache keys and versioned URLs (immutable packs and tiles, ETag API) |
| `localStorage` / IndexedDB (preferences, last view) | Web persistence | `UserDefaults` / app container files, same keys and schema |
| Web Share API, clipboard, "copy link" | Web sharing | `ShareLink` / `UIActivityViewController`, `NSPasteboard` / `UIPasteboard` |
| Browser geolocation ("use my location") | Web permission model | Core Location. The point then goes to the same `/api/v1` point-in-polygon lookup |
| Responsive CSS breakpoints (phone / iPad / desktop) | Web layout | SwiftUI size classes, using the same token breakpoints |
| Keyboard shortcuts and focus handling | Web input | `keyboardShortcut` / `.focusable` modifiers, same action names from the core |
| Print / PDF export | Browser print | `ImageRenderer` / PDFKit, from the same data |
| Analytics / error beacons (`sendBeacon`) | Web transport | The native SDK or a URLSession post to the same endpoint and event names |

Anything not in this table that touches the DOM or browser APIs needs a note in the PR saying why, and what its native equivalent is.
