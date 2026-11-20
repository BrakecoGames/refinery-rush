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
