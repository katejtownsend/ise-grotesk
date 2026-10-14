"""Hint a TTF with ttfautohint (via the ttfautohint-py package, which has no command-line tool of its own).
python scripts/hint.py in.ttf out.ttf"""
import shutil, sys
from ttfautohint import ttfautohint
src, dst = sys.argv[1], sys.argv[2]
try:
    ttfautohint(in_file=src, out_file=dst)                              # default settings
    print("hinted", dst)
except Exception as e:                                              # never lose a build because hinting failed
    print("hinting failed, copying unhinted:", e); shutil.copy(src, dst)
