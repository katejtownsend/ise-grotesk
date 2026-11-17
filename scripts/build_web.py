"""Build the web files: unhinted WOFF2 (plus a ready-to-use CSS file) from the fontmake output in release/build.

    python3 scripts/build_web.py                       # writes release/web/*.woff2 and release/web/ise-grotesk.css
    python3 scripts/build_web.py --out /tmp/web --flavor woff   # test run without the brotli library

What makes these "web" files, compared with the desktop TTFs in release/ttf:
  * unhinted (no fpgm/prep/cvt or glyph instructions): about 40% smaller, and fine for a display face
  * post table format 3 (no glyph names): a little smaller
  * STAT table, fsType 0 and vendor ID (same as the desktop fonts), no Mac name records
  * gasp table set to smooth (grayscale) rendering at every size
The desktop fonts are not touched.
"""
import argparse, glob, os, shutil, sys
from fontTools.ttLib import TTFont
from fontTools.otlLib.builder import buildStatTable
sys.path.insert(0, os.path.dirname(__file__))

ap = argparse.ArgumentParser()
ap.add_argument("--src", default="release/build", help="folder with the unhinted fontmake TTFs")
ap.add_argument("--out", default="release/web", help="output folder")
ap.add_argument("--flavor", default="woff2", choices=["woff2", "woff", "ttf"])
args = ap.parse_args()

def axes_for(name):
    bold, italic = "Bold" in name, "Italic" in name
    wght = dict(value=700, name="Bold") if bold else dict(value=400, name="Regular", flags=0x2, linkedValue=700)
    ital = dict(value=1, name="Italic") if italic else dict(value=0, name="Upright", flags=0x2, linkedValue=1)
    return [dict(tag="wght", name="Weight", ordering=0, values=[wght]), dict(tag="ital", name="Italic", ordering=1, values=[ital])]

files = sorted(glob.glob(os.path.join(args.src, "IseGrotesk-*.ttf")))
if not files:
    sys.exit(f"No fonts found in {args.src}. Run ./build.sh first.")
os.makedirs(args.out, exist_ok=True)
ext = {"woff2": ".woff2", "woff": ".woff", "ttf": ".ttf"}[args.flavor]
report = []
for path in files:
    name = os.path.basename(path)
    f = TTFont(path)
    # remove any hinting that might be present
    for t in ("fpgm", "prep", "cvt ", "hdmx", "VDMX", "LTSH", "DSIG"):
        if t in f: del f[t]
    for g in f["glyf"].glyphs.values():
        if hasattr(g, "program"):
            from fontTools.ttLib.tables import ttProgram
            g.program = ttProgram.Program(); g.program.fromBytecode(b"")
    f["head"].flags &= ~0x8                                  # integer-ppem flag is for hinted fonts only
    if "gasp" not in f:                                      # fontmake leaves it out of unhinted fonts: add it
        from fontTools.ttLib import newTable
        f["gasp"] = newTable("gasp"); f["gasp"].version = 1
    f["gasp"].gaspRange = {0xFFFF: 0x000F}                   # grayscale smoothing at every size
    # STAT, name table, OS/2 (same rules as the desktop build)
    if "STAT" in f: del f["STAT"]
    buildStatTable(f, axes_for(name), elidedFallbackName=2)
    f["name"].names = [n for n in f["name"].names if n.platformID != 1]
    os2 = f["OS/2"]; os2.fsType = 0
    if os2.achVendID.strip() in ("", "NONE"): os2.achVendID = "KTWN"
    for n in f["name"].names:
        if n.nameID == 3 and ";NONE;" in str(n): n.string = str(n).replace(";NONE;", ";KTWN;")
    # smaller post table: no glyph names
    f["post"].formatType = 3.0
    f["post"].extraNames = []; f["post"].mapping = {}
    if args.flavor != "ttf": f.flavor = args.flavor
    out = os.path.join(args.out, name.replace(".ttf", ext))
    f.save(out)
    report.append((os.path.basename(out), os.path.getsize(path), os.path.getsize(out)))

# CSS: @font-face for the four styles, plus a size-matched fallback so the page does not jump when the font loads
FALLBACK = '''/* Size-matched fallback: Ise Grotesk is about 15% wider than Arial. These values keep the layout steady while the font loads.
   (size-adjust = Ise average width / Arial average width; overrides = Ise metric / (1000 x size-adjust).) Check with a layout-shift test. */
'''
faces = []
fall = []
for style, weight, italic in (("Regular", 400, False), ("Italic", 400, True), ("Bold", 700, False), ("BoldItalic", 700, True)):
    st = "italic" if italic else "normal"
    faces.append(f'''@font-face {{
  font-family: "Ise Grotesk";
  src: url("IseGrotesk-{style}{ext}") format("{'woff2' if args.flavor == 'woff2' else args.flavor}");
  font-weight: {weight};
  font-style: {st};
  font-display: swap;
}}''')
    local = {"Regular": 'local("Arial")', "Italic": 'local("Arial Italic"), local("Arial-ItalicMT")',
             "Bold": 'local("Arial Bold"), local("Arial-BoldMT")', "BoldItalic": 'local("Arial Bold Italic"), local("Arial-BoldItalicMT")'}[style]
    fall.append(f'''@font-face {{
  font-family: "Ise Fallback";
  src: {local};
  font-weight: {weight};
  font-style: {st};
  size-adjust: 115%;
  ascent-override: 87%;
  descent-override: 26%;
  line-gap-override: 0%;
}}''')
css = ("/* Ise Grotesk web fonts (unhinted). Licence: SIL OFL 1.1, Reserved Font Name 'Ise Grotesk'. https://github.com/katejtownsend/ise-grotesk */\n\n"
       + "\n\n".join(faces) + "\n\n" + FALLBACK + "\n\n".join(fall) + '''

/* Use it */
:root { font-family: "Ise Grotesk", "Ise Fallback", system-ui, sans-serif; }
body { font-synthesis: none; }                       /* never invent a fake bold or italic */
h1, h2, .display { line-height: 1.1; }               /* display sizes: full whimsy by default */
body, button, input, .small {                        /* text and UI: plain forms plus clear look-alike letters */
  font-feature-settings: "ss01", "ss02";
  letter-spacing: 0.01em;
}
''')
with open(os.path.join(args.out, "ise-grotesk.css"), "w") as fh: fh.write(css)
print(f"{'file':32s} {'unhinted TTF':>14s} {'output':>10s}")
for n, a, b in report: print(f"{n:32s} {a:14d} {b:10d}")
print("wrote", os.path.join(args.out, "ise-grotesk.css"))
