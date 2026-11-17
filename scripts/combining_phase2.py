"""Phase 2.3: combining marks (U+0300 ...), anchors for mark positioning, and the ccmp feature.

What this adds
  * zero-width combining glyphs (gravecomb, acutecomb, uni0302 ...) drawn from the same accents the font already uses
  * anchors in the UFO: every base letter gets "top" / "bottom" / "ogonek" points; every mark gets "_top" / "_bottom" / "_ogonek"
    (and top marks also a "top" anchor, so a second mark stacks above the first). ufo2ft turns these into the mark and mkmk
    features when fontmake compiles the font.
  * ccmp: a letter followed by a combining mark is swapped for the ready-made accented letter when we have one (a + acute
    becomes aacute), and i followed by a top mark becomes dotless i so the dot does not collide with the accent.
register(mg) is called from make_glyphs.py before main().
"""
import unicodedata
from fontTools.pens.transformPen import TransformPen

# unicode -> (spacing mark name in make_glyphs.MARKS, kind)
COMB = {0x300: "grave", 0x301: "acute", 0x302: "circumflex", 0x303: "tilde", 0x304: "macron", 0x306: "breve", 0x307: "dotaccent",
        0x308: "dieresis", 0x30A: "ring", 0x30B: "hungarumlaut", 0x30C: "caron", 0x326: "cedilla", 0x327: "cedilla", 0x328: "ogonek"}
NAME = {u: "uni%04X" % u for u in COMB}
TOP = [u for u, m in COMB.items() if m not in ("cedilla", "ogonek")]
LETTERS = [chr(c) for c in range(65, 91)] + [chr(c) for c in range(97, 123)] + ["dotlessi"]

mg = None
def register(module):
    global mg
    mg = module
    for u, mark in COMB.items():
        d = mg.MARKS[mark][1]
        def draw(p, d=d, mark=mark):
            q = TransformPen(p, (1, 0, 0, 1, -mg.MC, 0))
            if mg.LCS != 100 and mark not in mg.BELOW_MARKS: mg._with_mt(d, mg.LC_MT, q)     # same heavier accent as the precomposed letters
            else: d(q)
        mg.G[NAME[u]] = (u, 0, draw)                       # advance 0: sits on the previous letter
    mg.ANCHORS_HOOK = anchors
    mg.COMP_ANCHORS_HOOK = comp_anchors
    mg.EXTRA_FEA = mg.EXTRA_FEA + ccmp()

def _dy(letter):
    return mg.CAP_LIFT if letter.isupper() else mg.ASC_DY.get(letter, 0)

def anchors(name, l, ink, k):
    """Anchor list for glyph `name`. l = left sidebearing, ink = ink width, k = slant tangent (shears x with y)."""
    sh = lambda x, y: round(x + k * y)
    out = []
    base = name.split(".")[0]
    if base in LETTERS and name == base:
        letter = "i" if base == "dotlessi" else base
        ax = l + ink / 2; top = mg.XH + _dy(letter)
        out += [dict(name="top", x=sh(ax, top), y=top), dict(name="bottom", x=sh(ax, 0), y=0),
                dict(name="ogonek", x=sh(l + ink - 55, 0), y=0)]
    for u, mark in COMB.items():
        if NAME[u] == name:
            if mark in ("cedilla",): out += [dict(name="_bottom", x=0, y=0)]
            elif mark == "ogonek": out += [dict(name="_ogonek", x=0, y=0)]
            else: out += [dict(name="_top", x=sh(0, mg.XH), y=mg.XH), dict(name="top", x=sh(0, mg.CAP), y=mg.CAP)]
    return out

def comp_anchors(name, k):
    """Anchors for an accented letter, so a further mark can still be added: the 'top' point sits above the accent already there."""
    meta = mg.COMP_META.get(name)
    if not meta: return []
    sh = lambda x, y: round(x + k * y)
    letter, l, ink = meta["letter"], meta["l"], meta["ink"]
    ax = l + 50 if letter == "L" else l + ink / 2
    y = mg.XH + _dy(letter) + (mg.CAP_LIFT if meta["top"] else 0)
    out = [dict(name="top", x=sh(ax, y), y=y)]
    if not any(m in mg.BELOW for m in meta["marks"]): out.append(dict(name="bottom", x=sh(ax, 0), y=0))
    return out

def ccmp():
    rules = []
    for ch in mg.CHARS:
        d = unicodedata.normalize("NFD", ch)
        if len(d) == 2 and ord(d[1]) in COMB:
            rules.append(f"    sub {d[0]} {NAME[ord(d[1])]} by uni{ord(ch):04X};")
    marks = " ".join(NAME[u] for u in TOP)
    return ("\n@TOPMARKS = [" + marks + "];\n\nfeature ccmp {\n    lookup ccmp_compose {\n" + "\n".join(rules) +
            "\n    } ccmp_compose;\n    lookup ccmp_dotless {\n        sub i' @TOPMARKS by dotlessi;\n    } ccmp_dotless;\n} ccmp;\n")
