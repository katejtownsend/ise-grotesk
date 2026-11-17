# Ise Grotesk

Four styles: Regular, Italic, Bold and Bold Italic. A display typeface, best at larger sizes.

## What is in the download

- `ttf/` and `otf/`: the fonts to install on a computer (hinted, for Windows and Mac apps).
- `web/`: the files for websites. Unhinted WOFF2 (smaller), plus `ise-grotesk.css` with the `@font-face` rules and a size-matched fallback font so pages do not jump while the font loads.
- `woff2/`: the same WOFF2 files made from the hinted fonts (larger; kept for compatibility). Prefer `web/` for new sites.

## Install on a computer

**Mac:** select all four `.ttf` files, right-click, Open, then click Install Font. (If an older Ise Grotesk is installed, remove it in Font Book first.)

**Windows:** select all four, right-click, Install.

## Use on a website

Copy the files from `web/` to your site and link `ise-grotesk.css`. Then set `font-family: "Ise Grotesk", "Ise Fallback", system-ui, sans-serif;`.

## Stylistic sets

- `ss01` "Logic": plain forms of the story letters.
- `ss02` "Clear": distinct forms for look-alike letters (I, l, 0, b, d, p, q).

In Figma: Text, Typography, Details, OpenType features. In Adobe apps: OpenType panel, Stylistic Sets. In CSS: `font-feature-settings: "ss01"` (or `"ss02"`, or both).

## Licence

SIL Open Font License 1.1, with the Reserved Font Name "Ise Grotesk". See `OFL.txt`.
