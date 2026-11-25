#!/bin/bash
# Re-creates the size-optimised fonts in proj/res/font from the originals in tools/fonts-src.
set -e; cd "$(dirname "$0")/.."
.venv/bin/pyftsubset tools/fonts-src/inter_medium.ttf --unicodes="U+0020-007E,U+00A0-017F,U+2010-2027,U+2030,U+2190-2193,U+2212" --layout-features='kern,tnum' --no-hinting --output-file=proj/res/font/inter_medium.ttf
.venv/bin/pyftsubset tools/fonts-src/outfit_light.ttf --unicodes="U+0030-003A,U+0020" --no-hinting --output-file=proj/res/font/outfit_light.ttf
