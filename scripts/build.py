#!/usr/bin/env python3
"""Builds the profile README: dot-matrix SVGs filled with live GitHub data.

Run locally:   GITHUB_TOKEN=$(gh auth token) python3 scripts/build.py
Runs in CI:    .github/workflows/refresh.yml (every 6 hours)

Edit PROJECTS / ROLE / STACK below to change what the profile shows.
Stdlib only. If the API is unreachable it falls back to assets/data.json.
"""
import json, math, os, random, sys, urllib.request
from datetime import datetime, timezone
from html import escape as e

USER = "jaikhuranna"
NAME = ("JAI", "KHURANA")
ROLE = "SOFTWARE ENGINEER"
WHERE = "PAYGLOCAL · BENGALURU, IN"
STACK = ["GO", "KOTLIN", "SWIFT", "TYPESCRIPT", "SQL"]
SOCIALS = [("LinkedIn", "https://linkedin.com/in/jaikhuranna"),
           ("Instagram", "https://instagram.com/jaikhuranna"),
           ("Twitter", "https://twitter.com/commondumlow")]
# repo name -> description override (None = use the repo's GitHub description)
PROJECTS = {
    "git-huh": "Your GitHub history as printed artefacts",
    "AIusageBar": "Claude usage limits on desktop & wrist",
    "nothing-mtui": "Material You colours on Nothing OS",
    "sitewatch": "Page watcher with Telegram alerts",
}
# never shown as "now building" (private repos and forks are never shown either)
NOT_BUILDING = {USER, "git-huh-sandbox"}

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,'SF Mono','Roboto Mono',Menlo,Consolas,'DejaVu Sans Mono',monospace"
RED = "#ff3b30"
LANG_CODE = {"TypeScript": "TS", "JavaScript": "JS", "Kotlin": "KT", "Swift": "SWIFT", "Go": "GO",
             "Python": "PY", "Java": "JAVA", "C#": "C#", "C++": "C++", "HTML": "HTML", "CSS": "CSS"}


# ------------------------------------------------------------------ data
def api(url, body=None):
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None,
                                 headers={"Accept": "application/vnd.github+json", "User-Agent": "profile-readme-build"})
    if tok:
        req.add_header("Authorization", f"Bearer {tok}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch():
    user = api(f"https://api.github.com/users/{USER}")
    repos = api(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner&sort=pushed")
    own = [r for r in repos if not r["fork"]]
    data = {
        "followers": user["followers"],
        "repos": user["public_repos"],
        "stars": sum(r["stargazers_count"] for r in own),
        "projects": {r["name"]: {"stars": r["stargazers_count"], "lang": r["language"],
                                 "desc": r["description"], "pushed": r["pushed_at"]}
                     for r in own if r["name"] in PROJECTS},
    }
    building = [r for r in own if r["name"] not in NOT_BUILDING]
    building.sort(key=lambda r: r["pushed_at"], reverse=True)
    if building:
        data["building"] = {"name": building[0]["name"], "lang": building[0]["language"]}
    try:
        q = ('query($u:String!){user(login:$u){contributionsCollection{contributionCalendar{'
             'totalContributions weeks{contributionDays{contributionLevel}}}}}}')
        cal = api("https://api.github.com/graphql", {"query": q, "variables": {"u": USER}})
        cal = cal["data"]["user"]["contributionsCollection"]["contributionCalendar"]
        lv = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
        data["total"] = cal["totalContributions"]
        data["weeks"] = [[lv[d["contributionLevel"]] for d in w["contributionDays"]] for w in cal["weeks"]]
    except Exception as ex:  # GraphQL needs a token; keep the old graph if it fails
        print("contributions unavailable:", ex, file=sys.stderr)
    return data


def load():
    cache = os.path.join(ASSETS, "data.json")
    old = json.load(open(cache)) if os.path.exists(cache) else {}
    try:
        new = fetch()
        old.update(new)
    except Exception as ex:
        print("API failed, using cached data:", ex, file=sys.stderr)
        if not old:
            raise
    os.makedirs(ASSETS, exist_ok=True)
    with open(cache, "w") as f:
        json.dump(old, f, indent=1, sort_keys=True)
    return old


def ago(iso):
    d = (datetime.now(timezone.utc) - datetime.fromisoformat(iso.replace("Z", "+00:00"))).days
    if d < 1: return "TODAY", True
    if d < 7: return f"{d}D AGO", True
    if d < 60: return f"{d // 7}W AGO", False
    return f"{d // 30}MO AGO", False


def wrap(text, width, lines=2):
    words, out, cur = (text or "").split(), [], ""
    for w in words:
        if len(cur) + len(w) + (1 if cur else 0) <= width:
            cur = f"{cur} {w}".strip()
        else:
            out.append(cur); cur = w
    out.append(cur)
    if len(out) > lines:
        out = out[:lines]
        out[-1] = out[-1][: width - 1].rstrip() + "…"
    return [l for l in out if l]


# ------------------------------------------------------------------ dot font
FONT = {
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "H": ["#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "I": [".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "J": ["..###", "...#.", "...#.", "...#.", "#..#.", "#..#.", ".##.."],
    "K": ["#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"],
    "N": ["#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"],
    "R": ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
    "U": ["#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "0": [".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."],
    "1": ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "2": [".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"],
    "3": ["####.", "....#", "....#", ".###.", "....#", "....#", "####."],
    "4": ["...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."],
    "5": ["#####", "#....", "####.", "....#", "....#", "#...#", ".###."],
    "6": [".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."],
    "7": ["#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."],
    "8": [".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."],
    "9": [".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."],
}


def dotmap(text):
    col, out = 0, []
    for ch in text:
        if ch == " ":
            col += 4
            continue
        for r, row in enumerate(FONT[ch]):
            out += [(col + c, r) for c, v in enumerate(row) if v == "#"]
        col += 6
    return out, max(col - 1, 0)


def svg(w, h, body, css=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'font-family="{SANS}">\n<style>{css}</style>\n{body}\n</svg>\n')


def panel(W, H, rx, fill="#000"):
    return (f'<rect width="{W}" height="{H}" rx="{rx}" fill="{fill}"/>'
            f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="{rx}" fill="none" stroke="#262626"/>')


BASE_CSS = f""".t{{font-family:{MONO};letter-spacing:2px}}
.rec{{animation:rec 1.2s steps(1) infinite}}
@keyframes rec{{0%{{opacity:1}}50%{{opacity:.15}}}}
"""


# ------------------------------------------------------------------ header
def header(d):
    W, H, P = 480, 360, 10.2
    x0, y0 = (W - 41 * P) / 2 + P / 2, 78
    css = BASE_CSS + f"""
.d{{opacity:0;animation:boot .45s ease-out forwards}}
.s{{opacity:0;animation:sweep 7s linear infinite}}
.seg{{opacity:0;animation:seg 5s ease-in-out infinite}}
@keyframes boot{{0%{{opacity:0}}60%{{opacity:1;fill:{RED}}}100%{{opacity:1}}}}
@keyframes sweep{{0%{{opacity:0}}3%{{opacity:1}}9%{{opacity:0}}100%{{opacity:0}}}}
@keyframes seg{{0%{{opacity:0}}5%{{opacity:1}}62%{{opacity:1}}70%{{opacity:0}}100%{{opacity:0}}}}
"""
    b = [f'<defs><clipPath id="r"><rect width="{W}" height="{H}" rx="30"/></clipPath>'
         f'<pattern id="g" width="{P}" height="{P}" patternUnits="userSpaceOnUse" x="{x0-P/2:.2f}" y="{y0-P/2:.2f}">'
         f'<circle cx="{P/2}" cy="{P/2}" r="1.7" fill="#1e1e1e"/></pattern></defs>',
         f'<g clip-path="url(#r)"><rect width="{W}" height="{H}" fill="#000"/><rect width="{W}" height="{H}" fill="url(#g)"/></g>',
         f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="30" fill="none" stroke="#262626"/>',
         f'<text class="t" x="28" y="38" font-size="12" fill="#8a8a8a">{USER.upper()}</text>',
         f'<text class="t" x="430" y="38" font-size="12" fill="#8a8a8a" text-anchor="end">LIVE</text>',
         f'<circle class="rec" cx="446" cy="34" r="5" fill="{RED}"/>']
    lit, red = [], []
    for li, (txt, roff) in enumerate([(NAME[0], 0), (NAME[1], 9)]):
        pts, _ = dotmap(txt)
        for c, r in pts:
            cx, cy = x0 + c * P, y0 + (r + roff) * P
            lit.append(f'<circle class="d" style="animation-delay:{.3+c*.028+li*.35:.3f}s" cx="{cx:.1f}" cy="{cy:.1f}" r="4"/>')
            red.append(f'<circle class="s" style="animation-delay:{2.6+c*.035:.3f}s" cx="{cx:.1f}" cy="{cy:.1f}" r="4"/>')
    b.append(f'<g fill="#f4f4f4">{"".join(lit)}</g><g fill="{RED}">{"".join(red)}</g>')
    bx, bw = x0 - 4, 41 * P
    b.append(f'<text class="t" x="{bx:.0f}" y="268" font-size="19" font-weight="700" fill="#fff">{e(ROLE)}</text>')
    b.append(f'<text class="t" x="{bx:.0f}" y="292" font-size="13.5" fill="#9a9a9a" letter-spacing="1.5">{e(WHERE)}</text>')
    n = 30
    sw = (bw - (n - 1) * 3) / n
    segs, on = [], []
    for k in range(n):
        x = bx + k * (sw + 3)
        segs.append(f'<rect x="{x:.1f}" y="310" width="{sw:.1f}" height="10" rx="2"/>')
        on.append(f'<rect class="seg" style="animation-delay:{k*.08:.2f}s" x="{x:.1f}" y="310" width="{sw:.1f}" height="10" rx="2"/>')
    b.append(f'<g fill="#222">{"".join(segs)}</g><g fill="#fff">{"".join(on)}</g>')
    bl = d.get("building")
    now = f'{bl["name"].upper()[:16]} / {(bl["lang"] or "").upper()}'.rstrip(" /") if bl else "SOMETHING NEW"
    b.append(f'<text class="t" x="{bx:.0f}" y="343" font-size="12" fill="#8a8a8a">NOW BUILDING</text>')
    b.append(f'<text class="t" x="{bx+bw:.0f}" y="343" font-size="12" fill="#fff" text-anchor="end">{e(now)}</text>')
    return svg(W, H, "\n".join(b), css)


# ------------------------------------------------------------------ activity
def dot_number(s, ox, oy, pitch, r, cls="", delay0=0.0):
    pts, _ = dotmap(s)
    return "".join(f'<circle class="{cls}" style="animation-delay:{delay0+c*.03:.2f}s" cx="{ox+c*pitch:.1f}" cy="{oy+rr*pitch:.1f}" r="{r}"/>'
                   for c, rr in pts)


def activity(d):
    W, H = 480, 236
    weeks = d.get("weeks") or [[0] * 7 for _ in range(52)]
    weeks = weeks[-52:]
    P = 8.3
    gx = (W - (len(weeks) - 1) * P) / 2
    gy = 58
    css = BASE_CSS + f"""
.a{{opacity:0;animation:aon .5s ease-out forwards}}
.n{{opacity:0;animation:aon .4s ease-out forwards}}
.today{{animation:rec 1.2s steps(1) infinite}}
.sc{{opacity:0;animation:scan 6s linear 2.5s infinite}}
@keyframes aon{{to{{opacity:1}}}}
@keyframes scan{{0%{{opacity:0}}2%{{opacity:.9}}7%{{opacity:0}}100%{{opacity:0}}}}
"""
    op = {1: .32, 2: .55, 3: .8, 4: 1}
    b = [panel(W, H, 26),
         f'<text class="t" x="24" y="36" font-size="12" fill="#8a8a8a">ACTIVITY · 52 WEEKS</text>',
         f'<text class="t" x="{W-24}" y="36" font-size="12" fill="#fff" text-anchor="end">{d.get("total", 0)} CONTRIBUTIONS</text>']
    dots, scan = [], []
    last = (len(weeks) - 1, len(weeks[-1]) - 1)
    for wi, wk in enumerate(weeks):
        for di, lv in enumerate(wk):
            cx, cy = gx + wi * P, gy + di * P
            if (wi, di) == last:
                dots.append(f'<circle class="today" cx="{cx:.1f}" cy="{cy:.1f}" r="3" fill="{RED}"/>')
            elif lv == 0:
                dots.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="2.2" fill="#222"/>')
            else:
                dots.append(f'<circle class="a" style="animation-delay:{.2+wi*.025:.3f}s" cx="{cx:.1f}" cy="{cy:.1f}" r="3" fill="#fff" fill-opacity="{op[lv]}"/>')
                scan.append(f'<circle class="sc" style="animation-delay:{2.5+wi*.03:.2f}s" cx="{cx:.1f}" cy="{cy:.1f}" r="3" fill="{RED}"/>')
    b += ["".join(dots), "".join(scan)]
    b.append(f'<line x1="24" x2="{W-24}" y1="128" y2="128" stroke="#1e1e1e"/>')
    cols = [("REPOS", d["repos"]), ("FOLLOWERS", d["followers"]), ("STARS", d["stars"])]
    cw = (W - 48) / 3
    for k, (lab, v) in enumerate(cols):
        x = 24 + k * cw
        b.append(f'<g fill="#f4f4f4">{dot_number(str(v), x + 2, 148, 6, 2.4, "n", .6 + k * .25)}</g>')
        b.append(f'<text class="t" x="{x}" y="214" font-size="12" fill="#8a8a8a">{lab}</text>')
        if k:
            b.append(f'<line x1="{x-12:.1f}" x2="{x-12:.1f}" y1="144" y2="218" stroke="#1e1e1e"/>')
    return svg(W, H, "\n".join(b), css)


# ------------------------------------------------------------------ tiles
TILE_CSS = BASE_CSS + """
.tw{animation:tw 2.8s ease-in-out infinite}
.up{opacity:.12;animation:up 3.2s ease-out infinite}
.rt{opacity:.12;animation:rt 3.6s linear infinite}
.rp{opacity:.2;animation:rp 2.2s ease-out infinite}
@keyframes tw{0%,100%{opacity:.15}50%{opacity:1}}
@keyframes up{0%{opacity:.12}8%{opacity:1}65%{opacity:1}75%{opacity:.12}100%{opacity:.12}}
@keyframes rt{0%{opacity:.12}4%{opacity:1}80%{opacity:1}90%{opacity:.12}100%{opacity:.12}}
@keyframes rp{0%{opacity:.2}12%{opacity:1}35%{opacity:.2}100%{opacity:.2}}
"""
ICONS = {"git-huh": "heat", "AIusageBar": "bars", "nothing-mtui": "wave", "sitewatch": "ripple"}


def tile(i, name, info, desc):
    W = H = 200
    bg, fg, off, mute = [("#f2f2f2", "#0a0a0a", "#d6d6d6", "#555"),
                         ("#000", "#f4f4f4", "#242424", "#8a8a8a"),
                         ("#000", "#f4f4f4", "#242424", "#8a8a8a"),
                         ("#d71921", "#fff", "#b3141b", "#ffd5d6")][i % 4]
    kind = ICONS.get(name, ["heat", "bars", "wave", "ripple"][i % 4])
    b = [panel(W, H, 26, bg) if bg == "#000" else f'<rect width="{W}" height="{H}" rx="26" fill="{bg}"/>']
    ox, oy, P, R = 24, 26, 10, 3.2
    rnd = random.Random(i * 7 + 3)
    hts = [2, 4, 3, 5, 6, 5, 3, 6]
    g = []
    for c in range(8):
        for r in range(6):
            cx, cy = ox + c * P, oy + r * P
            if kind == "heat":
                if rnd.random() < .45:
                    g.append(f'<circle class="tw" style="animation-delay:{-rnd.random()*2.8:.2f}s" cx="{cx}" cy="{cy}" r="{R}" fill="{fg}"/>')
                else:
                    g.append(f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="{fg}" opacity="{rnd.choice([.15, .15, .4, .7, 1])}"/>')
            elif kind == "bars":
                rb = 5 - r
                if rb < hts[c]:
                    g.append(f'<circle class="up" style="animation-delay:{c*.09+rb*.1:.2f}s" cx="{cx}" cy="{cy}" r="{R}" fill="{fg}"/>')
                else:
                    g.append(f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="{off}"/>')
            elif kind == "wave":
                if r == round(2.5 - 2.4 * math.sin(c * .9)):
                    fill = RED if c == 7 else fg
                    g.append(f'<circle class="rt" style="animation-delay:{c*.16:.2f}s" cx="{cx}" cy="{cy}" r="{R}" fill="{fill}"/>')
                else:
                    g.append(f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="{off}"/>')
            else:
                dd = math.hypot(c - 3.5, r - 2.5)
                g.append(f'<circle class="rp" style="animation-delay:{int(dd*1.2)*.18:.2f}s" cx="{cx}" cy="{cy}" r="{R}" fill="{fg}"/>')
    b.append("".join(g))
    pts, _ = dotmap(f"{i+1:02d}")
    b.append("".join(f'<circle cx="{W-22-10*4+c*4:.1f}" cy="{26+r*4}" r="1.6" fill="{fg}"/>' for c, r in pts))
    lang = LANG_CODE.get(info.get("lang"), (info.get("lang") or "").upper()[:5])
    stars = f" ★{info['stars']}" if info.get("stars") else ""
    b.append(f'<text class="t" x="{W-22}" y="72" font-size="11" fill="{mute}" text-anchor="end" letter-spacing="1">{e(lang)}{stars}</text>')
    nm = name if len(name) <= 13 else name[:12] + "…"
    b.append(f'<text x="22" y="120" font-family="{MONO}" font-size="{21 if len(nm) <= 11 else 18}" font-weight="800" fill="{fg}" letter-spacing="-.5">{e(nm)}</text>')
    for k, ln in enumerate(wrap(desc, 21)):
        b.append(f'<text x="22" y="{145+k*19}" font-size="14.5" fill="{mute}">{e(ln)}</text>')
    if info.get("pushed"):
        when, hot = ago(info["pushed"])
        if hot:
            b.append(f'<circle class="rec" cx="26" cy="181" r="3.5" fill="{RED if bg != "#d71921" else "#fff"}"/>')
        b.append(f'<text class="t" x="{36 if hot else 22}" y="185" font-size="10" fill="{mute}" letter-spacing="1.5">PUSHED {when}</text>')
    return svg(W, H, "\n".join(b), TILE_CSS)


# ------------------------------------------------------------------ stack
def stack():
    W, H = 480, 64
    cw, pad, gap = 8.6, 15, 9
    widths = [len(t) * cw + pad * 2 for t in STACK]
    x = (W - sum(widths) - gap * (len(STACK) - 1)) / 2
    css = f""".m{{font-family:{MONO};font-size:13px;font-weight:700}}
.hl{{opacity:0;animation:hl 6s ease infinite}}
@keyframes hl{{0%{{opacity:0}}3%{{opacity:1}}17%{{opacity:1}}20%{{opacity:0}}100%{{opacity:0}}}}"""
    b = [panel(W, H, 22)]
    for k, (t, w) in enumerate(zip(STACK, widths)):
        tl = len(t) * cw
        hb, ht = (RED, "#fff") if k == 0 else ("#fff", "#000")
        b.append(f'<rect x="{x:.1f}" y="16" width="{w:.1f}" height="32" rx="16" fill="none" stroke="#444"/>'
                 f'<text class="m" x="{x+pad:.1f}" y="37" fill="#eee" textLength="{tl:.1f}">{t}</text>'
                 f'<g class="hl" style="animation-delay:{k*1.2:.1f}s"><rect x="{x:.1f}" y="16" width="{w:.1f}" height="32" rx="16" fill="{hb}"/>'
                 f'<text class="m" x="{x+pad:.1f}" y="37" fill="{ht}" textLength="{tl:.1f}">{t}</text></g>')
        x += w + gap
    return svg(W, H, "\n".join(b), css)


# ------------------------------------------------------------------ readme
def readme(d):
    names = list(PROJECTS)
    tiles = [f'<a href="https://github.com/{USER}/{n}"><img src="assets/tile-{i+1}.svg" width="49%" alt="{e(n)}"></a>'
             for i, n in enumerate(names)]
    rows = "\n".join(f'<p align="center">{" ".join(tiles[k:k+2])}</p>' for k in range(0, len(tiles), 2))
    soc = " &nbsp;·&nbsp; ".join(f'<a href="{u}">{n}</a>' for n, u in SOCIALS)
    return f"""<!-- generated by scripts/build.py, refreshed by .github/workflows/refresh.yml; edit the script, not this file -->
<p align="center"><img src="assets/header.svg" width="100%" alt="Jai Khurana, software engineer at PayGlocal, Bengaluru"></p>

<p align="center"><img src="assets/activity.svg" width="100%" alt="{d.get('total', 0)} contributions in the last year · {d['repos']} repos · {d['followers']} followers · {d['stars']} stars"></p>

{rows}

<p align="center"><img src="assets/stack.svg" width="100%" alt="{', '.join(STACK)}"></p>

<p align="center">{soc}</p>
"""


def main():
    d = load()
    out = {"header.svg": header(d), "activity.svg": activity(d), "stack.svg": stack()}
    for i, n in enumerate(PROJECTS):
        info = d["projects"].get(n, {})
        out[f"tile-{i+1}.svg"] = tile(i, n, info, PROJECTS[n] or info.get("desc") or "")
    for fn, s in out.items():
        with open(os.path.join(ASSETS, fn), "w") as f:
            f.write(s)
    with open(os.path.join(ROOT, "README.md"), "w") as f:
        f.write(readme(d))
    print("built", len(out), "svgs:", {k: d[k] for k in ("repos", "followers", "stars")}, "total", d.get("total"))


if __name__ == "__main__":
    main()
