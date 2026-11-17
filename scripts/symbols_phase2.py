"""Phase 2.1 draft symbols for Ise Grotesk (not yet part of the font).

    python3 scripts/symbols_phase2.py     # writes ../Phase2-symbols-preview.html (outside the repo, private)

Every glyph here is built from the same parts as the rest of the font: monoline strokes (mg.S), true circle arcs,
flat horizontal cuts. register() adds them to make_glyphs.G once approved.
"""
import math, os, sys
sys.path.insert(0, os.path.dirname(__file__))
mg = None          # set by register() (make_glyphs passes itself in) or by the preview at the bottom
ORIG = {}          # unwrapped draw functions of the existing glyphs (Bold wrapping would reset the stroke)
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.svgPathPen import SVGPathPen

N = {}      # name -> (unicode, ink width, draw)
def g(name, uni, W, draw): N[name] = (uni, W, draw)       # W = ink width; advance added at registration

def S(): return mg.S
def base(n): return ORIG[n] if n in ORIG else mg.G[n][2]
def base_adv(n): return mg.G[n][1]
def SB(): return mg.SB
def K(): return mg.LCS - 100          # extra stroke weight (0 Regular, 50 Bold); used for widths, which are fixed at registration
def LT(): return 70 + 0.35 * (S() - 100)   # a lighter stroke for reduced marks (digits, (c)/(r)/TM): 70 Regular, ~88 Bold

def disc(p, cx, cy, r): mg._arc(p, cx, cy, r, 0, 2 * math.pi, True); p.closePath()

# ---- punctuation ----
def ellipsis(p):
    r = mg.DR; pitch = 2 * r + 90
    for i in range(3): disc(p, SB() + r + i * pitch, r, r)
g("ellipsis", 0x2026, lambda: 6 * mg.DR + 180, ellipsis)
g("periodcentered", 0xB7, lambda: 2 * mg.DR, lambda p: disc(p, SB() + mg.DR, 300, mg.DR))
g("quotesinglbase", 0x201A, lambda: 2 * mg.DR + 4, lambda p: mg.comma_shape(p, SB() + mg.CP))
g("quotedblbase", 0x201E, lambda: 4 * mg.DR + 54, lambda p: [mg.comma_shape(p, SB() + mg.CP + i * (2 * mg.DR + 50)) for i in range(2)])
g("guilsinglleft", 0x2039, 120, lambda p: mg.polyline_stroke(p, [(SB() + 120, 450), (SB() + 10, 320), (SB() + 120, 190)], 0.7 * S()))
g("guilsinglright", 0x203A, 120, lambda p: mg.polyline_stroke(p, [(SB() + 10, 450), (SB() + 120, 320), (SB() + 10, 190)], 0.7 * S()))

def dagger(p, double=False):
    cx = SB() + 130; h = S() / 2
    rect = mg.rect
    rect(p, cx - h, -100, cx + h, 700)
    rect(p, SB(), 520 - h, SB() + 260, 520 + h)
    if double: rect(p, SB(), 160 - h, SB() + 260, 160 + h)
g("dagger", 0x2020, 260, dagger)
g("daggerdbl", 0x2021, 260, lambda p: dagger(p, True))

# ---- maths ----
def multiply(p):
    cx, cy, L = SB() + 160, 300, 160
    for s in (1, -1): mg.line_quad(p, cx - L, cy - s * L, cx + L, cy + s * L, S())
g("multiply", 0xD7, 320, multiply)

def divide(p):
    mg.rect(p, SB(), 300 - S() / 2, SB() + 400, 300 + S() / 2)
    disc(p, SB() + 200, 300 + 175, mg.DR); disc(p, SB() + 200, 300 - 175, mg.DR)
g("divide", 0xF7, 400, divide)

def plusminus(p):
    h = S() / 2; cx = SB() + 200
    mg.rect(p, SB(), 400 - h, SB() + 400, 400 + h); mg.rect(p, cx - h, 400 - 190, cx + h, 400 + 190)
    mg.rect(p, SB(), 100 - h, SB() + 400, 100 + h)
g("plusminus", 0xB1, 400, plusminus)
g("minus", 0x2212, 400, lambda p: mg.rect(p, SB(), 300 - S() / 2, SB() + 400, 300 + S() / 2))

def approx(p):
    R = 110 + 0.5 * K(); t = S() * 0.7; r = R - t; off = R + 20       # bigger waves; the two rows sit 40 units apart, centred on the maths axis
    for cy in (300 + off, 300 - off):
        mg.band(p, SB() + R, cy, R, r, 0, 180); mg.band(p, SB() + 2 * R + r, cy, R, r, 180, 360)
g("approxequal", 0x2248, lambda: 4 * (110 + 0.5 * K()) - 0.7 * mg.LCS, approx)

def notequal(p):
    h = S() / 2
    mg.rect(p, SB(), 200 - h, SB() + 400, 200 + h); mg.rect(p, SB(), 400 - h, SB() + 400, 400 + h)
    hw = mg.hw_for(lambda w: 130 - w, 560) * 0.85; mg.diag(p, 20, SB() + 200 - 65, 580, SB() + 200 + 65, hw)
g("notequal", 0x2260, 400, notequal)

def lessequal(p, flip=False):
    h = S() / 2
    pts = [(SB() + 400, 560), (SB() + 40, 400), (SB() + 400, 240)]
    if flip: pts = [(2 * SB() + 400 - x, y) for x, y in pts]
    mg.polyline_stroke(p, pts, S()); mg.rect(p, SB(), 100 - h, SB() + 400, 100 + h)
g("lessequal", 0x2264, 400, lessequal)
g("greaterequal", 0x2265, 400, lambda p: lessequal(p, True))

# ---- arrows: shaft + chevron head in the same stroke as the font's < > ----
def arrow_r(p):
    h = S() / 2; W = 560; y = 300
    mg.rect(p, SB(), y - h, SB() + W - 20, y + h)
    mg.polyline_stroke(p, [(SB() + W - 190, y + 170), (SB() + W - 20, y), (SB() + W - 190, y - 170)], S())
def arrow_l(p): arrow_r(TransformPen(p, (-1, 0, 0, 1, 2 * SB() + 560, 0)))
def arrow_u(p):
    h = S() / 2; x = SB() + 170; y0, y1 = -50, 650
    mg.rect(p, x - h, y0, x + h, y1 - 20)
    mg.polyline_stroke(p, [(x - 170, y1 - 190), (x, y1), (x + 170, y1 - 190)], S())
def arrow_d(p): arrow_u(TransformPen(p, (1, 0, 0, -1, 0, 600)))
g("arrowright", 0x2192, 560, arrow_r); g("arrowleft", 0x2190, 560, arrow_l)
g("arrowup", 0x2191, 340, arrow_u); g("arrowdown", 0x2193, 340, arrow_d)

# ---- reference marks ----
def pilcrow(p):
    s_ = S(); gap = 90; pitch = s_ + gap; cx = SB() + 210 + K() * 0.5
    mg.band(p, cx, 490, 210 + K() / 2, 110 - K() / 2, 90, 270)       # ring thickness = stroke
    mg.rect(p, cx, 700 - s_, cx + pitch + s_, 700); mg.rect(p, cx, 380 - s_, cx + pitch, 380)
    mg.rect(p, cx, 0, cx + s_, 700); mg.rect(p, cx + pitch, 0, cx + pitch + s_, 700)
g("paragraph", 0xB6, lambda: 500 + 2.5 * K(), pilcrow)

def section(p):
    # two stacked S-curves: the upper ends in a hook on the left, the lower in a hook on the right
    # four stacked half-rings (left, right, left, right) make a double S; short flat terminals at top and bottom
    t = S() * 0.85; R = (850 + 3 * t) / 8; cx = SB() + R + 40; pitch = 2 * R - t       # rings overlap by one stroke so the snake is joined
    for i, (a0, a1) in enumerate([(90, 270), (-90, 90), (90, 270), (-90, 90)]):
        mg.band(p, cx, 700 - R - i * pitch, R, R - t, a0, a1)
    mg.rect(p, cx, 700 - t, cx + 70, 700); mg.rect(p, cx - 70, -150, cx, -150 + t)
g("section", 0xA7, 320, section)

# ---- fractions and superscripts: the font's own digits at 60%, same weight as the lowercase ----
def small_digit(p, name, scale, x, y, stroke=None):
    draw = base(name)
    old = mg.S; mg.S = (LT() if stroke is None else stroke) / scale               # compensate so the reduced digit keeps the lighter stroke LT()
    try: draw(TransformPen(p, (scale, 0, 0, scale, x - mg.SB * scale, y)))
    finally: mg.S = old
SC = 0.58
SCS = 0.66                                   # superscripts are a little larger and heavier than fraction digits
def LTS(): return 84 + 0.4 * (S() - 100)
DWS = lambda name: (base_adv(name) - 2 * mg.SB) * SCS
DW = lambda name: (base_adv(name) - 2 * mg.SB) * SC
def sup(name):
    return lambda p: small_digit(p, name, SCS, SB(), 700 - 700 * SCS, LTS())  # top sits exactly on cap height
g("onesuperior", 0xB9, lambda: round(DWS("one")), sup("one"))
g("twosuperior", 0xB2, lambda: round(DWS("two")), sup("two"))
g("threesuperior", 0xB3, lambda: round(DWS("three")), sup("three"))

FW0 = 580           # was 520: the extra 60 opens the space between the slash and the denominator
FW = lambda: FW0 + 0.8 * K()
def fraction(top, bottom):
    def d(p):
        small_digit(p, top, SC, SB(), 700 - 700 * SC)                       # numerator: top at cap height
        small_digit(p, bottom, SC, SB() + FW() - DW(bottom), 0)             # denominator: on the baseline
        hw = mg.hw_for(lambda h: 230 - h, 700) * 0.6; c = FW() / 2 - 30; mg.diag(p, 0, SB() + c - 115, 700, SB() + c + 115, hw)
    return d
g("fraction", 0x2044, 230, lambda p: mg.diag(p, 0, SB() + 40, 700, SB() + 190, mg.hw_for(lambda h: 150 - h, 700) * 0.6))
g("onehalf", 0xBD, FW, fraction("one", "two"))
g("onequarter", 0xBC, FW, fraction("one", "four"))
g("threequarters", 0xBE, FW, fraction("three", "four"))

# ---- legal and trademark ----
def copyright_(p, letter):
    R = 350; cx = SB() + R; cy = 350; t = LT()
    mg.ring(p, cx, cy, R, R - t)
    if letter == "c":
        mg.band(p, cx, cy, 190, 190 - t, 40, 320)
    else:                                   # the font's own R at 55%, centred in the ring
        sc = 0.55; old = mg.S; mg.S = LT() / sc
        try: base("R")(TransformPen(p, (sc, 0, 0, sc, cx - (base_adv("R") / 2) * sc, cy - 350 * sc)))
        finally: mg.S = old
g("copyright", 0xA9, 700, lambda p: copyright_(p, "c"))
g("registered", 0xAE, 700, lambda p: copyright_(p, "r"))

def trademark(p):
    sc = 0.5
    old = mg.S; mg.S = LT() / sc
    try:
        base("T")(TransformPen(p, (sc, 0, 0, sc, -mg.SB * sc + SB(), 700 - 700 * sc)))
        base("M")(TransformPen(p, (sc, 0, 0, sc, -mg.SB * sc + SB() + (base_adv("T") - 2 * mg.SB) * sc + 25, 700 - 700 * sc)))
    finally: mg.S = old
g("trademark", 0x2122, 600, trademark)

# ---- more extras that go with the set ----
g("cent", 0xA2, lambda: 360 + 0.8 * K(), lambda p: (mg.band(p, SB() + 180 + 0.4 * K(), 300, 180 + 0.4 * K(), 180 + 0.4 * K() - S(), 40, 320), mg.rect(p, SB() + 160 + 0.4 * K(), 30, SB() + 160 + 0.4 * K() + 0.7 * S(), 570)))
g("brokenbar", 0xA6, lambda: mg.LCS, lambda p: (mg.rect(p, SB(), 330, SB() + S(), 750), mg.rect(p, SB(), -150, SB() + S(), 270)))
g("logicalnot", 0xAC, 400, lambda p: (mg.rect(p, SB(), 300 - S() / 2, SB() + 400, 300 + S() / 2), mg.rect(p, SB() + 400 - S(), 100, SB() + 400, 300)))


# ---- Phase 2.2: Icelandic and other letters ----
g("Eth", 0xD0, 700, lambda p: mg.Dstroke(p))                       # same drawing as Dcroat (Đ): the capital Eth is the same letter shape
def eth(p):
    # a d whose ascender curls over to the left (a quarter-circle hook), crossed by a short bar: reads as eth, not as d
    R2 = 105; x0 = SB() + 2 * mg.R_ - S(); x1 = x0 + S(); yc = 750 - R2
    mg.bowl(p); mg.stem(p, x0, 0, yc + 4)
    mg.band(p, x1 - R2, yc, R2, R2 - S(), 0, 90)
    mg.rect(p, x0 - 90, 548, x1 + 90, 548 + 0.7 * S())
g("eth", 0xF0, 500 + 90, eth)
def Thorn(p):
    cx = SB() + 210; top, bot = 540, 120
    mg.stem(p, SB()); mg.rect(p, SB() + S(), top - S(), cx, top); mg.rect(p, SB() + S(), bot, cx, bot + S())
    mg.band(p, cx, (top + bot) / 2, (top - bot) / 2, (top - bot) / 2 - S(), -90, 90)
g("Thorn", 0xDE, 420, Thorn)
g("thorn", 0xFE, 500, lambda p: (mg.stem(p, SB(), mg.DESC, mg.ASC), mg.bowl(p)))
g("mu", 0xB5, 440, lambda p: (mg.lc_u(p), mg.stem(p, SB(), mg.DESC, mg.XH)))
SPN = {"Eth": (50, 60), "eth": (60, 90), "Thorn": (90, 50), "thorn": (90, 60), "mu": (90, 90)}

# ---- spaces (advance widths; en/em follow the 1000-unit em) ----
SPACES = [("nbspace", 0xA0, 380), ("enspace", 0x2002, 500), ("emspace", 0x2003, 1000), ("threeperemspace", 0x2004, 333),
          ("fourperemspace", 0x2005, 250), ("sixperemspace", 0x2006, 167), ("figurespace", 0x2007, None), ("punctuationspace", 0x2008, 260),
          ("thinspace", 0x2009, 200), ("hairspace", 0x200A, 100), ("zerowidthspace", 0x200B, 0), ("narrownbspace", 0x202F, 200)]

def register(module):
    """Add the approved symbols and spaces to make_glyphs.G. Call before main() so Bold/Italic get them too."""
    global mg
    mg = module
    for n in ("one", "two", "three", "four", "R", "T", "M", "C"): ORIG[n] = mg.G[n][2]
    for name, (uni, W, draw) in N.items(): mg.G[name] = (uni, (W() if callable(W) else W) + 2 * mg.SB, draw)
    for name, uni, adv in SPACES:
        if adv is None: adv = mg.G["zero"][1]              # figure space = width of a digit
        mg.G[name] = (uni, adv, lambda p: None)
    mg.SP.update(SPN)
    # no soft hyphen (U+00AD): Font Bakery advises leaving it out; the shaping engine handles hyphenation
    MATH = ["multiply", "divide", "plusminus", "minus", "approxequal", "notequal", "lessequal", "greaterequal", "logicalnot"]
    for n in MATH:                                     # every maths sign gets the same advance (520) as + = < >, so they line up in a row
        sb = (520 - (mg.G[n][1] - 2 * mg.SB)) / 2
        mg.SP[n] = (sb, sb)
    mg.EXTRA_FEA = mg.EXTRA_FEA + case_and_tabular()
    return list(N) + [s[0] for s in SPACES]

# ---- Phase 2.4: tabular figures (tnum) and case-sensitive forms (case) ----
CASE_SHIFT = {"hyphen": 50, "endash": 50, "emdash": 50, "minus": 50, "plus": 50, "equal": 50, "multiply": 50, "divide": 50, "plusminus": 50,
              "less": 50, "greater": 50, "parenleft": 50, "parenright": 50, "bracketleft": 50, "bracketright": 50, "braceleft": 50,
              "braceright": 50, "bullet": 50, "periodcentered": 50, "asciitilde": 50, "guillemotleft": 30, "guillemotright": 30,
              "guilsinglleft": 30, "guilsinglright": 30}
DIGITS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "zero.ss02", "five.ss01"]

def case_and_tabular():
    """Add the .case and .tf glyph variants to make_glyphs.G and return the feature code for them."""
    fea = []
    for n, dy in CASE_SHIFT.items():
        if n not in mg.G: continue
        uni, adv, draw = mg.G[n]
        mg.G[n + ".case"] = (None, adv, (lambda d, dy: lambda p: d(TransformPen(p, (1, 0, 0, 1, 0, dy))))(draw, dy))
        fea.append(f"    sub {n} by {n}.case;")
    case = "feature case {\n" + "\n".join(fea) + "\n} case;\n"
    tw = max(mg.spacing(d)[2] for d in DIGITS if d in mg.G)               # tabular width = the widest digit's advance
    tf = []
    for d in DIGITS:
        if d not in mg.G: continue
        uni, adv, draw = mg.G[d]
        l, ink, _ = mg.spacing(d)
        mg.G[d + ".tf"] = (None, adv, draw)
        mg.SP[d + ".tf"] = ((tw - ink) / 2 - mg.PAD, (tw - ink) / 2 - mg.PAD)   # centre the figure in the tabular width
        tf.append(f"    sub {d} by {d}.tf;")
    return "\n" + case + "\nfeature tnum {\n" + "\n".join(tf) + "\n} tnum;\n"

def draw_svg(draw, adv, stroke=100):
    pen = SVGPathPen(None)
    old = mg.S; mg.S = stroke
    try: draw(TransformPen(pen, (1, 0, 0, -1, 0, 800)))
    finally: mg.S = old
    return pen.getCommands()

def preview(path):
    cells = []
    for name, (uni, W, draw) in N.items():
        adv = (W() if callable(W) else W) + 2 * mg.SB
        try: d = draw_svg(draw, adv)
        except Exception as e: d = ""; name += " ERR " + str(e)
        cells.append(f'<figure><svg viewBox="-40 0 {adv + 80} 1100"><line x1="-40" x2="{adv + 40}" y1="800" y2="800" class="b"/><line x1="-40" x2="{adv + 40}" y1="100" y2="100" class="c"/><line x1="-40" x2="{adv + 40}" y1="300" y2="300" class="x"/><path d="{d}"/></svg><figcaption>{chr(uni)} <code>U+{uni:04X}</code><br>{name}</figcaption></figure>')
    html = f"""<!doctype html><meta charset=utf-8><title>Ise Grotesk Phase 2 symbols</title>
<style>body{{font:14px system-ui;margin:24px;background:#fff;color:#111}}h1{{font-size:20px}}.g{{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px}}
figure{{margin:0;border:1px solid #ddd;padding:8px}}svg{{width:100%;height:150px}}path{{fill:#111}}.b{{stroke:#d3342c;stroke-width:3}}.c{{stroke:#999;stroke-width:3}}.x{{stroke:#bbb;stroke-width:2;stroke-dasharray:12 12}}
figcaption{{font-size:12px;color:#555}}.run{{font-size:48px;margin:16px 0}}</style>
<h1>Phase 2.1 draft symbols (Regular, not yet in the font)</h1>
<p>Red line = baseline (y 0). Grey = cap height (700). Dotted = maths axis (300).</p><div class=g>{''.join(cells)}</div>"""
    open(path, "w").write(html)

if __name__ == "__main__":
    import make_glyphs; mg = make_glyphs
    out = os.path.join(os.path.dirname(__file__), "..", "..", "Phase2-symbols-preview.html")
    preview(out); print("wrote", os.path.abspath(out), len(N), "glyphs")
