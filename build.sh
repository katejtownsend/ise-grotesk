#!/usr/bin/env bash
# Release build: regenerate the four UFO sources, then compile with fontmake (pathops overlap removal),
# hint with ttfautohint, and make WOFF2. Run on a machine with internet (see docs/RELEASE_PLAN.md).
# Needs: pip install fontmake skia-pathops ttfautohint-py brotli fonttools
set -euo pipefail
cd "$(dirname "$0")"
OUT=release; rm -rf "$OUT/build"; mkdir -p "$OUT/build/ttf" "$OUT/build/otf" "$OUT/ttf" "$OUT/otf" "$OUT/woff2"

# 1. Regenerate the UFO sources (fontTools only)
./build_all.sh >/dev/null

# 2. Compile the four styles (skip ARCHIVE-* sources)
for style in Regular Italic Bold BoldItalic; do
  ufo="sources/IseGrotesk-$style.ufo"
  fontmake -u "$ufo" -o ttf otf --output-dir "$OUT/build" --overlaps-backend pathops --verbose WARNING
done
# fontmake writes the files straight into release/build; sort them
mv "$OUT"/build/*.otf "$OUT/otf/" 2>/dev/null || true
mv "$OUT"/build/ttf/*.ttf "$OUT/build/" 2>/dev/null || true
mv "$OUT"/build/otf/*.otf "$OUT/otf/" 2>/dev/null || true

# 3. Hint the TTFs (ttfautohint-py has no command of its own, so we call it from Python)
for f in "$OUT"/build/*.ttf; do
  python3 scripts/hint.py "$f" "$OUT/ttf/$(basename "$f")"
done

# 3b. Add a STAT table and the integer-ppem flag (Font Bakery requirements)
python3 scripts/postprocess.py "$OUT"/ttf/*.ttf "$OUT"/otf/*.otf

# 4. WOFF2 for the web
for f in "$OUT"/ttf/*.ttf; do
  python3 -c "from fontTools.ttLib import TTFont; import sys; f=TTFont(sys.argv[1]); f.flavor='woff2'; f.save(sys.argv[2])" "$f" "$OUT/woff2/$(basename "${f%.ttf}").woff2"
done
echo "Done. Fonts are in $OUT/ttf, $OUT/otf, $OUT/woff2"
