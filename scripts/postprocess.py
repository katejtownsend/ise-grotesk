"""Release post-processing for compiled fonts: adds a STAT table (one entry per axis, this font's own style), removes Mac name
records, sets the head 'integer ppem' flag required for hinted fonts, sets fsType to 0 (installable) and a real vendor ID.
python scripts/postprocess.py font.ttf [font2.otf ...]   (fixes Font Bakery: no-stat, STAT_in_statics, no_mac_entries, integer_ppem_if_hinted)"""
import os, sys
from fontTools.ttLib import TTFont
from fontTools.otlLib.builder import buildStatTable

def axes_for(name):
    bold, italic = "Bold" in name, "Italic" in name
    wght = dict(value=700, name="Bold") if bold else dict(value=400, name="Regular", flags=0x2, linkedValue=700)
    ital = dict(value=1, name="Italic") if italic else dict(value=0, name="Upright", flags=0x2, linkedValue=1)
    return [dict(tag="wght", name="Weight", ordering=0, values=[wght]), dict(tag="ital", name="Italic", ordering=1, values=[ital])]

for path in sys.argv[1:]:
    f = TTFont(path)
    if "STAT" in f: del f["STAT"]
    buildStatTable(f, axes_for(os.path.basename(path)), elidedFallbackName=2)    # name ID 2 = the font's subfamily name
    f["name"].names = [n for n in f["name"].names if n.platformID != 1]          # drop Mac (platform 1) name records
    if "glyf" in f: f["head"].flags |= 0x8                                       # bit 3: force integer ppem (hinted fonts)
    os2 = f["OS/2"]
    os2.fsType = 0                                                               # installable embedding (OFL allows free embedding)
    if os2.achVendID.strip() in ("", "NONE"): os2.achVendID = "KTWN"             # project vendor ID instead of 'NONE'
    for n in f["name"].names:
        if n.nameID == 3 and ";NONE;" in str(n): n.string = str(n).replace(";NONE;", ";KTWN;")   # unique font ID carries the vendor ID
    f.save(path); print("post-processed", path)
