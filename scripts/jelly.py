"""Script-free jelly art and native disclosure controls for the GitHub profile."""
import json
import math
from html import escape
from pathlib import Path

AMBER = '#efb96d'
DARK = '#171612'
DEMO_URL = 'https://jaikhuranna.github.io/jaikhuranna/jelly/'


def mesh(width, height, top, bottom, seed=0):
    """Equal-topology paths let SVG interpolate a soft, travelling deformation."""
    paths = []
    for row in range(13):
        frames = []
        for phase in range(7):
            t = phase / 6 * math.tau
            coords = []
            for col in range(37):
                x = col * width / 36
                y = top + row * (bottom - top) / 12
                envelope = math.sin(col / 36 * math.pi) * math.sin(row / 12 * math.pi)
                dx = math.sin(x / 100 + t + seed) * 17 * envelope
                dy = math.sin(x / 80 - t + row * .22 + seed) * 17 * envelope
                coords.append(f'{x + dx:.1f},{y + dy:.1f}')
            frames.append('M' + ' L'.join(coords))
        paths.append(f'<path d="{frames[0]}" fill="none" stroke="{AMBER}" stroke-opacity="{.26 + row % 3 * .13:.2f}" stroke-width=".8"><animate attributeName="d" dur="7s" values="{";".join(frames)}" repeatCount="indefinite"/></path>')
    return '<g class="mesh">' + ''.join(paths) + '</g>'


def image(width, height, body):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">
<style>text{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}}.soft{{font-family:Arial,Helvetica,sans-serif}}.still{{display:none}}@media(prefers-reduced-motion:reduce){{.motion,.mesh{{display:none}}.still{{display:inline}}}}</style>
<rect width="{width}" height="{height}" rx="18" fill="{DARK}"/>{body}</svg>\n'''


def hero(phone=False):
    w, h = (480, 430) if phone else (960, 390)
    size = 47 if phone else 84
    left = 28 if phone else 44
    title_y = 170 if phone else 168
    sub_y = title_y + size * 1.06
    end = h - 78
    body = f'''<defs>
<linearGradient id="gel" x2=".2" y2="1"><stop stop-color="#553a20"/><stop offset=".48" stop-color="#a87534"/><stop offset="1" stop-color="#50391f"/></linearGradient>
<radialGradient id="clear"><stop offset=".65" stop-color="black"/><stop offset="1" stop-color="white"/></radialGradient>
<mask id="window"><rect width="{w}" height="{h}" fill="white"/><ellipse class="still" cx="{w*.45}" cy="{title_y}" rx="{w*.65}" ry="160" fill="black"/><ellipse class="motion" cx="{w*.3}" cy="{title_y}" rx="{w*.25}" ry="110" fill="url(#clear)"><animate attributeName="cx" values="{w*.2};{w*.75};{w*.4};{w*.2}" dur="10s" repeatCount="indefinite"/><animate attributeName="cy" values="{title_y};{sub_y};{title_y};{title_y}" dur="10s" repeatCount="indefinite"/></ellipse></mask></defs>
<text x="{left}" y="37" fill="#f3e9d9" font-size="14" letter-spacing="2">JAI KHURANA</text>
<text x="{w-left}" y="37" fill="{AMBER}" text-anchor="end" font-size="11">JELLY / 03</text>
<text class="soft" x="{left}" y="{title_y}" fill="#fff2dc" font-size="{size}" font-weight="800" letter-spacing="-2">SOFTWARE.</text>
<text class="soft" x="{left}" y="{sub_y}" fill="#fff2dc" font-size="{size}" font-weight="800" letter-spacing="-2">SOFT SIDE.</text>
<g mask="url(#window)"><rect x="1" y="65" width="{w-2}" height="{end-65}" rx="12" fill="url(#gel)" opacity=".92"/>{mesh(w,h,65,end)}</g>
<text x="{left}" y="{h-47}" fill="#d3c4ac" font-size="{12 if phone else 13}">ENGINEER AT PAYGLOCAL · BENGALURU</text>
<text x="{left}" y="{h-23}" fill="{AMBER}" font-size="{12 if phone else 13}">PRESS, DRAG, FIND THE WORK ↗</text>'''
    return image(w, h, body)


def strip(index, name, phone=False):
    w, h = (480, 90) if phone else (960, 86)
    return image(w, h, f'''{mesh(w,h,3,h-3,index*.65)}
<rect x="16" y="20" width="{min(330,w-110)}" height="47" rx="10" fill="{DARK}" fill-opacity=".88"/>
<text x="28" y="49" fill="{AMBER}" font-size="14">0{index+1}</text>
<text x="69" y="49" fill="#f4e8d6" font-size="{18 if phone else 20}">{escape(name)}</text>
<rect x="{w-93}" y="24" width="69" height="38" rx="19" fill="{AMBER}"/>
<text x="{w-58}" y="48" fill="{DARK}" font-size="20" text-anchor="middle">＋</text>''')


def files(names):
    out = {'jelly.svg': hero(True), 'd-jelly.svg': hero(False)}
    for i, name in enumerate(names):
        out[f'jelly-{i+1}.svg'] = strip(i, name, True)
        out[f'd-jelly-{i+1}.svg'] = strip(i, name, False)
    return out


def readme(data, art, projects, socials, pic):
    sections = []
    for i, (name, desc) in enumerate(projects.items()):
        info = data['projects'].get(name, {})
        sections.append(f'''<details>
<summary>{pic(f"jelly-{i+1}.svg", f"Click to uncover {name}", "100%", art)}</summary>

### [{name}](https://github.com/jaikhuranna/{name})

{desc or info.get('desc') or ''}

[{info.get('lang') or 'Source'} · Explore the repository ↗](https://github.com/jaikhuranna/{name})

</details>''')
    stats = f"{data.get('total',0):,} contributions in the last year · {data['repos']} repos · {data['followers']} followers · {data['stars']} stars"
    return f'''<!-- generated by scripts/build.py; edit scripts/jelly.py for the layout -->
<a href="{DEMO_URL}">{pic('jelly.svg', 'Jai Khurana. Software, with a soft side. Open the interactive jelly.', '100%', art)}</a>

Click a jelly strip to uncover the work. **[Drag and poke the jelly ↗]({DEMO_URL})**

{chr(10).join(sections)}

<details>
<summary>The activity underneath</summary>

{pic('activity.svg', stats, '100%', art)}

</details>

**Go · Kotlin · Swift · TypeScript · SQL**<br>
Software engineer at PayGlocal, Bengaluru.

{' · '.join(f'[{name}]({url})' for name, url in socials)}
'''


def write_demo(root, data, projects):
    dest = Path(root) / 'docs/jelly/content.json'
    dest.parent.mkdir(parents=True, exist_ok=True)
    content = {'name': 'Jai Khurana', 'role': 'Software engineer at PayGlocal', 'place': 'Bengaluru',
               'projects': [{'name': name, 'description': desc or data['projects'].get(name,{}).get('desc') or '',
                             'language': data['projects'].get(name,{}).get('lang') or '',
                             'url': f'https://github.com/jaikhuranna/{name}'} for name,desc in projects.items()]}
    dest.write_text(json.dumps(content, indent=2) + '\n')
