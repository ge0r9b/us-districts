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
4. **Icons (flags, seals, logos) render as they are.** Inside the fixed 30 px thumbnail, an icon uses `object-fit: contain` on a transparent background (native: `.scaledToFit()` / `contentMode = .scaleAspectFit`, with a clear background). Non-rectangular flags such as Nepal's display in their true shape, with no fallback, cropping or substitute box. The thumbnail size and transparency are design tokens.
5. **The map uses PMTiles plus a style that MapLibre Native can load.** Only style-spec features that MapLibre Native supports are used: no custom JS layers and no DOM overlays carrying data. Feature-state colouring is driven by the same core and API data.

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

## Same app on web and native (user refinements, 2026-10-18)

The user, relayed via Trailblazer, at **11:52 AM EDT**:

> "they will be idenitical except for what apple allows its native developers to do better, unfortunately the browser version will sometimes have a url bar and navigation popup futher"

**Rule:** web and native have identical features and identical design. Native may go further only where Apple's APIs allow it. Each such item is an **optional enhancement over a shared baseline** that the web also has, never a feature only native has:

| Native enhancement (optional) | Shared baseline (web and native) |
|---|---|
| Haptics (selection and impact feedback on slider, filter and pin) | The same interaction with visual feedback (pressed state, animation tokens) |
| Widgets (Home / Lock Screen / desktop: a watched contest or district) | The same view as a shareable deep link / pinned view in the app |
| Live Activities (election-night count for a watched contest) | The same live contest view with auto-refresh in the app and on the web |
| Share sheet (`ShareLink`) | Web Share API, or copy link, with the same URL and title |
| Background refresh (`BGAppRefreshTask`: refresh watched contests and packs) | Refresh on open / focus, with the service worker revalidating the same versioned URLs |

**The web accepts the browser chrome** (URL bar, Safari's bottom bar, navigation pop-ups). These layout rules make it safe. They are **shared design tokens**, and native maps them to its safe-area insets (`safeAreaInsets` / SwiftUI `safeAreaPadding`):

- Insets come from `env(safe-area-inset-top|right|bottom|left)` (with `viewport-fit=cover`), exposed as tokens `space.safe.top|right|bottom|left`. Native fills the same tokens from its safe-area insets.
- Heights use `100dvh` (or `100svh` where a stable minimum is needed), **never `100vh`**. The token is `size.viewport.height`, and native uses the container height.
- Floating Liquid Glass controls (the map buttons, layers button, time row) stay **inside the safe areas**. Their offsets are `space.safe.*` plus `space.float.gap`.
- Bottom controls must not collide with Safari's bottom URL bar. Anchor them above `space.safe.bottom` plus `space.chrome.bottomReserve`, which is a token: non-zero on the web for iOS Safari, 0 on native. Keep tap targets out of the bar's collapse zone.
- Nothing critical depends on fullscreen. Every control and every piece of data is reachable with the browser chrome showing. Fullscreen / standalone (PWA) is only an enhancement.

## Layout modes: phone, tablet, desktop

The user, relayed via Trailblazer, at **11:53 AM EDT**:

> "the ios app will run natively on mac os as ios sized window just like iphone mirroring. but the desktop /tablet sized will be an option two. we will allow users to select from"

- **Three layout modes**, `phone`, `tablet` and `desktop`, are design tokens with breakpoints: `layout.breakpoint.tablet` and `layout.breakpoint.desktop`, by container width (values set in the token file and shared by CSS and Swift).
- **User-selectable mode:** `auto` (default) picks the mode from the width. A manual override (`phone` / `tablet` / `desktop`) is **persisted per device**: `localStorage` on the web, `UserDefaults` on native. It is not synced to the account.
- **macOS:** the iOS app runs natively on the Mac in an **iPhone-sized window by default** (like iPhone Mirroring), with `tablet` and `desktop` as choices in the same selector.
- **Web** gets the same selector, with the same labels and the same `auto` default.
- **Purely presentational:** the layout mode changes only arrangement and density. All three modes use the same `/api/v1` and the same shared core: the same data, the same rules, the same results. No feature is missing in any mode, and the PR checklist item above applies to each mode.
