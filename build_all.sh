#!/usr/bin/env bash
# Regenerate sources and test TTFs for every style (fontTools only).
set -euo pipefail
mk() { ISE_STYLE="$1" ISE_S="$2" ISE_SLANT="$3" python scripts/make_glyphs.py >/dev/null; ISE_STYLE="$1" python scripts/build_ttf.py | tail -1; }
mk Regular 100 0
mk Italic 100 12             # 12-degree slanted roman
mk Bold 150 0
mk "Bold Italic" 150 12
