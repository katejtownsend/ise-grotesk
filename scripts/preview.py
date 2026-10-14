"""Render a specimen SVG of the UFO (no font build needed), with spacing and kerning applied.
python scripts/preview.py [text] [logic]      '¦' (broken bar) starts a new line, so '|' can be previewed; add `logic` to show the ss01 plain forms.   Output: docs/specimen.svg (open in a browser)"""
import sys, os
from fontTools.ufoLib import UFOReader
from fontTools.ufoLib.glifLib import GlyphSet
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.pointPen import PointToSegmentPen
UFO = os.environ.get("ISE_UFO", "sources/IseGrotesk-Regular.ufo")
text = sys.argv[1] if len(sys.argv) > 1 else "ABCDEFGHIJKLM¦NOPQRSTUVWXYZ"
logic = len(sys.argv) > 2 and sys.argv[2] == "logic"      # python scripts/preview.py "text" logic  ->  render the ss01 plain forms
gs = GlyphSet(UFO + "/glyphs"); kern = UFOReader(UFO).readKerning()
class G: pass
cmap = {}
for n in gs.keys():
    g = G(); g.unicodes = []; gs.readGlyph(n, g); [cmap.__setitem__(chr(u), n) for u in g.unicodes]
rows, y = [], 900
for line in text.split("¦"):
    x, paths, prev = 40, [], None
    for ch in line:
        n = cmap.get(ch)
        if n is None: continue
        if logic and n + ".ss01" in gs: n = n + ".ss01"
        if prev: x += kern.get((prev, n), 0)
        g = G(); sp = SVGPathPen(gs); gs.readGlyph(n, g, PointToSegmentPen(sp))
        paths.append(f'<path transform="translate({x},{y}) scale(1,-1)" d="{sp.getCommands()}"/>'); x += g.width; prev = n
    rows.append((x, paths)); y += 1100
W = max(r[0] for r in rows) + 40
open("docs/specimen.svg", "w").write(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {y-150}"><rect width="100%" height="100%" fill="#fff"/>' + "".join("".join(r[1]) for r in rows) + "</svg>")
print("wrote docs/specimen.svg")
