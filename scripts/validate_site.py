"""Local consistency checks for the static site."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
import json,re,sys,xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
errors=[]

class Checker(HTMLParser):
    def __init__(self,path): super().__init__(convert_charrefs=True); self.path=path; self.refs=[]; self.scripts=[]; self.in_json=False
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag in ('a','link') and a.get('href'): self.refs.append(a['href'])
        if tag in ('img','script') and a.get('src'): self.refs.append(a['src'])
        if tag=='script' and a.get('type')=='application/ld+json': self.in_json=True; self.scripts.append('')
    def handle_endtag(self,tag):
        if tag=='script': self.in_json=False
    def handle_data(self,data):
        if self.in_json: self.scripts[-1]+=data

htmls=sorted(ROOT.rglob('*.html'))
for p in htmls:
    raw=p.read_text(encoding='utf-8'); c=Checker(p)
    try: c.feed(raw); c.close()
    except Exception as e: errors.append(f'{p}: HTML parse: {e}')
    for data in c.scripts:
        try: json.loads(data)
        except Exception as e: errors.append(f'{p}: JSON-LD: {e}')
    public=re.sub(r'<!--.*?-->','',raw,flags=re.S)
    if re.search(r'href\s*=\s*["\']#["\']',public): errors.append(f'{p}: public href="#"')
    if re.search(r'(?:価格|料金|標高|コースタイム)[^<。]{0,30}\d',re.sub(r'<[^>]+>','',public)):
        errors.append(f'{p}: changing numeric fact near restricted term')
    for ref in c.refs:
        u=urlparse(ref)
        if u.scheme or ref.startswith(('#','mailto:','tel:')): continue
        target=(p.parent/u.path).resolve()
        if not target.exists(): errors.append(f'{p}: missing {ref}')

ns={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}
tree=ET.parse(ROOT/'sitemap.xml')
listed={urlparse(n.text).path[len('/yama-hajime/'):].rstrip('/') if urlparse(n.text).path.startswith('/yama-hajime/') else urlparse(n.text).path.rstrip('/') for n in tree.findall('.//s:loc',ns)}
expected={'','about.html','privacy.html','articles/mountain-hiking-start.html','articles/trekking-start.html','articles/swimming-start.html','articles/fuji-climbing.html','articles/fuji-climbing-gear.html','en','en/fuji-climbing.html','en/fuji-climbing-gear.html'}
if listed!=expected: errors.append(f'sitemap mismatch: {listed ^ expected}')

for p in sorted((ROOT/'articles').glob('*.html')):
    public=re.sub(r'<!--.*?-->','',p.read_text(encoding='utf-8'),flags=re.S)
    text=re.sub(r'<[^>]+>','',public)
    print(f'{p.relative_to(ROOT)}: visible text {len("".join(text.split()))} chars')
if errors:
    print('\n'.join('ERROR '+e for e in errors)); sys.exit(1)
print(f'OK: parsed {len(htmls)} HTML files; JSON-LD, local refs, public placeholders, numeric-fact scan and sitemap passed')
