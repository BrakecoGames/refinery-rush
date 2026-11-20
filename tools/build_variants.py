#!/usr/bin/env python3
"""Generate the other builds from index.html (the Poki build, the single source of truth).

  refinery-rush-crazygames.html  CrazyGames build: same game, CrazyGames SDK v3 instead of the Poki SDK.
  refinery-rush-en.html          development build: three.js from the CDN, Google Fonts, no platform SDK.

The game code picks the platform at runtime (window.CrazyGames.SDK or window.PokiSDK),
so only the <script> tags differ between the builds.  Run:  python3 tools/build_variants.py
"""
import pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
POKI_TAG = '<script src="https://game-cdn.poki.com/scripts/v2/poki-sdk.js"></script>'
CG_TAG = '<script src="https://sdk.crazygames.com/crazygames-sdk-v3.js"></script>'
THREE_CDN = '<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>'
FONTS = ('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Big+Shoulders+Display:wght@600;800;900'
         '&family=Barlow+Semi+Condensed:wght@400;500;600;700&family=Old+Standard+TT:ital,wght@0,400;0,700;1,400&display=swap">')

def main():
    src = (ROOT / 'index.html').read_text(encoding='utf-8')
    if src.count(POKI_TAG) != 1:
        sys.exit('index.html: Poki SDK script tag not found exactly once')
    # CrazyGames build
    (ROOT / 'refinery-rush-crazygames.html').write_text(src.replace(POKI_TAG, CG_TAG), encoding='utf-8')
    # development build: inlined three.js -> CDN, no platform SDK, web fonts
    three = re.search(r'<script>/\* three\.js r128 \(MIT\) \*/\n.*?</script>\n', src, re.S)
    if not three:
        sys.exit('index.html: inlined three.js block not found')
    dev = src.replace(three.group(0), THREE_CDN + '\n').replace(POKI_TAG + '\n', '')
    has_fonts = '@font-face' in dev
    if not has_fonts:
        dev = dev.replace('<title>Refinery Rush</title>\n', '<title>Refinery Rush</title>\n' + FONTS + '\n', 1)
    dev = dev.replace('<title>Refinery Rush</title>\n', '<title>Refinery Rush</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n', 1)
    (ROOT / 'refinery-rush-en.html').write_text(dev, encoding='utf-8')
    for f in ('index.html', 'refinery-rush-crazygames.html', 'refinery-rush-en.html'):
        print(f'{f}: {(ROOT / f).stat().st_size:,} bytes')

if __name__ == '__main__':
    main()
