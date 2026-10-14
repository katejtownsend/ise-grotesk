"""Build fonts/IseGrotesk-Regular.ttf straight from the UFO using only fontTools (no fontmake needed).
python scripts/build_ttf.py
Limits vs fontmake: no overlap removal (overlaps are valid TrueType, but run fontmake --overlaps-backend pathops for release),
no hinting (run ttfautohint), no OTF/CFF output."""
import io, os, sys
from fontTools.ufoLib import UFOReader
from fontTools.ufoLib.glifLib import GlyphSet
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.pointPen import PointToSegmentPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.fontBuilder import FontBuilder
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.ttLib import TTFont

STYLE = os.environ.get("ISE_STYLE", "Regular")                 # Regular | Bold | Italic | Bold Italic
UFO = "sources/IseGrotesk-%s.ufo" % STYLE.replace(" ", ""); OUT = "fonts"
ITALIC = "Italic" in STYLE
FAMILY = "Ise Grotesk"
BOLD = "Bold" in STYLE
SUB = ("Bold Italic" if ITALIC else "Bold") if BOLD else ("Italic" if ITALIC else "Regular")
PS = FAMILY.replace(" ", "") + "-" + SUB.replace(" ", "")
rd = UFOReader(UFO); info = type("I", (), {})()
rd.readInfo(info)
gs = GlyphSet(UFO + "/glyphs"); kern = rd.readKerning()
fea = open(UFO + "/features.fea").read()

class G: pass
class _Glyph:
    def __init__(self, n): self.n = n
    def draw(self, pen): gs.readGlyph(self.n, G(), PointToSegmentPen(pen))
class _GS:
    def __getitem__(self, n): return _Glyph(n)
names, cmap, adv = [], {}, {}
for n in gs.keys():
    g = G(); g.unicodes = []; gs.readGlyph(n, g)
    names.append(n); adv[n] = g.width
    for u in g.unicodes: cmap[u] = n
order = [".notdef"] + sorted(names, key=lambda n: (n != "space", n))
adv[".notdef"] = 500

glyphs = {}
for n in order:
    pen = TTGlyphPen(None)
    if n == ".notdef":
        for pts, d in (([(80, 0), (80, 700), (420, 700), (420, 0)], 1), ([(160, 80), (340, 80), (340, 620), (160, 620)], -1)):
            p = pts if d == 1 else pts
            pen.moveTo(p[0]); [pen.lineTo(q) for q in p[1:]]; pen.closePath()
    else:
        rec = DecomposingRecordingPen(_GS()); _Glyph(n).draw(rec)
        rec.replay(Cu2QuPen(pen, 1.0, reverse_direction=True))   # UFO is ccw-outer; TrueType wants clockwise-outer
    glyphs[n] = pen.glyph()

fb = FontBuilder(info.unitsPerEm, isTTF=True)
fb.setupGlyphOrder(order)
fb.setupCharacterMap(cmap)
fb.setupGlyf(glyphs)
metrics = {}
for n in order:
    gl = glyphs[n]; gl.recalcBounds(fb.font["glyf"]) if hasattr(gl, "recalcBounds") else None
    metrics[n] = (adv[n], getattr(gl, "xMin", 0) if gl.numberOfContours else 0)
fb.setupHorizontalMetrics(metrics)
fb.setupHorizontalHeader(ascent=info.openTypeHheaAscender, descent=info.openTypeHheaDescender, lineGap=0)
ver = f"{info.versionMajor}.{info.versionMinor:03d}"
fb.setupNameTable({"familyName": FAMILY, "styleName": SUB, "uniqueFontIdentifier": f"{PS}-{ver}",
                   "fullName": f"{FAMILY} {SUB}", "psName": PS, "version": f"Version {ver}",
                   "copyright": "Copyright (c) Kate Townsend. SIL Open Font License 1.1.",
                   "description": "Ise Grotesk: a Bauhaus-inspired geometric sans, named for Ise Gropius. For the un-sung women in design."})
fb.setupOS2(version=4, sTypoAscender=info.openTypeOS2TypoAscender, sTypoDescender=info.openTypeOS2TypoDescender, sTypoLineGap=0,
            usWinAscent=info.openTypeOS2WinAscent, usWinDescent=info.openTypeOS2WinDescent,
            sxHeight=info.xHeight, sCapHeight=info.capHeight, fsType=0, achVendID="NONE", fsSelection=(0x01 if ITALIC else 0) | (0x20 if BOLD else 0) | (0x40 if SUB == "Regular" else 0) | 0x80, usWeightClass=700 if BOLD else 400)
fb.setupPost(keepGlyphNames=True, italicAngle=float(getattr(info, "italicAngle", 0) or 0))
fb.font["head"].macStyle = (2 if ITALIC else 0) | (1 if BOLD else 0)
fb.setupDummyDSIG = None

kfea = "\nfeature kern {\n" + "".join(f"    pos {a} {b} {v};\n" for (a, b), v in sorted(kern.items()) if a in adv and b in adv) + "} kern;\n"
addOpenTypeFeaturesFromString(fb.font, fea + kfea)

os.makedirs(OUT, exist_ok=True)
path = f"{OUT}/{PS}.ttf"; fb.save(path)
print("wrote", path, os.path.getsize(path), "bytes;", len(order), "glyphs;", len(cmap), "codepoints;", len(kern), "kern pairs")
