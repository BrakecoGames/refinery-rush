# Game Improvement Log — Refinery Rush

Autonomous improvement loop, started 2026-11-20.
Restore point before the loop: git tag `restore-before-loop-2026-11-20` (commit 10f36d3).

## Test setup

- Local static server + Playwright (pre-installed Chromium, SwiftShader software WebGL).
- Test builds are made from `index.html` with a small debug hook (`window.__rr`) injected
  before the closing IIFE — the hook is **only** in the scratch test copy, never in the shipped files.
- Bots: `play.js` (clicks like a player: build card → tap the arrow spot, speed 3×, auto-research,
  save → reload), `sim.js` (fast-forward economy with rendering stubbed), `perf*.js`
  (draw calls / meshes / frame time per category), `shot.js` (deterministic before/after screenshot + pixel diff).
- Limitation: SwiftShader is a CPU rasteriser, so absolute FPS is **not** representative of real
  hardware. Draw calls, mesh counts and JS time per frame are measured exactly; real-device FPS is an estimate.
- Not testable here: real Poki/CrazyGames SDK (hosts blocked by the sandbox network), real touch
  hardware, audio output.

## Phase 1 — analysis summary

Single-file three.js r128 game (~3,400 dense lines). `index.html` = Poki build (three.js inlined,
Poki SDK), `refinery-rush-en.html` = dev build (three.js from CDN). Both are kept in sync by hand.
Mature game: 5 maps, 30+ unit types, research tree, contracts, meta progression, historical events
1940–2026, per-map save slots (save v7), onboarding arrows.

Top 10 improvement points (priority = player impact × retention ÷ risk/time):

1. **Draw calls**: 3,684 calls in a mid-size refinery (31 units), ~1,000 on an empty map. Far too many for mobile. (high impact, medium risk)
2. **CrazyGames SDK**: the game only talks to the Poki SDK; the target platform is CrazyGames. (high impact for publishing)
3. **Mobile HUD clutter**: toasts, onboarding tip and the unit panel overlap at the bottom of a phone screen. (high UX impact)
4. **Fonts not shipped in the Poki build**: the display/body fonts fall back to Impact/Arial Narrow/system fonts, so the look differs per device. (visual identity)
5. Environment decor (town, terminal, trees, jetty) is ~1,800 individual meshes.
6. Delivery vehicles at truck bays are ~50 meshes each; pipe connections per unit ~17 meshes.
7. First minute: income is slightly negative until pump + truck bay are built; a lot of waiting on the first build crew.
8. Tanker state is not saved (an unloading tanker resets on reload) — minor.
9. Long-session stability across all five maps needs an automated check.
10. Dev build and Poki build drift apart (SDK wrapper, key handling) — maintenance risk.

## Baseline scores (before iteration 1)

T = based on a real automated test, E = expert estimate.

| Area | Score | Basis |
|---|---|---|
| First impression | 7/10 | T (screenshots) |
| Gameplay | 8/10 | E + T (bot play) |
| Visual quality | 8/10 | T (screenshots) |
| Usability | 6/10 | T (mobile overlap seen) |
| Progression | 8/10 | E + T (sim) |
| Retention potential | 8/10 | E |
| Performance | 5/10 | T (draw calls measured) |
| Stability | 8/10 | T (no JS errors in bot runs) |
| Mobile experience | 5/10 | T (390×844 screenshots) |
| CrazyGames readiness | 4/10 | E (no CrazyGames SDK) |

---

## Iteration 1 — vertex-colour batching of unit models, pipes and roads

- **Problem**: every unit model was merged per *material*, but every colour is its own material,
  so one unit still cost 12–39 draw calls (×2 with the shadow pass). 3,684 draw calls in a
  31-unit refinery.
- **Change**: `mergeModel` now folds all plain opaque Lambert/Phong materials (no texture, no
  transparency, no emissive) into one shared vertex-coloured material per shading type, so they
  share one mesh. Textured, transparent and emissive materials keep their own mesh as before.
  `mergeLocal` (pipe and road cells) uses the same path and keeps per-mesh shadow flags and render order.
- **Files**: `index.html`, `refinery-rush-en.html`.
- **Tests**: `perf2.js` same 31-unit refinery before/after; `shot.js` deterministic
  before/after screenshot with pixel diff; `play.js` (place via arrow, run, save/reload).
- **Results**: draw calls 3,684 → 1,924 (−48 %). Unit meshes 1,827 → 1,170. Pixel diff: 0.02 % of
  pixels differ by >20/255 (only flames/particles) — visually identical. No JS errors; save/load OK.
- **Remaining**: decor (~1,400 meshes), vehicles and pipe connections are still separate meshes.

| Area | Score | Basis |
|---|---|---|
| First impression | 7/10 | T |
| Gameplay | 8/10 | E |
| Visual quality | 8/10 | T |
| Usability | 6/10 | T |
| Progression | 8/10 | E |
| Retention potential | 8/10 | E |
| Performance | 6/10 | T (draw calls), E (real FPS) |
| Stability | 8/10 | T |
| Mobile experience | 5.5/10 | E (fewer draw calls helps phones most) |
| CrazyGames readiness | 4/10 | E |

## Iteration 2 — instanced trees and baked static decor

- **Problem**: an empty level already cost ~1,000 draw calls: ~470 tree meshes (one group of
  2 meshes per tree) and ~1,800 decor meshes (terminal, compound, car parks, entrance, jungle,
  polar decor) that are drawn one by one.
- **Change**:
  - Trees are now 3 `InstancedMesh`es (trunks + two green tones). Felling a tree sets its
    instance to a zero matrix (same technique the jungle trees already used). The polar
    snow tint still works because the cones keep the shared tree materials.
  - New `bakeDecor()` at the end of `applyLoc()`: every decor group is merged into a few
    vertex-coloured meshes in its own local space; loose static meshes are gathered into one
    extra group. Everything an animation refers to (LFX incl. fauna, level crossings, under/overpass,
    rocks, lots, any object with `userData` links) and hidden parts are kept as separate objects.
  - Merged decor geometry is disposed when the level is switched (no GPU memory growth).
  - Fix found while testing: re-merging a mesh that already had vertex colours crashed in the
    desert level → existing colour attributes are now copied.
- **Files**: `index.html`, `refinery-rush-en.html`.
- **Tests**:
  - `perf2.js` with seeded `Math.random`, 31-unit refinery: before vs after.
  - `mmcheck.js`: records every mesh the bake removes, then plays 200 s of game time on all
    5 levels (incl. storm surge) and checks none of them is moved, hidden/shown or recoloured
    afterwards (would mean a broken animation).
  - `maps.js`: before/after screenshot of all 5 levels + pixel diff.
  - `treecheck.js`: building on tree cells hides exactly those trees.
  - `play.js` regression (arrow placement, run, save/reload).
- **Results**:
  - Draw calls, 31-unit refinery: 4,078 (original) → 2,334 (−43 % vs. original, deterministic run).
  - Empty level: 999 → 525 draw calls.
  - Animated-mesh check: 838 / 936 / 460 / 645 / 423 meshes baked per level, **0** animated afterwards.
  - Screenshot diff: Harbor City 0.06 %, other levels 0.4–1.7 % — the differences are oil patches
    and particles placed with timing-dependent randomness, not rendering changes.
  - No JS errors on any level.
- **Remaining**: pipe connections per unit (~17 meshes) and delivery trucks (~50 meshes each).

| Area | Score | Basis |
|---|---|---|
| First impression | 7/10 | T |
| Gameplay | 8/10 | E |
| Visual quality | 8/10 | T (unchanged look) |
| Usability | 6/10 | T |
| Progression | 8/10 | E |
| Retention potential | 8/10 | E |
| Performance | 7/10 | T (draw calls), E (real FPS) |
| Stability | 8.5/10 | T (desert crash found and fixed before release) |
| Mobile experience | 6/10 | E |
| CrazyGames readiness | 4/10 | E |

## Iteration 3 — CrazyGames SDK integration, one source for all builds

- **Problem**: the target platform is CrazyGames, but the game only knew the Poki SDK. The dev build
  had drifted from the Poki build (older SDK wrapper, no ad between menus, no key/scroll guards).
- **Change**:
  - Platform layer detects `window.CrazyGames.SDK` or `window.PokiSDK` at runtime.
    CrazyGames: `init` (max 3 s wait, then the game starts anyway), `loadingStart/Stop`,
    `gameplayStart/Stop` (driven by the existing pause logic), `happytime` on completed contracts,
    `requestAd('midgame')` at the existing natural breaks (menu close, level switch, restart),
    `requestAd('rewarded')` with the reward **only** on `adFinished`, platform mute setting respected.
  - `STORE` wrapper: on CrazyGames saves/meta progress go to `SDK.data` (synced to the player's
    account) and are mirrored to localStorage; reads fall back to localStorage, so existing
    progress is never lost. Save keys and save format (v7) unchanged.
  - Poki behaviour unchanged (same calls, same order).
  - `tools/build_variants.py` generates `refinery-rush-crazygames.html` (SDK tag swapped) and the
    dev build from `index.html`, so the three builds can no longer drift apart.
- **Files**: `index.html`, `refinery-rush-en.html` (regenerated), `refinery-rush-crazygames.html` (new),
  `tools/build_variants.py` (new), `README.md`.
- **Tests** (real SDK hosts are blocked in the sandbox, so mock SDKs with the documented API were used):
  - `cgtest.js` (CrazyGames mock): boot order `init → loadingStart → loadingStop → gameplayStart`;
    2× profit button → `gameplayStop, ad:rewarded, gameplayStart` and boost granted; failing ad →
    no boost + "No ad available" toast; menu → `gameplayStop`, Keep playing → `ad:midgame, gameplayStart`;
    save lands in `SDK.data`; after wiping localStorage and reloading the save (money, units) is restored.
  - `pokitest.js` (Poki mock): `init → loaded → gpStart`, rewarded and commercial break unchanged.
  - `devtest.js`: generated dev build starts and plays (CDN three.js served locally).
  - `play.js` regression without any SDK.
- **Results**: all checks pass, no JS errors.
- **Not tested**: the real CrazyGames SDK in the CrazyGames QA tool (needs their site); run the
  build through the CrazyGames "SDK implementation checklist" before submitting.

| Area | Score | Basis |
|---|---|---|
| First impression | 7/10 | T |
| Gameplay | 8/10 | E |
| Visual quality | 8/10 | T |
| Usability | 6/10 | T |
| Progression | 8/10 | E |
| Retention potential | 8.5/10 | E (cloud saves on CrazyGames) |
| Performance | 7/10 | T/E |
| Stability | 8.5/10 | T |
| Mobile experience | 6/10 | E |
| CrazyGames readiness | 7/10 | T (mock SDK), E (real QA tool pending) |

## Iteration 4 — mobile and tablet HUD: no more overlapping elements

- **Problem** (found with an automatic overlap detector on real device profiles):
  - Phone portrait: the top bar wraps to 3 rows once the income text gets longer, and the
    research bar then disappears under the fixed "Contracts / Statistics" buttons.
  - The onboarding tip and its ✕ button covered the **"Contract completed → Double"** bar — the
    very first reward moment — and a mis-tap on ✕ skipped the tutorial. The reward bar was also
    dimmed by the onboarding overlay.
  - Toasts and the reward bar ran under the camera buttons on the right.
  - iPad portrait (768 px) used the desktop top bar, which overlapped itself (year clipped,
    research text under the money, menu over "2× profit").
  - Phone landscape: the camera buttons collided with "Statistics".
- **Change**:
  - `hudLayout()` writes the real bottom edge of the top bar into `--topB` (on resize and in the
    UI tick); side buttons, side panel and pause banner are positioned from it.
  - Onboarding tip (and ✕) moves above the reward bar and any message bar (`onbAvoid`).
  - Reward bar sits above the onboarding dimmer (`z-index:31`).
  - Portrait phones: toasts and the reward bar are left-aligned and keep clear of the camera column.
  - Compact HUD breakpoint 760 → 900 px (tablets in portrait); slightly smaller camera buttons in landscape.
- **Files**: `index.html` (+ regenerated `refinery-rush-crazygames.html`, `refinery-rush-en.html`).
- **Tests**: `mobov.js` — touch play (tap card, tap spot twice, select unit, unit running) on
  iPhone 13, Pixel 5, iPad Mini, iPhone 13 landscape and Desktop Chrome, reporting every pair of
  overlapping HUD elements; screenshots checked.
- **Results**: iPhone 13, Pixel 5, iPad Mini, iPhone 13 landscape and Desktop Chrome: **0 overlaps**
  (before: 1–6 per device). A first desktop run still showed the tip over an info message; fixed in
  the follow-up commit by letting the tip avoid every message, then re-tested on all profiles.
- **Remaining**: on small screens the onboarding arrow can still sit over the reward bar's ✕
  (the arrow does not block taps).

| Area | Score | Basis |
|---|---|---|
| First impression | 7.5/10 | T (first reward is visible and tappable on phones) |
| Gameplay | 8/10 | E |
| Visual quality | 8/10 | T |
| Usability | 7.5/10 | T (overlap detector) |
| Progression | 8/10 | E |
| Retention potential | 8.5/10 | E |
| Performance | 7/10 | T/E |
| Stability | 8.5/10 | T |
| Mobile experience | 7.5/10 | T (device profiles) |
| CrazyGames readiness | 7.5/10 | T/E |

## Iteration 5 — the game's own fonts are shipped in the build

- **Problem**: the CSS is designed around Big Shoulders Display (HUD/headlines), Barlow Semi
  Condensed (body) and Old Standard TT (newspaper modals), but only the dev build loaded them
  (Google Fonts). The Poki/CrazyGames builds fell back to Arial Narrow / Impact / system fonts,
  so the look differed per device and wide fallback fonts truncated labels ("Water p…") and
  pushed the phone top bar onto an extra row.
- **Change**: the latin subsets of the weights actually used (3 + 3 + 3 woff2 files, 185 KB) are
  embedded as `@font-face` data URIs with `font-display:swap` (no extra request, no external host,
  text is never invisible while loading). Sources: `@fontsource` npm packages. All three families
  are SIL Open Font License 1.1; notice in the CSS and full licence texts in `licenses/OFL-fonts.txt`.
  The dev build no longer needs Google Fonts either.
- **Files**: `index.html`, generated builds, `licenses/OFL-fonts.txt` (new).
- **Tests**: `fonts.js` (fonts resolve, before/after screenshots of HUD and menu), `mobov2.js` on
  5 device profiles (0 overlaps), `play.js` regression.
- **Results**: consistent industrial/newspaper identity on every device; labels fit
  ("Water pump" no longer cut off on phones). Build size 1.06 MB → 1.31 MB (one file, no extra requests).
- **Trade-off**: +250 KB download (base64). Acceptable for a 1.3 MB single-file game.

| Area | Score | Basis |
|---|---|---|
| First impression | 8/10 | T (screenshots) |
| Gameplay | 8/10 | E |
| Visual quality | 8.5/10 | T |
| Usability | 7.5/10 | T |
| Progression | 8/10 | E |
| Retention potential | 8.5/10 | E |
| Performance | 7/10 | T/E |
| Stability | 8.5/10 | T |
| Mobile experience | 7.5/10 | T |
| CrazyGames readiness | 7.5/10 | T/E |

## Iteration 6 — long sessions: end-of-game loop, double ad, advisor when in the red

- **Analysis**: `long.js` lets a bot play every level from 1940 to the end (2026) at 3× speed with
  rendering stubbed (~26,000 frames), clicking modals, choosing research and tapping incident alerts.
- **Problems found**:
  1. After the final newspaper, *Play again* → picking the **same** location only closed the
     dialog (that path means "keep playing" during a game); the ended game stayed and the end
     screen came straight back — an endless loop for anyone replaying their level.
  2. That flow requested **two midgame ads back to back** (one on *Play again*, one on the location pick).
  3. No safety net when a player's money goes negative: nothing tells them why (the desert bot
     sank to −$8.6 B without a single hint).
- **Change**:
  1. Picking the current location after the game has ended starts a new game.
  2. *Play again* no longer requests an ad; the single ad plays when the location is picked.
  3. `advisor()`: while the money is negative, every ~25 s a short bar at the bottom gives the most
     likely cause with a concrete fix and rings the matching build card: no crude oil (pumpjacks /
     oil tanks), cooling shortage (water pump / air cooler), product offtake over capacity (truck
     bay / rail), fines, or general cost > sales advice. No popup, no pause.
- **Files**: `index.html` (+ generated builds).
- **Tests**: `long.js` on all 5 levels to the end and through *Play again*; `advtest.js` forces each
  diagnosis (desert without crude, Harbor City without cooling, Harbor City with costs > sales).
- **Results**: all 5 levels run 1940 → 2026 with **0 JS errors**; *Play again* starts a fresh game
  (year back to 1940); each diagnosis appears with the right card.

| Area | Score | Basis |
|---|---|---|
| First impression | 8/10 | T |
| Gameplay | 8/10 | E + T (bot) |
| Visual quality | 8.5/10 | T |
| Usability | 8/10 | T |
| Progression | 8/10 | T (full-length bot runs) |
| Retention potential | 8.5/10 | E (replay loop fixed) |
| Performance | 7/10 | T/E |
| Stability | 9/10 | T (5 full sessions, 0 errors) |
| Mobile experience | 7.5/10 | T |
| CrazyGames readiness | 8/10 | T/E (no double ads) |

## Iteration 7 — vehicles and pipe connections batched

- **Problem**: each delivery truck was 51 meshes, each tank wagon 35, the locomotive 53, and the
  pipe connection of every unit ~17 — all separate draw calls (×2 with shadows).
- **Change**: trucks, locomotive and wagons are merged once when created (they only move as a whole;
  wheels are not animated separately); a unit's pipe connection is merged with `mergeLocal` when built.
- **Files**: `index.html` (+ generated builds).
- **Tests**: `perf2.js` (seeded 31-unit refinery), `vehcheck.js` (mesh/triangle count per vehicle,
  previous vs new build), `shot.js` screenshot diff vs previous commit, `long.js` (Delta Islands to
  2026), `play.js`.
- **Results**: draw calls 2,334 → **1,799** (original 4,078: −56 % overall). Truck 51 → 6 meshes,
  wagon 35 → 2, locomotive 53 → 3, identical triangle counts. Screenshot diff 0.1 % (particles).
  No errors.

| Area | Score | Basis |
|---|---|---|
| First impression | 8/10 | T |
| Gameplay | 8/10 | E + T |
| Visual quality | 8.5/10 | T |
| Usability | 8/10 | T |
| Progression | 8/10 | T |
| Retention potential | 8.5/10 | E |
| Performance | 7.5/10 | T (draw calls), E (real FPS) |
| Stability | 9/10 | T |
| Mobile experience | 7.5/10 | T/E |
| CrazyGames readiness | 8/10 | T/E |

## Iteration 8 — faster first success moment

- **Problem**: the first 30 seconds were mostly waiting: the free distillation column takes 16 s to
  build plus the pipe animation; the first "Running!" + first star came at ~19 s, and the starter
  chain (column → water pump → truck bay running) took ~54 s with one build crew.
- **Change**: `bStart()` — the first unit of a game builds in half the time, the next two 30 %
  faster. Applies to every level start (also returning players starting a new level); the build
  cards show the shorter times, so nothing is hidden. Later builds are unchanged.
- **Files**: `index.html` (+ generated builds).
- **Tests**: `first.js` (same scripted starter chain on previous vs new build, game time at 1×), `play.js`.
- **Results**: first "Running!" + first star 18.9 s → **10.9 s**; starter chain running 54.4 s → **34.9 s**.
  No errors, save/load fine.

| Area | Score | Basis |
|---|---|---|
| First impression | 8.5/10 | T (first reward ~11 s) |
| Gameplay | 8/10 | E + T |
| Visual quality | 8.5/10 | T |
| Usability | 8/10 | T |
| Progression | 8/10 | T |
| Retention potential | 8.5/10 | E |
| Performance | 7.5/10 | T/E |
| Stability | 9/10 | T |
| Mobile experience | 7.5/10 | T/E |
| CrazyGames readiness | 8/10 | T/E |

## Iteration 9 — load time check; fix own regression (reward bar over dialogs)

- **Analysis**: startup timing with the built-in markers (`?rrdebug=1`, 3 runs each, SwiftShader):
  original build interactive after 1.37–1.88 s, current build 1.74–2.09 s (first frame ~0.65–1.1 s).
  The embedded fonts add at most ~0.2 s, within run-to-run noise. No action needed.
- **Problem found** (regression from iteration 4): `#offer{z-index:31}` put the reward bar above
  **every** dialog, so it covered the research tree on phones.
- **Change**: the bar is only lifted (`.lift`) while the onboarding is on screen and no dialog is open.
- **Files**: `index.html` (+ generated builds).
- **Tests**: `load.js` (timing), `rsui.js` (iPhone 13: build lab, open research tree, screenshot +
  pixel check under the former bar position), `mobov2.js` (onboarding reward bar still bright, 0 overlaps).
- **Results**: research tree no longer covered; onboarding reward bar unchanged. The tree scrolls
  horizontally on phones (1182 px content in 358 px) — the clipped column already hints at it.

| Area | Score | Basis |
|---|---|---|
| First impression | 8.5/10 | T |
| Gameplay | 8/10 | E + T |
| Visual quality | 8.5/10 | T |
| Usability | 8/10 | T |
| Progression | 8/10 | T |
| Retention potential | 8.5/10 | E |
| Performance | 7.5/10 | T/E (load ~2 s) |
| Stability | 9/10 | T |
| Mobile experience | 7.5/10 | T |
| CrazyGames readiness | 8/10 | T/E |
