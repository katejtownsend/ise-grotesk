"""Render a proof PNG of a built TTF: python scripts/proof.py fonts/IseGrotesk-Bold.ttf out.png [size]"""
import sys
from PIL import Image, ImageDraw, ImageFont
f, out = sys.argv[1], sys.argv[2]; size = int(sys.argv[3]) if len(sys.argv) > 3 else 110
fo = ImageFont.truetype(f, size)
lines = ["ABCDEFGHIJKLM", "NOPQRSTUVWXYZ", "abcdefghijklm", "nopqrstuvwxyz", "0123456789 &@%$#", "ÀÁÂÃÄÅ Çñ ßæœø !?.,:;()[]{}"]
im = Image.new("RGB", (2000, int(size * 1.55) * len(lines) + 40), "white"); d = ImageDraw.Draw(im)
for i, t in enumerate(lines): d.text((30, 20 + i * int(size * 1.55)), t, font=fo, fill="black")
im.save(out)
