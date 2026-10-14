"""Build docs/glyph-viewer.html: every character in every style, with ss01/ss02 toggles. Fonts are embedded, so the file works offline.
python scripts/make_viewer.py   (run ./build_all.sh first)"""
import base64, json, os, unicodedata
from fontTools.ttLib import TTFont
STYLES = [("Regular", "IseGrotesk-Regular", 400, "normal"), ("Italic", "IseGrotesk-Italic", 400, "italic"),
          ("Bold", "IseGrotesk-Bold", 700, "normal"), ("Bold Italic", "IseGrotesk-BoldItalic", 700, "italic")]
f = TTFont(os.environ.get("ISE_FONTDIR","fonts")+"/IseGrotesk-Regular.ttf"); cmap = f.getBestCmap()
def group(u):
    c = chr(u); cat = unicodedata.category(c)
    if c.isalpha() and u < 0x80: return "Uppercase" if c.isupper() else "Lowercase"
    if cat == "Nd": return "Digits"
    if c.isalpha(): return "Accented capitals" if c.isupper() else "Accented lowercase"
    if u in (0x20,): return "Space"
    return "Punctuation and symbols"
order = ["Uppercase", "Lowercase", "Digits", "Punctuation and symbols", "Accented capitals", "Accented lowercase"]
groups = {k: [] for k in order}
for u in sorted(cmap):
    g = group(u)
    if g in groups: groups[g].append([u, unicodedata.name(chr(u), cmap[u])])
faces = "".join(f"@font-face{{font-family:'Ise';src:url(data:font/ttf;base64,{base64.b64encode(open(os.environ.get('ISE_FONTDIR','fonts')+f'/{fn}.ttf','rb').read()).decode()}) format('truetype');font-weight:{w};font-style:{st}}}\n" for _, fn, w, st in STYLES)
html = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Ise Grotesk glyph viewer</title><style>
%FACES%
:root{--bg:#fff;--fg:#111;--mut:#777;--line:#ddd;--acc:#d3342c}
@media(prefers-color-scheme:dark){:root{--bg:#141414;--fg:#f2f2f2;--mut:#999;--line:#333}}
body{margin:0;background:var(--bg);color:var(--fg);font:14px system-ui,sans-serif}
header{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--line);padding:12px 20px;display:flex;flex-wrap:wrap;gap:14px;align-items:center;z-index:2}
h1{font-size:16px;margin:0 8px 0 0}
button,label,input{font:inherit}
.seg button{padding:6px 12px;border:1px solid var(--line);background:none;color:var(--fg);cursor:pointer}
.seg button.on{background:var(--fg);color:var(--bg)}
main{padding:16px 20px 80px}
h2{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--mut);margin:28px 0 8px;font-weight:600}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(var(--cell,96px),1fr));gap:1px;background:var(--line);border:1px solid var(--line)}
.c{background:var(--bg);aspect-ratio:1;display:flex;flex-direction:column;align-items:center;justify-content:center;cursor:pointer;position:relative;overflow:hidden}
.c:hover{outline:2px solid var(--acc);z-index:1}
.c b{font:var(--fs,44px)/1 'Ise';font-weight:var(--w);font-style:var(--st);font-feature-settings:var(--ff)}
.c i{position:absolute;bottom:3px;font:10px system-ui;color:var(--mut);font-style:normal}
#big{position:fixed;inset:0;background:color-mix(in srgb,var(--bg) 94%,transparent);display:none;flex-direction:column;align-items:center;justify-content:center;z-index:5;cursor:pointer}
#big .g{font:300px/1 'Ise';font-weight:var(--w);font-style:var(--st);font-feature-settings:var(--ff);padding:0 40px;max-width:100%;overflow:hidden;position:relative}
#big .g.guide{background:linear-gradient(transparent 0,transparent 100%)}
#big p{color:var(--mut);margin:10px 0 0}
textarea{width:100%;box-sizing:border-box;font:56px/1.2 'Ise';font-weight:var(--w);font-style:var(--st);font-feature-settings:var(--ff);border:1px solid var(--line);background:var(--bg);color:var(--fg);padding:12px;height:150px}
.note{color:var(--mut);max-width:60ch}
@media(max-width:600px){header{padding:10px 16px}main{padding:12px 16px 80px}}
</style></head><body>
<header><h1>Ise Grotesk</h1>
<span class="seg" id="styles"></span>
<label><input type="checkbox" id="ss01"> ss01 Logic</label>
<label><input type="checkbox" id="ss02"> ss02 Clear</label>
<label>Size <input type="range" id="size" min="24" max="90" value="44"></label>
<input id="find" placeholder="Jump to a character, e.g. f" size="22"></header>
<main><p class="note">Every character in the font. Click one to see it large. Turn on ss01 to see the plain forms of the whimsy letters, ss02 for the look-alike fixes (l, I, 0, b, d, p, q). Draft fonts: the glyph set grows as we build.</p>
<h2>Try your own text</h2><textarea id="try">Ise Grotesk: Walter und Ise, Größe, ¿Qué?</textarea><div id="out"></div></main>
<div id="big"><div class="g" id="bg"></div><p id="bi"></p></div>
<script>
const STYLES=%STYLES%,GROUPS=%GROUPS%,order=%ORDER%;
const root=document.documentElement; let cur=0;
function apply(){const s=STYLES[cur];root.style.setProperty('--w',s[2]);root.style.setProperty('--st',s[3]);
 const ff=[];if(ss01.checked)ff.push('"ss01"');if(ss02.checked)ff.push('"ss02"');root.style.setProperty('--ff',ff.join(',')||'normal');
 root.style.setProperty('--fs',size.value+'px');root.style.setProperty('--cell',Math.max(70,size.value*2)+'px');
 [...styles.children].forEach((b,i)=>b.classList.toggle('on',i===cur));}
STYLES.forEach((s,i)=>{const b=document.createElement('button');b.textContent=s[0];b.onclick=()=>{cur=i;apply()};styles.appendChild(b)});
const out=document.getElementById('out');
order.forEach(g=>{if(!GROUPS[g].length)return;const h=document.createElement('h2');h.textContent=g+' ('+GROUPS[g].length+')';out.appendChild(h);
 const d=document.createElement('div');d.className='grid';
 GROUPS[g].forEach(([u,n])=>{const c=document.createElement('div');c.className='c';c.dataset.ch=String.fromCodePoint(u);c.dataset.u=u;
  c.innerHTML='<b></b><i>U+'+u.toString(16).toUpperCase().padStart(4,'0')+'</i>';c.firstChild.textContent=String.fromCodePoint(u);c.title=n;
  c.onclick=()=>{bg.textContent=c.dataset.ch;bi.textContent=n+'  ·  U+'+u.toString(16).toUpperCase().padStart(4,'0');big.style.display='flex'};d.appendChild(c)});out.appendChild(d)});
big.onclick=()=>big.style.display='none';document.onkeydown=e=>{if(e.key==='Escape')big.style.display='none'};
find.oninput=()=>{const q=find.value;if(!q)return;const c=[...document.querySelectorAll('.c')].find(x=>x.dataset.ch===q[0]);if(c){c.scrollIntoView({block:'center'});c.style.outline='3px solid var(--acc)';setTimeout(()=>c.style.outline='',1200)}};
[ss01,ss02,size].forEach(e=>e.oninput=apply);apply();
</script></body></html>"""
html = html.replace("%FACES%", faces).replace("%STYLES%", json.dumps([[s[0], s[1], s[2], s[3]] for s in STYLES])).replace("%GROUPS%", json.dumps(groups)).replace("%ORDER%", json.dumps(order))
open(os.environ.get("ISE_OUT","docs/glyph-viewer.html"), "w").write(html); print("wrote docs/glyph-viewer.html", len(html) // 1024, "KB;", {k: len(v) for k, v in groups.items()})
