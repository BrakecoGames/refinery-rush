# Refinery Rush

3D refinery tycoon game (three.js) for Poki and CrazyGames: build a refinery from 1940 to 2025.

- `index.html` – Poki build (three.js inlined, Poki SDK). **This is the source file: edit this one.** Upload this to Poki.
- `refinery-rush-crazygames.html` – CrazyGames build (CrazyGames SDK v3: gameplay start/stop, loading events,
  midgame + rewarded ads, happytime, mute setting, saves in `SDK.data`). Upload this to CrazyGames.
- `refinery-rush-en.html` – development version (three.js from CDN, Google Fonts, no platform SDK).
- `tools/build_variants.py` – regenerates the CrazyGames and development builds from `index.html`
  (`python3 tools/build_variants.py`). The game code detects the platform at runtime, so only the script tags differ.
- `backups/` – restore points.
- `GAME_IMPROVEMENT_LOG.md` – changelog of the improvement loop (tests, results, scores).
