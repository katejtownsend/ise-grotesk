"""Ise Grotesk glyph generator (v0.7: uppercase A-Z, digits 0-9, lowercase a-z draft).
Builds sources/IseGrotesk-Regular.ufo from the grid in docs/DESIGN_BRIEF.md.
Needs only fontTools:  pip install fonttools
Run from the repo root:  python scripts/make_glyphs.py

Shapes may overlap; build.sh removes overlaps when compiling (pathops).
Curved letters are built from true circle arcs; diagonals are parallelograms
with flat horizontal cuts. Spacing is rough: proper sidebearings/kerning = v0.3.
"""
import math, os, shutil, sys, unicodedata
from fontTools.pens.transformPen import TransformPen
from fontTools.ufoLib import UFOWriter
from fontTools.ufoLib.glifLib import GlyphSet
from fontTools.pens.pointPen import SegmentToPointPen

# ---- Grid (1000 UPM) -- change here, regenerate ----
UPM, CAP, XH, ASC, DESC = 1000, 700, 500, 750, -250
S = 100          # monoline stroke
SB = 80          # sidebearing (rough)
STYLE = os.environ.get("ISE_STYLE", "Regular")        # Regular | Bold | Italic | Bold Italic
LCS = int(os.environ.get("ISE_S", 100))                # stroke weight of every glyph (Regular 100, Bold about 150)
PAD = int(os.environ["ISE_PAD"]) if "ISE_PAD" in os.environ else round((int(os.environ.get("ISE_S", 100)) - 100) * 0.0)    # extra sidebearing per side. Bold tested at -25, 0, +15: 0 keeps the same rhythm and line length as Regular
KSCALE = float(os.environ.get("ISE_KSCALE", 1 + (int(os.environ.get("ISE_S", 100)) - 100) / 100 * 0.4))   # heavier diagonals need deeper kerns
SLANT = float(os.environ.get("ISE_SLANT", 0))          # degrees; Italic uses 12
OUT = "sources/IseGrotesk-%s.ufo" % STYLE.replace(" ", "")

F_HOOK_END = int(os.environ.get("ISE_FHOOK", 40))   # lowercase f: where the hook ends (degrees; 60 was the original, 40 hooks over a little further)
E_BAR_OVERHANG = 18   # lowercase e: how far the crossbar sticks out past the bowl on each side (an intentional ledge)
LC_I_STYLE = "soft"   # lowercase i: "plain", "tower" (drum 140 wide, twin of the capital I) or "soft" (drum 118 wide)
A_BALL_R = 60      # radius of the disc on the A; its top sits exactly at cap height, so the A body is shorter (see A_ball)
H_STYLE = "gap"   # "step" (offset halves) or "gap" (hairline gap where the halves meet); see docs/BUILDING_DETAILS.md

# ---- Whimsy: building-inspired letterforms (see docs/BUILDING_DETAILS.md). Set False for the plain letter. ----
WHIMSY = {
    "I": True,   # Fagus Factory chimney tower: slim tapered shaft with a drum bulge
    "W": True,   # Fagus facade windows: uniform flat-bottomed points
    "w": True,   # lowercase w: window points, twin of the capital W (i and w = Ise and Walter's initials)
    "5": True,   # Ise's diaries, 1923-1928 (five years): a small bookmark ribbon hangs from the top bar
    "A": True,   # Apollo (Ise edited and translated "Apollo in the Democracy"); Japan's sun disc; a head above the body
    "H": True,   # Hannover, 1923: where Walter and Ise met. Crossbar = two halves meeting in the middle, slightly offset
    "Z": True,   # Isokon (Lawn Road Flats), Belsize Park: the Gropiuses' London home; stair flight as the diagonal
}

# ---- Geometry helpers ----
def area(pts):
    return sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1])) / 2

def poly(p, pts):
    if area(pts) < 0: pts = pts[::-1]          # keep every contour counter-clockwise
    p.moveTo(pts[0]); [p.lineTo(q) for q in pts[1:]]; p.closePath()

def rect(p, x0, y0, x1, y1):
    poly(p, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)])

def hw_for(dx_fn, dy):
    """Horizontal width of a diagonal stroke of perpendicular thickness S."""
    hw = S
    for _ in range(60): hw = S * math.sqrt(1 + (dx_fn(hw) / dy) ** 2)
    return hw

def diag(p, ya, xa, yb, xb, hw):
    """Stroke whose centreline runs (xa,ya)->(xb,yb); flat horizontal ends."""
    poly(p, [(xa - hw / 2, ya), (xa + hw / 2, ya), (xb + hw / 2, yb), (xb - hw / 2, yb)])

def line_quad(p, x0, y0, x1, y1, t=S):
    dx, dy = x1 - x0, y1 - y0; n = math.hypot(dx, dy); nx, ny = -dy / n * t / 2, dx / n * t / 2
    poly(p, [(x0 + nx, y0 + ny), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)])

def _arc(p, cx, cy, R, a0, a1, start):
    n = max(1, math.ceil(abs(a1 - a0) / (math.pi / 2) - 1e-9)); d = (a1 - a0) / n
    k = 4 / 3 * math.tan(d / 4)
    pt = lambda t: (cx + R * math.cos(t), cy + R * math.sin(t))
    if start: p.moveTo(pt(a0))
    for i in range(n):
        t0, t1 = a0 + i * d, a0 + (i + 1) * d
        (x0, y0), (x3, y3) = pt(t0), pt(t1)
        p.curveTo((x0 - k * R * math.sin(t0), y0 + k * R * math.cos(t0)),
                  (x3 + k * R * math.sin(t1), y3 - k * R * math.cos(t1)), (x3, y3))

def band(p, cx, cy, R, r, a0, a1):
    """Arc band between radii r..R, angles a0->a1 in degrees (counter-clockwise)."""
    a0, a1 = math.radians(a0), math.radians(a1)
    _arc(p, cx, cy, R, a0, a1, True)
    p.lineTo((cx + r * math.cos(a1), cy + r * math.sin(a1)))
    _arc(p, cx, cy, r, a1, a0, False)
    p.closePath()

def ring(p, cx, cy, R, r=None):
    r = max(R - S, 28) if r is None else r        # counters never close completely
    _arc(p, cx, cy, R, 0, 2 * math.pi, True); p.closePath()
    _arc(p, cx, cy, r, 2 * math.pi, 0, True); p.closePath()

def stem(p, x, y0=0, y1=CAP): rect(p, x, y0, x + S, y1)
DR = 60 * (LCS / 100) ** 0.8          # radius of dots (period, i dot, ...) at this weight

# ---- Glyph definitions: draw(p) functions; ink spans x = SB .. SB+W ----
G = {}
def glyph(name, uni, W, draw): G[name] = (uni, W + 2 * SB, draw)

glyph("space", 0x20, 220, lambda p: None)
glyph("nbspace", 0xA0, 220, lambda p: None)          # no-break space, same width as space
def I_tower(p):
    """Fagus Factory chimney: tapered shaft, drum bulge about 40% up, like the tower's lettered drum."""
    hd = S / 2 + 30; cx = SB + hd; y0, y1, d = 250, 330, 20       # drum half-width hd (80 at Regular); shaft is S wide
    poly(p, [(cx - S / 2, 0), (cx + S / 2, 0), (cx + S / 2, y1 + 20), (cx + S / 2 - 4, CAP), (cx - S / 2 + 4, CAP), (cx - S / 2, y1 + 20)])
    poly(p, [(cx - S / 2, y0 - 20), (cx + S / 2, y0 - 20), (cx + hd, y0 + 10), (cx + hd, y1 - 10),
             (cx + S / 2, y1 + 20), (cx - S / 2, y1 + 20), (cx - hd, y1 - 10), (cx - hd, y0 + 10)])
if WHIMSY["I"]: glyph("I", 0x49, LCS + 60, I_tower)
else: glyph("I", 0x49, LCS, lambda p: stem(p, SB))

def H_plain(p):
    W = 500; stem(p, SB); stem(p, SB + W - S); rect(p, SB + S, CAP / 2 - S / 2, SB + W - S, CAP / 2 + S / 2)

def H_meeting(p):
    """Hannover 1923: the crossbar is two halves that meet at the centre with a small step (OFF units), like two people of
    different heights meeting halfway. Walter (b. 1883) is the higher, left half."""
    W, OFF = 500, 30; cx = SB + W / 2; stem(p, SB); stem(p, SB + W - S)
    rect(p, SB + S, CAP / 2 - S / 2 + OFF / 2, cx + 10, CAP / 2 + S / 2 + OFF / 2)       # left half, higher
    rect(p, cx - 10, CAP / 2 - S / 2 - OFF / 2, SB + W - S, CAP / 2 + S / 2 - OFF / 2)   # right half, lower
def H_gap(p):
    """Hannover 1923, alternative: two bars that stop a hair short of each other (GAP units) in the middle."""
    W, GAP = 500, 28; cx = SB + W / 2; stem(p, SB); stem(p, SB + W - S)
    rect(p, SB + S, CAP / 2 - S / 2, cx - GAP / 2, CAP / 2 + S / 2); rect(p, cx + GAP / 2, CAP / 2 - S / 2, SB + W - S, CAP / 2 + S / 2)
glyph("H", 0x48, 500, (H_gap if H_STYLE == "gap" else H_meeting) if WHIMSY["H"] else H_plain)

def A_plain(p, h=CAP):
    W = 700; cx = SB + W / 2
    hw = hw_for(lambda w: cx - SB - w / 2, h)
    diag(p, 0, SB + hw / 2, h, cx, hw); diag(p, 0, SB + W - hw / 2, h, cx, hw)
    yb = round(h * 0.27); rect(p, SB + 150, yb, SB + W - 150, yb + S)           # crossbar

def A_ball(p):
    """A for Apollo, with a solid disc fused to the apex: the Japanese sun disc (Ise's Japan chapter) and a head on
    shoulders. The disc's top sits at cap height, so the whole glyph stays within the cap-height line;
    the A body is correspondingly shorter."""
    R, OVER = A_BALL_R * (0.5 + S / 200), 15                      # OVER = how far the disc overlaps the apex
    h = CAP - 2 * R + OVER                      # body height
    A_plain(p, h)
    _arc(p, SB + 350, CAP - R, R, 0, 2 * math.pi, True); p.closePath()
glyph("A", 0x41, 700, A_ball if WHIMSY["A"] else A_plain)

def B(p):
    W = 440; Rb = 175 + S / 4; cx = SB + W - Rb; stem(p, SB)              # two bowls meeting at a middle bar centred at y=350 (original at S=100)
    rect(p, SB + S, CAP - S, cx, CAP); rect(p, SB + S, 350 - S / 2, cx, 350 + S / 2); rect(p, SB + S, 0, cx, S)
    band(p, cx, CAP - Rb, Rb, Rb - S, -90, 90); band(p, cx, Rb, Rb, Rb - S, -90, 90)
glyph("B", 0x42, 440, B)

def C(p):
    band(p, SB + 350, 350, 350, 350 - S, 40, 320)
glyph("C", 0x43, 620, C)

def D(p):
    W = 620; cx = SB + W - 350; stem(p, SB)
    rect(p, SB + S, CAP - S, cx, CAP); rect(p, SB + S, 0, cx, S)
    band(p, cx, 350, 350, 350 - S, -90, 90)
glyph("D", 0x44, 620, D)

def E(p):
    W = 420; stem(p, SB)
    rect(p, SB, CAP - S, SB + W, CAP); rect(p, SB, 0, SB + W, S); rect(p, SB, CAP / 2 - S / 2, SB + W - 60, CAP / 2 + S / 2)
glyph("E", 0x45, 420, E)

def F(p):
    W = 400; stem(p, SB)
    rect(p, SB, CAP - S, SB + W, CAP); rect(p, SB, CAP / 2 - S / 2, SB + W - 60, CAP / 2 + S / 2)
glyph("F", 0x46, 400, F)

def Gl(p):
    cx = SB + 350; band(p, cx, 350, 350, 350 - S, 35, 360); rect(p, cx, 350 - S, cx + 350, 350)
glyph("G", 0x47, 700, Gl)

def J(p):
    W = 420; stem(p, SB + W - S, 210, CAP); band(p, SB + 210, 210, 210, 210 - S, 180, 360)
glyph("J", 0x4A, 420, J)

def K(p):
    W = 560; stem(p, SB); yj = 320
    hu = hw_for(lambda h: W - h, CAP - yj); hl = hw_for(lambda h: W - h, yj)
    diag(p, yj, SB + hu / 2, CAP, SB + W - hu / 2, hu); diag(p, yj, SB + hl / 2, 0, SB + W - hl / 2, hl)
glyph("K", 0x4B, 560, K)

glyph("L", 0x4C, 380, lambda p: (stem(p, SB), rect(p, SB, 0, SB + 380, S)))

def M(p):
    W = 760; cx = SB + W / 2; stem(p, SB); stem(p, SB + W - S)
    hw = hw_for(lambda h: cx - SB - h / 2 - S / 2, CAP)
    diag(p, CAP, SB + hw / 2, 0, cx, hw); diag(p, CAP, SB + W - hw / 2, 0, cx, hw)
glyph("M", 0x4D, 760, M)

def N(p):
    W = 560; stem(p, SB); stem(p, SB + W - S)
    hw = hw_for(lambda h: W - h, CAP); diag(p, CAP, SB + hw / 2, 0, SB + W - hw / 2, hw)
glyph("N", 0x4E, 560, N)

glyph("O", 0x4F, 700, lambda p: ring(p, SB + 350, 350, 350))

def P(p):
    W = 420; cx = SB + W - 210; stem(p, SB)
    rect(p, SB + S, CAP - S, cx, CAP); rect(p, SB + S, 280, cx, 280 + S); band(p, cx, 490, 210, 210 - S, -90, 90)
glyph("P", 0x50, 420, P)

def Q(p):
    ring(p, SB + 350, 350, 350); line_quad(p, SB + 430, 190, SB + 660, -40)
glyph("Q", 0x51, 700, Q)

def R(p):
    W = 440; P(p)
    hw = hw_for(lambda h: 200, 280)
    diag(p, 280, SB + 170, 0, SB + W - hw / 2 + 0, hw)
glyph("R", 0x52, 440, R)

def Sx(p):
    R = (CAP + S) / 4; cx = SB + R              # R chosen so the two bowls' end faces coincide exactly in the spine (200 at S=100)
    band(p, cx, CAP - R, R, R - S, 35, 270); band(p, cx, R, R, R - S, -145, 90)
glyph("S", 0x53, round((CAP + LCS) / 2), Sx)

def T(p):
    W = 560; rect(p, SB, CAP - S, SB + W, CAP); stem(p, SB + W / 2 - S / 2, 0, CAP)
glyph("T", 0x54, 560, T)

def U(p):
    W = 560; r = W / 2; stem(p, SB, r, CAP); stem(p, SB + W - S, r, CAP); band(p, SB + r, r, r, r - S, 180, 360)
glyph("U", 0x55, 560, U)

def V(p):
    W = 700; cx = SB + W / 2; hw = hw_for(lambda h: cx - SB - h / 2, CAP)
    diag(p, CAP, SB + hw / 2, 0, cx, hw); diag(p, CAP, SB + W - hw / 2, 0, cx, hw)
glyph("V", 0x56, 700, V)

def leg(p, ya, yb, xa_fn, xb_fn):
    hw = hw_for(lambda h: xb_fn(h) - xa_fn(h), abs(yb - ya)); diag(p, ya, xa_fn(hw), yb, xb_fn(hw), hw)

def Wg_plain(p):
    W = 920; x1, x3, cx = SB + W / 4, SB + 3 * W / 4, SB + W / 2
    hw = hw_for(lambda h: W / 4 - h / 2, CAP)
    diag(p, CAP, SB + hw / 2, 0, x1, hw); diag(p, 0, x1, CAP, cx, hw)
    diag(p, CAP, cx, 0, x3, hw); diag(p, 0, x3, CAP, SB + W - hw / 2, hw)

def Wg_windows(p):
    """Fagus facade windows: every point is a flat, equal-width cut (F), like a row of identical panes."""
    W, F = 960, 170; x1, x3, cx = SB + W / 4, SB + 3 * W / 4, SB + W / 2
    leg(p, CAP, 0, lambda h: SB + h / 2, lambda h: x1 - F / 2 + h / 2)
    leg(p, 0, CAP, lambda h: x1 + F / 2 - h / 2, lambda h: cx - F / 2 + h / 2)
    leg(p, CAP, 0, lambda h: cx + F / 2 - h / 2, lambda h: x3 - F / 2 + h / 2)
    leg(p, 0, CAP, lambda h: x3 + F / 2 - h / 2, lambda h: SB + W - h / 2)
if WHIMSY["W"]: glyph("W", 0x57, 960, Wg_windows)
else: glyph("W", 0x57, 920, Wg_plain)

def X(p):
    W = 640; hw = hw_for(lambda h: W - h, CAP)
    diag(p, 0, SB + hw / 2, CAP, SB + W - hw / 2, hw); diag(p, 0, SB + W - hw / 2, CAP, SB + hw / 2, hw)
glyph("X", 0x58, 640, X)

def Y(p):
    W = 640; cx = SB + W / 2; ym = 300
    hw = hw_for(lambda h: W / 2 - h / 2, CAP - ym)
    diag(p, CAP, SB + hw / 2, ym, cx, hw); diag(p, CAP, SB + W - hw / 2, ym, cx, hw); stem(p, cx - S / 2, 0, ym)
glyph("Y", 0x59, 640, Y)

def Z_plain(p):
    W = 560; hw = hw_for(lambda h: W - h, CAP)
    rect(p, SB, CAP - S, SB + W, CAP); rect(p, SB, 0, SB + W, S)
    diag(p, 0, SB + hw / 2, CAP, SB + W - hw / 2, hw)

def Z_stairs(p, n=3, t=S):
    """Isokon stair flight: top and bottom decks joined by a stepped run (n risers, stroke t) in place of the diagonal."""
    W = 680
    rect(p, SB, CAP - S, SB + W, CAP); rect(p, SB, 0, SB + W, S)          # decks
    dx, dy = (W - t) / n, (CAP - 2 * S + t) / n      # gaps between treads match the gaps to the decks
    x, y = SB + t / 2, S - t / 2
    for i in range(n):                                                    # tread then riser
        rect(p, x - t / 2, y - t / 2, x + dx + t / 2, y + t / 2)
        x += dx
        rect(p, x - t / 2, y - t / 2, x + t / 2, y + dy + t / 2)
        y += dy
if WHIMSY["Z"]: glyph("Z", 0x5A, 680, Z_stairs)
else: glyph("Z", 0x5A, 560, Z_plain)

# ---- Digits 0-9 (lining figures, cap height). Draft: same grid and stroke as the capitals ----
def zero(p):
    W = 440; cx = SB + W / 2; R = W / 2
    stem(p, SB, R, CAP - R); stem(p, SB + W - S, R, CAP - R)
    band(p, cx, CAP - R, R, R - S, 0, 180); band(p, cx, R, R, R - S, 180, 360)
glyph("zero", 0x30, 440, zero)

def one(p):
    W = 320; stem(p, SB + W - S)
    hw = hw_for(lambda h: W - h, 170); diag(p, CAP - 170, SB + hw / 2, CAP, SB + W - hw / 2, hw)   # flag
glyph("one", 0x31, 320, one)

def two(p):
    """Bowl on top; the diagonal continues the arc's tangent, with the arc's own radial cut as its top edge (no kink)."""
    W = 400; cx = SB + 200; cy = CAP - 200; Rc = 200 - S / 2
    def left_edge(deg):                                   # where the diagonal's bottom-left corner lands, relative to SB
        a = math.radians(deg); px, py = cx + Rc * math.cos(a), cy + Rc * math.sin(a)
        return px + py * math.tan(a) - S / (2 * math.cos(a)) - SB
    lo, hi = -50.0, -20.0
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if left_edge(mid) < 0 else (lo, mid)
    deg = (lo + hi) / 2; a = math.radians(deg)
    band(p, cx, cy, 200, 200 - S, deg, 165)
    d = (math.sin(a), -math.cos(a)); n = (math.cos(a), math.sin(a)); P = (cx + Rc * n[0], cy + Rc * n[1])
    A1 = (P[0] + n[0] * S / 2, P[1] + n[1] * S / 2); A2 = (P[0] - n[0] * S / 2, P[1] - n[1] * S / 2)
    B = lambda q: (q[0] + d[0] * (-q[1] / d[1]), 0)
    poly(p, [A1, A2, B(A2), B(A1)])
    rect(p, SB, 0, SB + W, S)
glyph("two", 0x32, 400, two)

def three(p):
    Rb = 175 + S / 4; cx = SB + Rb                                       # two bowls meeting at a bar centred at y=350
    band(p, cx, CAP - Rb, Rb, max(Rb - S, 28), -90, 150); band(p, cx, Rb, Rb, max(Rb - S, 28), -150, 90); rect(p, cx - Rb + 100, 350 - S / 2, cx, 350 + S / 2)
glyph("three", 0x33, 350 + LCS // 2, three)

def four(p):
    W = 520; xs = SB + W - 60                                   # stem right edge
    rect(p, SB, 170, SB + W, 270); stem(p, xs - S)
    hw = hw_for(lambda h: xs - h / 2 - SB - h / 2, CAP - 170); diag(p, 170, SB + hw / 2, CAP, xs - hw / 2, hw)
glyph("four", 0x34, 520, four)

def five_core(p, ribbon):
    W = 420; cx = SB + 210
    rect(p, SB, CAP - S, SB + W - 40, CAP); stem(p, SB, 420 - S, CAP)
    rect(p, SB, 420 - S, cx, 420)                       # bar from stem into the bowl's top
    band(p, cx, 210, 210, 210 - S, -150, 90)
    if ribbon:                                      # bookmark ribbon: full stroke width, right edge flush with the top bar's end
        x1 = SB + W - 40; x0 = x1 - S; yt, yb = CAP - S + 10, CAP - S - 110
        poly(p, [(x0, yt), (x1, yt), (x1, yb), ((x0 + x1) / 2, yb + 45), (x0, yb)])
def five(p): five_core(p, WHIMSY["5"])
glyph("five", 0x35, 420, five)

def six(p):
    cx = SB + 240
    ring(p, cx, 240, 240); stem(p, SB, 240, 460); band(p, cx, 460, 240, 240 - S, 50, 180)
glyph("six", 0x36, 480, six)

def seven(p):
    W = 460; rect(p, SB, CAP - S, SB + W, CAP)
    hw = hw_for(lambda h: W - 90 - h, CAP); diag(p, 0, SB + 90 + hw / 2, CAP, SB + W - hw / 2, hw)
glyph("seven", 0x37, 460, seven)

def eight(p):
    cx = SB + 215; ring(p, cx, 515, 185); ring(p, cx, 215, 215)
glyph("eight", 0x38, 430, eight)

glyph("nine", 0x39, 480, lambda p: six(TransformPen(p, (-1, 0, 0, -1, 2 * (SB + 240), CAP))))   # six, rotated 180 degrees

# ---- Lowercase a-z (draft): single-storey a and g, round forms are circles of diameter x-height ----
R_ = XH / 2                                              # 250: bowl radius
def bowl(p, cx=None): ring(p, (SB + R_) if cx is None else cx, R_, R_)       # 500 wide, S stroke
def dot(p, cx): r = 0.6 * S; _arc(p, cx, CAP - r, r, 0, 2 * math.pi, True); p.closePath()   # 60 at S=100; grows with the lowercase stroke   # same 60-unit disc as the A's ball

def lc_a(p): bowl(p); stem(p, SB + 2 * R_ - S, 0, XH)
glyph("a", 0x61, 500, lc_a)
def lc_b(p): stem(p, SB, 0, ASC); bowl(p)
glyph("b", 0x62, 500, lc_b)
glyph("c", 0x63, 440, lambda p: band(p, SB + R_, R_, R_, R_ - S, 40, 320))
def lc_d(p): bowl(p); stem(p, SB + 2 * R_ - S, 0, ASC)
glyph("d", 0x64, 500, lc_d)
def lc_e(p):
    """The crossbar runs straight through and sticks out E_BAR_OVERHANG units past the bowl on both sides, a deliberate ledge
    (a few units would just look like a rendering glitch). The bowl starts exactly at the bar's top edge."""
    O = E_BAR_OVERHANG; q = TransformPen(p, (1, 0, 0, 1, O, 0))          # shift right so the overhang stays inside the sidebearings
    cx, cy = SB + R_, R_; hb = S / 2
    a = math.asin(hb / R_)
    band(q, cx, cy, R_, R_ - S, math.degrees(a), 320)
    rect(q, cx - R_ - O, cy - hb, cx + R_ + O, cy + hb)
glyph("e", 0x65, 500 + 2 * E_BAR_OVERHANG, lc_e)
def lc_f(p):
    Rf = 170 + (S - 100) * 0.4; x0 = SB + 70; stem(p, x0, 0, ASC - Rf); band(p, x0 + Rf, ASC - Rf, Rf, Rf - S, F_HOOK_END, 180)
    rect(p, SB, XH - S, SB + 260, XH)
glyph("f", 0x66, 320 + round((LCS - 100) * 0.8), lc_f)
def lc_g(p): bowl(p); stem(p, SB + 2 * R_ - S, 0, XH); band(p, SB + R_, 0, R_, R_ - S, 215, 360)
glyph("g", 0x67, 500, lc_g)
def arch(p, W=440, stem_top=XH):
    R = W / 2; cy = XH - R; stem(p, SB, 0, stem_top); stem(p, SB + W - S, 0, cy + 10); band(p, SB + R, cy, R, R - S, 0, 180)   # +10: stem overlaps the arch, no seam
glyph("h", 0x68, 440, lambda p: arch(p, 440, ASC))
def lc_i_drum(p, hw=70, ch=15, with_dot=True):
    """Lowercase twin of the Fagus-chimney capital I: the same drum bulge, scaled down (stem stays full width and height)."""
    cx = SB + hw; y0, y1 = 150, 230
    rect(p, cx - S / 2, 0, cx + S / 2, XH)
    poly(p, [(cx - S / 2, y0 - ch), (cx + S / 2, y0 - ch), (cx + hw, y0 + 5), (cx + hw, y1 - 5),
             (cx + S / 2, y1 + ch), (cx - S / 2, y1 + ch), (cx - hw, y1 - 5), (cx - hw, y0 + 5)])
    if with_dot: dot(p, cx)
def lc_i(p):
    if LC_I_STYLE == "tower": lc_i_drum(p, S / 2 + 20, 15)
    elif LC_I_STYLE == "soft": lc_i_drum(p, S / 2 + 9, 12)
    else: stem(p, SB, 0, XH); dot(p, SB + S / 2)
glyph("i", 0x69, {"tower": LCS + 40, "soft": LCS + 18}.get(LC_I_STYLE, LCS), lc_i)
def lc_j(p):
    R = 150; stem(p, SB + 2 * R - S, -(250 - R), XH); band(p, SB + R, -(250 - R), R, R - S, 180, 360); dot(p, SB + 2 * R - S / 2)
glyph("j", 0x6A, 300, lc_j)
def lc_k(p):
    W, yj = 420, 200; stem(p, SB, 0, ASC)
    hu = hw_for(lambda h: W - h, XH - yj); hl = hw_for(lambda h: W - h, yj)
    diag(p, yj, SB + hu / 2, XH, SB + W - hu / 2, hu); diag(p, yj, SB + hl / 2, 0, SB + W - hl / 2, hl)
glyph("k", 0x6B, 420, lc_k)
glyph("l", 0x6C, max(S, LCS), lambda p: stem(p, SB, 0, ASC))
def lc_m(p):
    c = (700 - 3 * S) / 2; R = (2 * S + c) / 2; cy = XH - R        # three stems of width S, two equal counters c; at S=100 this is the original m
    xm, xr = SB + S + c, SB + 2 * S + 2 * c
    stem(p, SB, 0, XH); stem(p, xm, 0, cy + 10); stem(p, xr, 0, cy + 10)
    band(p, SB + R, cy, R, R - S, 0, 180); band(p, SB + 700 - R, cy, R, R - S, 0, 180)
glyph("m", 0x6D, 700, lc_m)
glyph("n", 0x6E, 440, lambda p: arch(p, 440, XH))
glyph("o", 0x6F, 500, lambda p: bowl(p))
def lc_p(p): stem(p, SB, DESC, XH); bowl(p)
glyph("p", 0x70, 500, lc_p)
def lc_q(p): stem(p, SB + 2 * R_ - S, DESC, XH); bowl(p)
glyph("q", 0x71, 500, lc_q)
def lc_r(p): stem(p, SB, 0, XH); band(p, SB + 220, 280, 220, 220 - S, 40, 180)
glyph("r", 0x72, 390, lc_r)
def lc_s(p):
    St = S if S <= 100 else 100 + (S - 100) * 0.45; R = (XH + St) / 4; cx = SB + R      # heavier s uses a slightly lighter curve so the counters stay open
    band(p, cx, XH - R, R, R - St, 35, 270); band(p, cx, R, R, R - St, -145, 90)
glyph("s", 0x73, round((XH + (LCS if LCS <= 100 else 100 + (LCS - 100) * 0.45)) / 2), lc_s)
def lc_t(p):
    x0 = SB + 70; stem(p, x0, 170, 650); band(p, x0 + 170, 170, 170, 170 - S, 180, 310); rect(p, SB, XH - S, SB + 260, XH)
glyph("t", 0x74, 350, lc_t)
def lc_u(p):
    W = 440; R = W / 2; stem(p, SB, R - 10, XH); stem(p, SB + W - S, 0, XH); band(p, SB + R, R, R, R - S, 180, 360)
glyph("u", 0x75, 440, lc_u)
def lc_v(p):
    W = 520; cx = SB + W / 2; hw = hw_for(lambda h: cx - SB - h / 2, XH)
    diag(p, XH, SB + hw / 2, 0, cx, hw); diag(p, XH, SB + W - hw / 2, 0, cx, hw)
glyph("v", 0x76, 520, lc_v)
def lc_w_plain(p):
    W = 760; x1, x3, cx = SB + W / 4, SB + 3 * W / 4, SB + W / 2; hw = hw_for(lambda h: W / 4 - h / 2, XH)
    diag(p, XH, SB + hw / 2, 0, x1, hw); diag(p, 0, x1, XH, cx, hw); diag(p, XH, cx, 0, x3, hw); diag(p, 0, x3, XH, SB + W - hw / 2, hw)
def lc_w_windows(p):
    """Lowercase twin of the Fagus-window capital W: all five points are flat cuts of equal width F."""
    W, F = 780, 130; x1, x3, cx = SB + W / 4, SB + 3 * W / 4, SB + W / 2
    leg(p, XH, 0, lambda h: SB + h / 2, lambda h: x1 - F / 2 + h / 2)
    leg(p, 0, XH, lambda h: x1 + F / 2 - h / 2, lambda h: cx - F / 2 + h / 2)
    leg(p, XH, 0, lambda h: cx + F / 2 - h / 2, lambda h: x3 - F / 2 + h / 2)
    leg(p, 0, XH, lambda h: x3 + F / 2 - h / 2, lambda h: SB + W - h / 2)
glyph("w", 0x77, 780 if WHIMSY["w"] else 760, lc_w_windows if WHIMSY["w"] else lc_w_plain)
def lc_x(p):
    W = 480; hw = hw_for(lambda h: W - h, XH)
    diag(p, 0, SB + hw / 2, XH, SB + W - hw / 2, hw); diag(p, 0, SB + W - hw / 2, XH, SB + hw / 2, hw)
glyph("x", 0x78, 480, lc_x)
def lc_y(p):
    W = 520; hw = hw_for(lambda h: (W - h / 2) - (20 + h / 2), XH - DESC)
    xt, xb = SB + W - hw / 2, SB + 20 + hw / 2                     # right arm: top and bottom centreline x
    diag(p, DESC, xb, XH, xt, hw)
    xm = xb + (60 - DESC) / (XH - DESC) * (xt - xb)                 # left arm joins the right arm near the baseline
    hl = hw_for(lambda h: xm - SB - h / 2, XH - 60); diag(p, 60, xm, XH, SB + hl / 2, hl)
glyph("y", 0x79, 520, lc_y)
def lc_z(p):
    W = 440; hw = hw_for(lambda h: W - h, XH)
    rect(p, SB, XH - S, SB + W, XH); rect(p, SB, 0, SB + W, S); diag(p, 0, SB + hw / 2, XH, SB + W - hw / 2, hw)
glyph("z", 0x7A, 440, lc_z)

# ---- Punctuation (draft) ----
def comma_shape(p, cx, base=0):
    """Round dot (radius DR, 60 at Regular) with a short tail swept down-left."""
    k = DR / 60; _arc(p, cx, base + DR, DR, 0, 2 * math.pi, True); p.closePath()
    poly(p, [(cx - 5 * k, base + 30 * k), (cx + 58 * k, base + 25 * k), (cx - 12 * k, base - 125 * k), (cx - 62 * k, base - 100 * k)])
def per_dot(p, cx, cy): _arc(p, cx, cy, DR, 0, 2 * math.pi, True); p.closePath()

W_D, CP = round(2 * DR), round(DR + 2)      # dot width and comma centre
glyph("period", 0x2E, W_D, lambda p: per_dot(p, SB + DR, DR))
glyph("comma", 0x2C, W_D + 4, lambda p: comma_shape(p, SB + CP))
glyph("colon", 0x3A, W_D, lambda p: (per_dot(p, SB + DR, DR), per_dot(p, SB + DR, XH - DR)))
glyph("semicolon", 0x3B, W_D + 4, lambda p: (comma_shape(p, SB + CP), per_dot(p, SB + CP, XH - DR)))
glyph("exclam", 0x21, W_D, lambda p: (rect(p, SB + DR - S / 2, 2 * DR + 80, SB + DR + S / 2, CAP), per_dot(p, SB + DR, DR)))
def question(p):
    cx = SB + 200; band(p, cx, 500, 200, 200 - S, -90, 160); rect(p, cx - S / 2, 200, cx + S / 2, 400); per_dot(p, cx, DR)
glyph("question", 0x3F, 400, question)
glyph("quotesingle", 0x27, LCS, lambda p: rect(p, SB, 450, SB + S, CAP))
glyph("quotedbl", 0x22, LCS + 180, lambda p: (rect(p, SB, 450, SB + S, CAP), rect(p, SB + 180, 450, SB + 180 + S, CAP)))
def qright(p, n=1):
    for i in range(n): comma_shape(p, SB + CP + i * (W_D + 50), CAP - 2 * DR)
def qleft(p, n=1):
    q = TransformPen(p, (-1, 0, 0, -1, 2 * (SB + CP) + (n - 1) * (W_D + 50), 2 * (CAP - 2 * DR + 122.5 * DR / 60)))
    for i in range(n): comma_shape(q, SB + CP + i * (W_D + 50), CAP - 2 * DR)
glyph("quoteright", 0x2019, W_D + 4, qright)
glyph("quoteleft", 0x2018, W_D + 4, qleft)
glyph("quotedblright", 0x201D, 2 * W_D + 54, lambda p: qright(p, 2))
glyph("quotedblleft", 0x201C, 2 * W_D + 54, lambda p: qleft(p, 2))
glyph("hyphen", 0x2D, 260, lambda p: rect(p, SB, 300 - S / 2, SB + 260, 300 + S / 2))
glyph("endash", 0x2013, 500, lambda p: rect(p, SB, 300 - S / 2, SB + 500, 300 + S / 2))
glyph("emdash", 0x2014, 1000, lambda p: rect(p, SB, 300 - S / 2, SB + 1000, 300 + S / 2))
glyph("parenleft", 0x28, 240, lambda p: band(p, SB + 700, 300, 700, 700 - S, 140, 220))
glyph("parenright", 0x29, 240, lambda p: band(p, SB - 460, 300, 700, 700 - S, -40, 40))
glyph("bracketleft", 0x5B, 200, lambda p: (stem(p, SB, -150, 750), rect(p, SB, -150, SB + 200, -150 + S), rect(p, SB, 750 - S, SB + 200, 750)))
glyph("bracketright", 0x5D, 200, lambda p: (stem(p, SB + 200 - S, -150, 750), rect(p, SB, -150, SB + 200, -150 + S), rect(p, SB, 750 - S, SB + 200, 750)))
def _brace(p, left):
    """Braces: two hooks, two stems, and a pointed middle made of two quarter arcs. Stroke centre-line radius c=100, ink 200 wide, y -150..750.
    The stems share x for both braces, so { and } are mirror images."""
    c = 100; h = S / 2; R = c + h; r = c - h; xs = SB + c - h; e = 8       # e: tiny stem overlap so no seams appear at the joins
    ytop, ybot = 750 - R, -150 + R                                         # hook centres (y)
    stem(p, xs, 300 + c - e, ytop + e); stem(p, xs, ybot - e, 300 - c + e)
    if left:
        band(p, SB + 2 * c, ytop, R, r, 90, 180); band(p, SB + 2 * c, ybot, R, r, 180, 270)
        band(p, SB, 300 + c, R, r, 268, 360);      band(p, SB, 300 - c, R, r, 0, 92)
    else:
        band(p, SB, ytop, R, r, 0, 90);         band(p, SB, ybot, R, r, 270, 360)
        band(p, SB + 2 * c, 300 + c, R, r, 180, 272); band(p, SB + 2 * c, 300 - c, R, r, 88, 180)
glyph("braceleft", 0x7B, 200, lambda p: _brace(p, True))
glyph("braceright", 0x7D, 200, lambda p: _brace(p, False))
def slash(p, flip=False):
    W = 400; hw = hw_for(lambda h: W - h, 900)
    a, b = (SB + W - hw / 2, SB + hw / 2) if flip else (SB + hw / 2, SB + W - hw / 2)
    diag(p, -150, a, 750, b, hw)
glyph("slash", 0x2F, 400, slash)
glyph("backslash", 0x5C, 400, lambda p: slash(p, True))
glyph("plus", 0x2B, 400, lambda p: (rect(p, SB, 300 - S / 2, SB + 400, 300 + S / 2), rect(p, SB + 200 - S / 2, 100, SB + 200 + S / 2, 500)))
glyph("equal", 0x3D, 400, lambda p: (rect(p, SB, 200 - S / 2, SB + 400, 200 + S / 2), rect(p, SB, 400 - S / 2, SB + 400, 400 + S / 2)))
glyph("underscore", 0x5F, 500, lambda p: rect(p, SB, -100 - S / 2, SB + 500, -100 + S / 2))

# ---- Ampersand: Gropius's "Art and Technique: a New Unity" (Ulm speech, 1955): a circle and a square joined ----
def ampersand(p):
    """Classic ampersand skeleton built from the two forms: curves (circle loop on top, circular bowl below) and one straight
    diagonal that runs from the top loop to the tail. Straight plus curved: 'Art and Technique: a New Unity'."""
    ring(p, SB + 200, 550, 150)                                             # upper loop (closed circle)
    band(p, SB + 215, 215, 215, 215 - S, 95, 335)                                  # lower bowl: open on the right, closed by the diagonal
    hw = hw_for(lambda h: (SB + 490) - (SB + 175), 440)
    diag(p, 0, SB + 490, 440, SB + 175, hw)                                    # diagonal from the loop's lower left to the tail
glyph("ampersand", 0x26, 560, ampersand)

# ---- "Logic" set (OpenType ss01): the plain forms of every whimsy letter. The default forms are the "magic" set. ----
# Gropius at Ulm (1955): restore "the magical element" beside the logical one. Each magic letter keeps a strict geometric
# skeleton; ss01 swaps in the skeleton alone, for anyone who wants it plain.
glyph("A.ss01", None, 700, A_plain)
glyph("H.ss01", None, 500, H_plain)
glyph("I.ss01", None, S, lambda p: stem(p, SB))
glyph("W.ss01", None, 920, Wg_plain)
glyph("Z.ss01", None, 560, Z_plain)
glyph("five.ss01", None, 420, lambda p: five_core(p, False))
glyph("i.ss01", None, S, lambda p: (stem(p, SB, 0, XH), dot(p, SB + S / 2)))
glyph("w.ss01", None, 760, lc_w_plain)
FEATURES = """languagesystem DFLT dflt;
languagesystem latn dflt;

feature ss01 {
    featureNames { name "Logic: plain forms of the whimsy letters"; };
    sub A by A.ss01;  sub H by H.ss01;  sub I by I.ss01;  sub W by W.ss01;  sub Z by Z.ss01;
    sub five by five.ss01;  sub i by i.ss01;  sub w by w.ss01;
} ss01;
"""

def polyline_stroke(p, pts, t=S):
    """Outline of an open polyline stroked with thickness t: butt caps, mitred corners (no notches at the joins)."""
    h = t / 2; n = len(pts)
    def unit(a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy); return dx / L, dy / L
    ds = [unit(pts[i], pts[i + 1]) for i in range(n - 1)]
    def offs(side):
        out = []
        for i in range(n):
            if i == 0: d1 = d2 = ds[0]
            elif i == n - 1: d1 = d2 = ds[-1]
            else: d1, d2 = ds[i - 1], ds[i]
            n1 = (-d1[1] * side, d1[0] * side); n2 = (-d2[1] * side, d2[0] * side)
            bx, by = n1[0] + n2[0], n1[1] + n2[1]; bl = math.hypot(bx, by)
            k = h / (bl / 2) if bl else h                           # mitre length: h / cos(half-angle)
            out.append((pts[i][0] + bx / bl * k, pts[i][1] + by / bl * k) if bl else (pts[i][0] + n1[0] * h, pts[i][1] + n1[1] * h))
        return out
    poly(p, offs(1) + offs(-1)[::-1])

# ---- Symbols (draft) ----
def tilde_shape(p, x0=SB, cy=300, R=None, r=None):
    R = 160 + (S - 100) / 2 if R is None else R; r = R - S if r is None else r
    """Wave built from two half-rings (hump and dip) that share their end, stroke S throughout."""
    band(p, x0 + R, cy, R, r, 0, 180); band(p, x0 + R + (R + r), cy, R, r, 180, 360)
glyph("asciitilde", 0x7E, 540 + (LCS - 100), tilde_shape)

def percent(p):
    W = 560; per_dot2 = lambda cx, cy, R: (_arc(p, cx, cy, R, 0, 2 * math.pi, True), p.closePath())
    per_dot2(SB + 110, 590, 110); per_dot2(SB + W - 110, 110, 110)
    hw = hw_for(lambda h: W - 60 - h, 700); diag(p, 0, SB + 60 + hw / 2, 700, SB + W - 60 - hw / 2 + 60, hw)
glyph("percent", 0x25, 560, percent)

def dollar(p):
    Sx(p); cx = SB + (CAP + S) / 4
    rect(p, cx - S / 2, CAP, cx + S / 2, CAP + 70); rect(p, cx - S / 2, -70, cx + S / 2, 0)       # ticks above and below the S
glyph("dollar", 0x24, round((CAP + LCS) / 2), dollar)

def numbersign(p):
    W = 520
    rect(p, SB + 150 - S / 2, 0, SB + 150 + S / 2, CAP); rect(p, SB + 370 - S / 2, 0, SB + 370 + S / 2, CAP)
    rect(p, SB, 220 - S / 2, SB + W, 220 + S / 2); rect(p, SB, 480 - S / 2, SB + W, 480 + S / 2)
glyph("numbersign", 0x23, 520, numbersign)

def asterisk(p):
    cx, cy, L = SB + 170, 520, 170
    for ang in (90, 30, 150):
        dx, dy = L * math.cos(math.radians(ang)), L * math.sin(math.radians(ang))
        line_quad(p, cx - dx, cy - dy, cx + dx, cy + dy, 0.8 * S)
glyph("asterisk", 0x2A, 340, asterisk)

def at_sign(p):
    cx, cy = SB + 350, 300
    band(p, cx, cy, 350, 350 - S, -35, 300)                           # outer ring, open at lower right
    k = 0.65 if S > 100 else 1                                        # the inner "a" carries less weight so it stays open
    ring(p, cx, cy, 150, 150 - k * S)                                 # the "a"
    rect(p, cx + 150 - k * S, cy - 150, cx + 150, cy + 150)           # its stem
glyph("at", 0x40, 700, at_sign)

def chevron(p, flip=False):
    W = 400; pts = [(SB + W, 500), (SB + 40, 300), (SB + W, 100)]
    if flip: pts = [(2 * SB + W - x, y) for x, y in pts]
    polyline_stroke(p, pts, S)
glyph("less", 0x3C, 400, chevron)
glyph("greater", 0x3E, 400, lambda p: chevron(p, True))
glyph("bar", 0x7C, LCS, lambda p: stem(p, SB, -150, 750))

def caret(p):
    W = 420; cx = SB + W / 2; hw = hw_for(lambda h: cx - SB - h / 2, 260)
    diag(p, 440, SB + hw / 2, 700, cx, hw); diag(p, 440, SB + W - hw / 2, 700, cx, hw)
glyph("asciicircum", 0x5E, 420, caret)


glyph("bullet", 0x2022, 200, lambda p: (_arc(p, SB + 100, 300, 100, 0, 2 * math.pi, True), p.closePath()))


# ======================= Step 2: language coverage =======================
# ---- Accent marks: drawn centred on x = SB + 150, at lowercase height (y 560..700). Capitals lift them by CAP_LIFT. ----
BELOW_MARKS = {"cedilla", "ogonek"}
def _with_mt(d, mt, p):
    global MT
    old, MT = MT, mt
    try: d(p)
    finally: MT = old
MT = 80                       # accent stroke (a little lighter than the letters, so accents never outweigh them)
CAP_LIFT = CAP - XH           # 200
def mhw(dx, dy, t=None): t = MT if t is None else t; return t * math.sqrt(1 + (dx / dy) ** 2)
MC = SB + 150
def m_disc(p, cx, cy, R=None): R = 55 * MT / 80 if R is None else R; _arc(p, cx, cy, R, 0, 2 * math.pi, True); p.closePath()
def m_acute(p): diag(p, 560, MC - 45, 700, MC + 45, mhw(90, 140))
def m_grave(p): diag(p, 560, MC + 45, 700, MC - 45, mhw(90, 140))
def m_circumflex(p): hw = mhw(90, 140); diag(p, 560, MC - 90, 700, MC, hw); diag(p, 560, MC + 90, 700, MC, hw)
def m_caron(p): hw = mhw(90, 140); diag(p, 700, MC - 90, 560, MC, hw); diag(p, 700, MC + 90, 560, MC, hw)
def m_dieresis(p): m_disc(p, MC - 80, 630); m_disc(p, MC + 80, 630)
def m_dotaccent(p): m_disc(p, MC, 630)
def m_ring(p): ring(p, MC, 620, 80, 80 - 55 * MT / 80)
def m_tilde(p): t = 60 * MT / 80; R = 10 + t; band(p, MC - 40, 630, R, R - t, 0, 180); band(p, MC + 40, 630, R, R - t, 180, 360)
def m_macron(p): h = MT / 2; rect(p, MC - 90, 640 - h, MC + 90, 640 + h)
def m_breve(p): band(p, MC, 700, 90, 90 - 70 * MT / 80, 180, 360)
def m_hungarumlaut(p): hw = mhw(70, 140); diag(p, 560, MC - 85, 700, MC - 15, hw); diag(p, 560, MC + 15, 700, MC + 85, hw)
def m_cedilla(p): comma_shape(p, MC, -125)                          # comma-style cedilla; also serves as comma-below (ș ț ģ ķ ļ ņ)
def m_ogonek(p): polyline_stroke(p, [(MC, 0), (MC, -80), (MC + 70, -140)], 70)
MARKS = {"acute": (0xB4, m_acute), "grave": (0x60, m_grave), "circumflex": (0x2C6, m_circumflex), "caron": (0x2C7, m_caron),
         "dieresis": (0xA8, m_dieresis), "dotaccent": (0x2D9, m_dotaccent), "ring": (0x2DA, m_ring), "tilde": (0x2DC, m_tilde),
         "macron": (0xAF, m_macron), "breve": (0x2D8, m_breve), "hungarumlaut": (0x2DD, m_hungarumlaut),
         "cedilla": (0xB8, m_cedilla), "ogonek": (0x2DB, m_ogonek)}
for _n, (_u, _d) in MARKS.items(): glyph(_n, _u, 300, _d)
LC_MT = round(80 * (1 + (LCS - 100) / 100 * 0.6))      # accents on lowercase letters follow the heavier stroke (80 at Regular)
if LCS != 100:
    for _n, (_u, _d) in MARKS.items():
        if _n not in BELOW_MARKS: glyph(_n + ".lc", None, 300, (lambda d: (lambda p: _with_mt(d, LC_MT, p)))(_d))
COMBINING = {0x300: "grave", 0x301: "acute", 0x302: "circumflex", 0x303: "tilde", 0x308: "dieresis", 0x30A: "ring", 0x30C: "caron",
             0x304: "macron", 0x306: "breve", 0x307: "dotaccent", 0x328: "ogonek", 0x30B: "hungarumlaut", 0x327: "cedilla", 0x326: "cedilla"}
BELOW = {"cedilla", "ogonek"}

# ---- Bespoke base glyphs ----
glyph("dotlessi", 0x131, {"tower": LCS + 40, "soft": LCS + 18}.get(LC_I_STYLE, LCS),
      lambda p: (lc_i_drum(p, S / 2 + 9, 12, False) if LC_I_STYLE == "soft" else lc_i_drum(p, S / 2 + 20, 15, False) if LC_I_STYLE == "tower" else stem(p, SB, 0, XH)))
glyph("dotlessi.ss01", None, LCS, lambda p: stem(p, SB, 0, XH))

def A_inner(p):
    """Accented capital A: the full-height A with its disc moved inside, between the two stalks, so the apex is free for the mark."""
    A_plain(p); hw = hw_for(lambda w: 350 - w / 2, CAP)
    _arc(p, SB + 350, 375, 42 * (0.5 + S / 200), 0, 2 * math.pi, True); p.closePath()
glyph("A.inner", None, 700, A_inner)
glyph("A.inner.plain", None, 700, A_plain)

def slash_diag(p, ya, xa, yb, xb): hw = hw_for(lambda h: xb - xa - h, yb - ya); diag(p, ya, xa + hw / 2, yb, xb - hw / 2, hw)
glyph("lslash", 0x142, 180, lambda p: (stem(p, SB + 40, 0, ASC), slash_diag(p, 250, SB, 500, SB + 180)))
glyph("Lslash", 0x141, 440, lambda p: (rect(p, SB + 60, 0, SB + 160, CAP), rect(p, SB + 60, 0, SB + 440, S), slash_diag(p, 240, SB, 480, SB + 260)))
def dstroke(p): lc_d(p); rect(p, SB + 340, 600, SB + 550, 680)
glyph("dcroat", 0x111, 550, dstroke)
def Dstroke(p):
    q = TransformPen(p, (1, 0, 0, 1, 80, 0)); D(q); rect(p, SB, 300, SB + 240, 400)
glyph("Dcroat", 0x110, 700, Dstroke)
glyph("oslash", 0xF8, 500, lambda p: (bowl(p), slash_diag(p, -40, SB + 40, 540, SB + 460)))
glyph("Oslash", 0xD8, 700, lambda p: (ring(p, SB + 350, 350, 350), slash_diag(p, -50, SB + 70, 750, SB + 630)))

def e_core(p, cx, x_bar0):
    cy, hb = R_, S / 2; a = math.asin(hb / R_)
    band(p, cx, cy, R_, R_ - S, math.degrees(a), 320)
    p.moveTo((x_bar0, cy - hb)); p.lineTo((cx + R_ * math.cos(a), cy - hb)); _arc(p, cx, cy, R_, -a, a, False)
    p.lineTo((x_bar0, cy + hb)); p.closePath()
glyph("ae", 0xE6, 900, lambda p: (bowl(p), stem(p, SB + 2 * R_ - S, 0, XH), e_core(p, SB + 650, SB + 2 * R_ - S)))
glyph("oe", 0x153, 900, lambda p: (bowl(p), e_core(p, SB + 650, SB + 2 * R_ - S)))
def OE(p):
    ring(p, SB + 350, 350, 350); rect(p, SB + 600, 0, SB + 700, CAP)
    rect(p, SB + 600, 600, SB + 1020, 700); rect(p, SB + 600, 300, SB + 940, 400); rect(p, SB + 600, 0, SB + 1020, 100)
glyph("OE", 0x152, 1020, OE)
def AE(p):
    xs = SB + 470; hw = hw_for(lambda h: xs + 50 - h / 2 - SB - h / 2, CAP)
    rect(p, xs, 0, xs + 100, CAP); diag(p, 0, SB + hw / 2, CAP, xs + 50, hw); rect(p, SB + 160, 190, xs, 290)
    rect(p, xs, 600, SB + 1000, 700); rect(p, xs, 300, SB + 940, 400); rect(p, xs, 0, SB + 1000, 100)
glyph("AE", 0xC6, 1000, AE)
SZ_STYLE = "hook"   # "open" (plain), "curl" (lower bowl curls back toward the stem, like the e/s/c terminals), "hook" (upper part is an open f-like hook + curl)
def germandbls(p):
    """Eszett: stem, upper loop, larger lower bowl. SZ_STYLE sets how the lower bowl ends (never closes, so it can't read as a B)."""
    ct, cb = SB + 190, SB + 235
    St = S * 0.9                                                    # loops carry slightly less weight than the stem so the counters stay open
    stem(p, SB, 0, 560); band(p, ct, 560, 190, 190 - St, -90 if SZ_STYLE != "hook" else 0, 180)
    if SZ_STYLE == "hook":
        rect(p, SB + 380 - St, 450, SB + 380, 560)      # open right side of the hook, ends flat
    else:
        rect(p, SB + S, 370, ct, 370 + S)
    band(p, cb, 235, 235, 235 - St, -90 if SZ_STYLE == "open" else -150, 90)
glyph("germandbls", 0xDF, 470, germandbls)

# ---- Spanish and other punctuation / currency ----
glyph("exclamdown", 0xA1, W_D, lambda p: (lambda q: (rect(q, SB + DR - S / 2, 2 * DR + 80, SB + DR + S / 2, CAP), per_dot(q, SB + DR, DR)))(TransformPen(p, (-1, 0, 0, -1, 2 * (SB + DR), CAP))))
glyph("questiondown", 0xBF, 400, lambda p: question(TransformPen(p, (-1, 0, 0, -1, 2 * (SB + 200), CAP))))
def guil(p, flip=False):
    pts = [(SB + 120, 450), (SB + 10, 320), (SB + 120, 190)]; pts2 = [(x + 140, y) for x, y in pts]
    if flip: pts, pts2 = [(2 * SB + 260 - x, y) for x, y in pts], [(2 * SB + 260 - x, y) for x, y in pts2]
    polyline_stroke(p, pts, 0.7 * S); polyline_stroke(p, pts2, 0.7 * S)
glyph("guillemotleft", 0xAB, 260, guil)
glyph("guillemotright", 0xBB, 260, lambda p: guil(p, True))
def euro(p):
    q = TransformPen(p, (1, 0, 0, 1, 30, 0)); band(q, SB + 350, 350, 350, 350 - S, 40, 320)
    rect(q, SB - 30, 270 - S / 2, SB + 420, 270 + S / 2); rect(q, SB - 30, 430 - S / 2, SB + 420, 430 + S / 2)
glyph("Euro", 0x20AC, 700, euro)
def sterling(p):
    band(p, SB + 260, 500, 200, 200 - S, 0, 180); rect(p, SB + 60, S, SB + 60 + S, 500); rect(p, SB, 0, SB + 460, S); rect(p, SB, 290, SB + 300, 290 + S * 0.9)
glyph("sterling", 0xA3, 460, sterling)
def yen(p): Y(p); cx = SB + 320; rect(p, cx - 120, 170 - S / 2, cx + 120, 170 + S / 2); rect(p, cx - 120, 320 - S / 2, cx + 120, 320 + S / 2)
glyph("yen", 0xA5, 640, yen)
glyph("degree", 0xB0, 200, lambda p: ring(p, SB + 100, 600, 100, max(100 - S * 0.6, 28)))
def ordinal(p, which):
    sc = 0.55; q = TransformPen(p, (sc, 0, 0, sc, SB * (1 - sc) + 0, 330))
    (lc_a if which == "a" else lambda r: bowl(r))(q); rect(p, SB, 330 - S * 0.3, SB + 280, 330 + S * 0.3)
glyph("ordfeminine", 0xAA, 280, lambda p: ordinal(p, "a"))
glyph("ordmasculine", 0xBA, 280, lambda p: ordinal(p, "o"))

# ---- Accessibility: "Clear forms" alternates (ss02) for the look-alikes ----
def l_tail(p): stem(p, SB, 150, ASC); band(p, SB + 150, 150, 150, 50, 180, 300)
glyph("l.ss02", None, 225, l_tail)
glyph("I.ss02", None, 220, lambda p: (rect(p, SB + 60, 0, SB + 160, CAP), rect(p, SB, 0, SB + 220, S), rect(p, SB, CAP - S, SB + 220, CAP)))
glyph("zero.ss02", None, 440, lambda p: (zero(p), line_quad(p, SB + 110, 170, SB + 330, 530, 60)))
glyph("b.ss02", None, 550, lambda p: (lambda q: (lc_b(q), rect(q, SB - 50, 0, SB + 100, 60)))(TransformPen(p, (1, 0, 0, 1, 50, 0))))
glyph("d.ss02", None, 550, lambda p: (lc_d(p), rect(p, SB + 400, ASC - 60, SB + 550, ASC)))
glyph("p.ss02", None, 550, lambda p: (lambda q: (lc_p(q), rect(q, SB - 50, XH - 60, SB + 100, XH)))(TransformPen(p, (1, 0, 0, 1, 50, 0))))
glyph("q.ss02", None, 550, lambda p: (lc_q(p), rect(p, SB + 400, DESC, SB + 550, DESC + 60)))
SS02_SUBS = ["l", "I", "zero", "b", "d", "p", "q"]
SPNEW = {"dotlessi": (90, 90), "dotlessi.ss01": (90, 90), "lslash": (60, 60), "Lslash": (60, 40), "dcroat": (60, 80), "Dcroat": (50, 60),
         "oslash": (55, 55), "Oslash": (55, 55), "ae": (55, 50), "oe": (55, 50), "OE": (55, 50), "AE": (30, 50), "germandbls": (90, 60),
         "exclamdown": (80, 80), "questiondown": (60, 60), "guillemotleft": (40, 40), "guillemotright": (40, 40), "Euro": (40, 40),
         "sterling": (40, 40), "yen": (30, 30), "degree": (60, 60), "ordfeminine": (30, 30), "ordmasculine": (30, 30),
         "A.inner": (30, 30), "A.inner.plain": (30, 30), "l.ss02": (90, 60), "I.ss02": (90, 90), "zero.ss02": (70, 70),
         "b.ss02": (90, 60), "d.ss02": (60, 90), "p.ss02": (90, 60), "q.ss02": (60, 90)}

# ---- Spacing: (left, right) sidebearings per glyph; anything not listed uses SB on both sides ----
SP = {
    # capitals: straights loose, rounds tighter, diagonals tightest
    "A": (30, 30), "B": (90, 60), "C": (60, 40), "D": (90, 60), "E": (90, 50), "F": (90, 30), "G": (60, 70), "H": (90, 90),
    "I": (90, 90), "J": (30, 80), "K": (90, 20), "L": (90, 30), "M": (90, 90), "N": (90, 90), "O": (55, 55), "P": (90, 50),
    "Q": (55, 55), "R": (90, 50), "S": (50, 50), "T": (30, 30), "U": (80, 80), "V": (20, 20), "W": (20, 20), "X": (30, 30),
    "Y": (20, 20), "Z": (50, 50),
    # lowercase
    "a": (60, 80), "b": (90, 60), "c": (60, 40), "d": (60, 90), "e": (60, 60), "f": (30, 20), "g": (60, 90), "h": (90, 90),
    "i": (90, 90), "j": (20, 90), "k": (90, 20), "l": (90, 90), "m": (90, 90), "n": (90, 90), "o": (55, 55), "p": (90, 60),
    "q": (60, 90), "r": (90, 10), "s": (40, 40), "t": (30, 40), "u": (90, 90), "v": (20, 20), "w": (20, 20), "x": (30, 30),
    "y": (20, 20), "z": (50, 50),
    # digits
    "zero": (70, 70), "one": (40, 90), "two": (60, 60), "three": (50, 50), "four": (30, 60), "five": (60, 50),
    "six": (60, 60), "seven": (40, 50), "eight": (50, 50), "nine": (60, 60),
    # punctuation
    "period": (70, 70), "comma": (60, 60), "colon": (70, 70), "semicolon": (60, 60), "exclam": (80, 80), "question": (60, 60),
    "quotesingle": (70, 70), "quotedbl": (70, 70), "quoteleft": (60, 60), "quoteright": (60, 60), "quotedblleft": (60, 60),
    "quotedblright": (60, 60), "hyphen": (60, 60), "endash": (40, 40), "emdash": (40, 40), "parenleft": (60, 40),
    "parenright": (40, 60), "bracketleft": (60, 40), "bracketright": (40, 60), "slash": (10, 10), "backslash": (10, 10),
    "plus": (60, 60), "equal": (60, 60), "underscore": (0, 0),
    "asciitilde": (50, 50), "percent": (40, 40), "dollar": (50, 50), "numbersign": (40, 40), "asterisk": (60, 60), "at": (50, 50),
    "less": (60, 60), "greater": (60, 60), "bar": (90, 90), "asciicircum": (60, 60), "bullet": (60, 60),
}

# ---- Kerning (first, second): units; negative = tighter. Draft values to tune by eye ----
def _pairs(first, seconds, v): return {(f, c): v for f in first for c in seconds}
KERN = {}
for f, c, v in [
    (["A"], ["T"], -70), (["A"], ["V", "Y"], -60), (["A"], ["W"], -50), (["A"], ["v", "w", "y"], -30), (["A"], ["quoteright", "quotedblright"], -60),
    (["L"], ["T", "Y"], -90), (["L"], ["V"], -70), (["L"], ["W"], -60), (["L"], ["y"], -40), (["L"], ["quoteright", "quotedblright"], -80),
    (["P", "F"], ["A"], -60), (["P", "F"], ["comma", "period"], -70),
    (["T"], ["A"], -60), (["T"], ["O"], -20), (["T"], ["a", "e", "o", "c"], -60), (["T"], ["r", "u"], -40), (["T"], ["w", "y", "s"], -50),
    (["T"], ["comma", "period", "hyphen"], -60),
    (["V"], ["A"], -50), (["V"], ["a", "e", "o"], -40), (["V"], ["comma", "period"], -60),
    (["W"], ["A"], -40), (["W"], ["a", "e", "o"], -30), (["W"], ["comma", "period"], -50),
    (["Y"], ["A"], -60), (["Y"], ["a", "e", "o"], -60), (["Y"], ["u"], -50), (["Y"], ["comma", "period"], -80),
    (["R"], ["T", "V", "Y"], -25),
    (["r"], ["comma", "period"], -50), (["r"], ["a", "o", "e"], -20),
    (["v", "w", "y"], ["a", "e", "o"], -20), (["v", "w", "y"], ["comma", "period"], -50),
    (["f"], ["i", "j"], 20),                      # the longer f hook would touch the i / j dot
    (["seven"], ["comma", "period"], -60), (["one"], ["one"], -30),
    (["quoteleft", "quotedblleft"], ["A"], -50),
]:
    KERN.update(_pairs(f, c, v))

SP.update(SPNEW)

# ---- Write UFO ----
class Gl_:
    def __init__(self, w, u): self.width, self.unicodes = w, ([u] if u else [])

CHARS = ("ÀÁÂÃÄÅÇÈÉÊËÌÍÎÏÑÒÓÔÕÖÙÚÛÜÝàáâãäåçèéêëìíîïñòóôõöùúûüýÿ"
         "ĀāĂăĄąĆćČčĎďĒēĖėĘęĚěĞğĪīĮįİĹĺĽľŃńŇňŌōŐőŔŕŘřŚśŞşŠšŢţŤťŪūŮůŰűŲųŴŵŶŷŸŹźŻżŽžȘșȚț")
ASC_DY = {"d": 250, "l": 250, "t": 150, "b": 250, "h": 250, "k": 250, "f": 250}
SS01_BASE = {"A.inner": "A.inner.plain", "I": "I.ss01", "W": "W.ss01", "Z": "Z.ss01", "w": "w.ss01", "dotlessi": "dotlessi.ss01"}

def spacing(name):
    l, r = SP.get(name, SP.get(name.split(".")[0], (SB, SB))); ink = G[name][1] - 2 * SB
    l, r = l + PAD, r + PAD
    return l, ink, l + ink + r

def build_composites():
    """Accented letters as components: base glyph + accent marks, so spacing and kerning follow the base letter."""
    comps, fam = {}, {}
    for ch in CHARS:
        d = unicodedata.normalize("NFD", ch); letter = d[0]
        try: marks = [COMBINING[ord(c)] for c in d[1:]]
        except KeyError: continue
        top = any(m not in BELOW for m in marks)
        base = "dotlessi" if (letter == "i" and top) else "A.inner" if letter == "A" else letter
        name = "uni%04X" % ord(ch)
        variants = [(name, ord(ch), base)]
        if base in SS01_BASE: variants.append((name + ".ss01", None, SS01_BASE[base]))
        for nm, uni, b in variants:
            l, ink, adv = spacing(b)
            dy = CAP_LIFT if letter.isupper() else ASC_DY.get(letter, 0)
            ax = l + ink / 2
            parts = [(b, (1, 0, 0, 1, 0, 0))]
            for mk in marks:
                x = l + ink - 55 if mk == "ogonek" else (l + 50 if letter == "L" else ax)
                mkn = mk + ".lc" if (LCS != 100 and mk not in BELOW) else mk
                parts.append((mkn, (1, 0, 0, 1, x - MC, 0 if mk in BELOW else dy)))
            comps[nm] = (uni, adv, parts)
        fam.setdefault(letter, []).append(name)
    return comps, fam

class _CompDraw:
    def __init__(self, parts): self.parts = parts
    def __call__(self, pp):
        for b, t in self.parts: pp.addComponent(b, t)

def _is_lower(name):
    base = name.split(".")[0]; u = G[base][0] if base in G else None
    return bool(u) and chr(u).isalpha() and chr(u).islower()

def _with_stroke(draw, stroke):
    def d(p):
        global S
        old, S = S, stroke
        try: draw(p)
        finally: S = old
    return d

def main():
    if LCS != 100:                                      # Bold: every glyph is drawn with the heavier stroke
        for n in list(G):
            if not n.endswith(".lc"): G[n] = (G[n][0], G[n][1], _with_stroke(G[n][2], LCS))
    shutil.rmtree(OUT, ignore_errors=True)
    w = UFOWriter(OUT, formatVersion=3)
    info = type("I", (), dict(familyName="Ise Grotesk", styleName=STYLE, italicAngle=-SLANT,
                              styleMapFamilyName="Ise Grotesk", styleMapStyleName={"Regular": "regular", "Italic": "italic", "Bold": "bold", "Bold Italic": "bold italic"}[STYLE],
                              openTypeOS2WeightClass=700 if "Bold" in STYLE else 400, unitsPerEm=UPM, ascender=1000, descender=-300,
                              capHeight=CAP, xHeight=XH, versionMajor=0, versionMinor=100,
                              openTypeHheaAscender=1000, openTypeHheaDescender=-300, openTypeHheaLineGap=0,
                              openTypeOS2TypoAscender=1000, openTypeOS2TypoDescender=-300, openTypeOS2TypoLineGap=0,
                              openTypeOS2WinAscent=1100, openTypeOS2WinDescent=300, openTypeOS2Selection=[7],
                              copyright="Copyright 2026 The Ise Grotesk Project Authors (https://github.com/katejtownsend/ise-grotesk)",
                              openTypeNameDesigner="Kate Townsend", openTypeNameDesignerURL="https://github.com/katejtownsend",
                              openTypeNameLicense="This Font Software is licensed under the SIL Open Font License, Version 1.1. This license is available with a FAQ at: https://openfontlicense.org",
                              openTypeNameLicenseURL="https://openfontlicense.org",
                              openTypeNameDescription="Ise Grotesk: a Bauhaus-inspired geometric sans, named for Ise Gropius. For the un-sung women in design."))()
    w.writeInfo(info)
    gs = w.getGlyphSet()
    for name, (uni, adv, draw) in G.items():
        l, r = SP.get(name, SP.get(name.split(".")[0], (SB, SB))); ink = adv - 2 * SB; l, r = l + PAD, r + PAD
        k = math.tan(math.radians(SLANT))
        gs.writeGlyph(name, Gl_(l + ink + r, uni),
                      lambda pp, d=draw, dx=l - SB: d(TransformPen(SegmentToPointPen(pp), (1, 0, k, 1, dx, 0))))
    comps, fam = build_composites()
    for name, (uni, adv, parts) in comps.items():
        k = math.tan(math.radians(SLANT))
        parts = [(b, (a, b_, c, d_, e + k * f, f)) for b, (a, b_, c, d_, e, f) in parts]      # keep marks on the slant
        gs.writeGlyph(name, Gl_(adv, uni), _CompDraw(parts))
    gs.writeContents(); w.writeLayerContents()
    allnames = set(G) | set(comps)
    def family(g): return [g] + fam.get(g, [])
    kern = {}
    for (f, c), v in KERN.items():
        for f2 in family(f):
            for c2 in family(c): kern[(f2, c2)] = round(v * KSCALE)
    w.writeKerning({k: v for k, v in kern.items() if k[0] in allnames and k[1] in allnames})
    subs1 = [f"sub {a} by {a}.ss01;" for a in ["A", "H", "I", "W", "Z", "five", "i", "w"]] + \
            [f"sub {n[:-5]} by {n};" for n in comps if n.endswith(".ss01")]
    subs2 = [f"sub {a} by {a}.ss02;" for a in SS02_SUBS]
    feat = ("languagesystem DFLT dflt;\nlanguagesystem latn dflt;\n\n"
            "feature ss01 {\n    featureNames { name \"Logic: plain forms of the whimsy letters\"; };\n    " + "\n    ".join(subs1) + "\n} ss01;\n\n"
            "feature ss02 {\n    featureNames { name \"Clear: distinct forms for look-alike letters\"; };\n    " + "\n    ".join(subs2) + "\n} ss02;\n")
    w.writeFeatures(feat)
    print(f"wrote {OUT}: {len(G)} drawn glyphs + {len(comps)} composites, {len(kern)} kerning pairs")

if __name__ == "__main__":
    main()
