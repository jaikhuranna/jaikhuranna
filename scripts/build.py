#!/usr/bin/env python3
"""Builds the jelly profile README and SVGs with live GitHub data.

Run locally:   GITHUB_TOKEN=$(gh auth token) python3 scripts/build.py
Runs in CI:    .github/workflows/refresh.yml (every 6 hours)

Every image comes in two layouts. The phone one is the <img>; the desktop one
is a <source media="(min-width: 1012px)"> in front of it, so a wide screen
gets a wide, short banner instead of a phone layout blown up to 850px.

Edit PROJECTS / ROLE / STACK below to change what the profile shows.
Stdlib only. If the API is unreachable it falls back to assets/data.json.
"""
import hashlib, json, math, os, random, sys, urllib.request
from datetime import datetime, timedelta, timezone
from html import escape as e
import jelly

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
    "git-huh": "GitHub on my phone: contribution charts, an inbox, pull requests and a home for project ideas.",
    "AIusageBar": "Claude and Codex subscription limits across desktop, phone and wrist. One Go server, native widgets.",
    "nothing-mtui": "Material You colours on Nothing OS",
    "sitewatch": "Page watcher with Telegram alerts",
}
# never shown as "now building" (private repos and forks are never shown either)
NOT_BUILDING = {USER, "git-huh-sandbox"}
DESKTOP = "(min-width: 1012px)"  # GitHub's wide layout starts here
RAW = f"https://raw.githubusercontent.com/{USER}/{USER}/main/"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,'SF Mono','Roboto Mono',Menlo,Consolas,'DejaVu Sans Mono',monospace"
RED = "#ff3b30"
INK = "#f4f4f4"
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
        data.update(contributions())
    except Exception as ex:  # GraphQL needs a token; keep the old field if it fails
        print("contributions unavailable:", ex, file=sys.stderr)
    return data


HISTORY_YEARS = 3  # enough that the field is always full of real days, never padding


def contributions():
    """Days oldest first as [date, level, count]; the last day is today.

    GitHub answers at most a year per contributionsCollection, so ask for
    several back-to-back years in one query and stitch them together."""
    now = datetime.now(timezone.utc).replace(microsecond=0)
    var, fields, args = {"u": USER}, [], ["$u:String!"]
    for k in range(HISTORY_YEARS):
        var[f"f{k}"] = (now - timedelta(days=365 * (k + 1))).isoformat()
        var[f"t{k}"] = (now - timedelta(days=365 * k)).isoformat()
        args += [f"$f{k}:DateTime!", f"$t{k}:DateTime!"]
        fields.append(f"y{k}:contributionsCollection(from:$f{k},to:$t{k}){{contributionCalendar{{"
                      "totalContributions weeks{contributionDays{date contributionLevel contributionCount}}}}")
    q = f"query({','.join(args)}){{user(login:$u){{{' '.join(fields)}}}}}"
    res = api("https://api.github.com/graphql", {"query": q, "variables": var})
    if res.get("errors"):
        raise RuntimeError(res["errors"])
    user = res["data"]["user"]
    lv = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
    by_date = {}
    for k in range(HISTORY_YEARS):
        for w in user[f"y{k}"]["contributionCalendar"]["weeks"]:
            for d in w["contributionDays"]:
                by_date[d["date"]] = [d["date"], lv[d["contributionLevel"]], d["contributionCount"]]
    days = [by_date[k] for k in sorted(by_date)]
    return {"total": user["y0"]["contributionCalendar"]["totalContributions"], "days": days}


def load():
    cache = os.path.join(ASSETS, "data.json")
    old = json.load(open(cache)) if os.path.exists(cache) else {}
    try:
        old.update(fetch())
    except Exception as ex:
        print("API failed, using cached data:", ex, file=sys.stderr)
        if not old:
            raise
    old.pop("weeks", None)
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
    out, cur = [], ""
    for w in (text or "").split():
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
HEAD_CSS = BASE_CSS + f"""
.d{{opacity:0;animation:boot .45s ease-out forwards}}
.s{{opacity:0;animation:sweep 7s linear infinite}}
.seg{{opacity:0;animation:seg 5s ease-in-out infinite}}
@keyframes boot{{0%{{opacity:0}}60%{{opacity:1;fill:{RED}}}100%{{opacity:1}}}}
@keyframes sweep{{0%{{opacity:0}}3%{{opacity:1}}9%{{opacity:0}}100%{{opacity:0}}}}
@keyframes seg{{0%{{opacity:0}}5%{{opacity:1}}62%{{opacity:1}}70%{{opacity:0}}100%{{opacity:0}}}}
"""


def name_dots(lines, x0, y0, P, r):
    """lines: [(text, row offset)]. Returns the lit layer and the red sweep layer."""
    lit, red = [], []
    for li, (txt, roff) in enumerate(lines):
        pts, _ = dotmap(txt)
        for c, rr in pts:
            cx, cy = x0 + c * P, y0 + (rr + roff) * P
            lit.append(f'<circle class="d" style="animation-delay:{.3+c*.028+li*.35:.3f}s" cx="{cx:.1f}" cy="{cy:.1f}" r="{r}"/>')
            red.append(f'<circle class="s" style="animation-delay:{2.6+c*.035:.3f}s" cx="{cx:.1f}" cy="{cy:.1f}" r="{r}"/>')
    return f'<g fill="{INK}">{"".join(lit)}</g><g fill="{RED}">{"".join(red)}</g>'


def seg_bar(x, y, w, n=30, h=10):
    sw = (w - (n - 1) * 3) / n
    off = "".join(f'<rect x="{x+k*(sw+3):.1f}" y="{y}" width="{sw:.1f}" height="{h}" rx="2"/>' for k in range(n))
    on = "".join(f'<rect class="seg" style="animation-delay:{k*.08:.2f}s" x="{x+k*(sw+3):.1f}" y="{y}" width="{sw:.1f}" height="{h}" rx="2"/>' for k in range(n))
    return f'<g fill="#222">{off}</g><g fill="#fff">{on}</g>'


def now_building(d):
    bl = d.get("building")
    return f'{bl["name"].upper()[:16]} / {(bl["lang"] or "").upper()}'.rstrip(" /") if bl else "SOMETHING NEW"


def header_top(W, H, x0, y0, P, rx):
    return [f'<defs><clipPath id="r"><rect width="{W}" height="{H}" rx="{rx}"/></clipPath>'
            f'<pattern id="g" width="{P}" height="{P}" patternUnits="userSpaceOnUse" x="{x0-P/2:.2f}" y="{y0-P/2:.2f}">'
            f'<circle cx="{P/2}" cy="{P/2}" r="1.7" fill="#1e1e1e"/></pattern></defs>',
            f'<g clip-path="url(#r)"><rect width="{W}" height="{H}" fill="#000"/><rect width="{W}" height="{H}" fill="url(#g)"/></g>',
            f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="{rx}" fill="none" stroke="#262626"/>']


def header(d):
    W, H, P = 480, 360, 10.2
    x0, y0 = (W - 41 * P) / 2 + P / 2, 78
    bx, bw = x0 - 4, 41 * P
    b = header_top(W, H, x0, y0, P, 30) + [
        f'<text class="t" x="28" y="38" font-size="12" fill="#8a8a8a">{USER.upper()}</text>',
        f'<text class="t" x="430" y="38" font-size="12" fill="#8a8a8a" text-anchor="end">LIVE</text>',
        f'<circle class="rec" cx="446" cy="34" r="5" fill="{RED}"/>',
        name_dots([(NAME[0], 0), (NAME[1], 9)], x0, y0, P, 4),
        f'<text class="t" x="{bx:.0f}" y="268" font-size="19" font-weight="700" fill="#fff">{e(ROLE)}</text>',
        f'<text class="t" x="{bx:.0f}" y="292" font-size="13.5" fill="#9a9a9a" letter-spacing="1.5">{e(WHERE)}</text>',
        seg_bar(bx, 310, bw),
        f'<text class="t" x="{bx:.0f}" y="343" font-size="12" fill="#8a8a8a">NOW BUILDING</text>',
        f'<text class="t" x="{bx+bw:.0f}" y="343" font-size="12" fill="#fff" text-anchor="end">{e(now_building(d))}</text>']
    return svg(W, H, "\n".join(b), HEAD_CSS)


def header_wide(d):
    """Desktop: the name on one line, a short banner."""
    W, H, P = 960, 268, 12.2
    _, cols = dotmap(" ".join(NAME))
    x0, y0 = (W - (cols - 1) * P) / 2, 82
    m = x0 - 4
    b = header_top(W, H, x0, y0, P, 26) + [
        f'<text class="t" x="{m:.0f}" y="44" font-size="12" fill="#8a8a8a">{USER.upper()}</text>',
        f'<text class="t" x="{W-m-16:.0f}" y="44" font-size="12" fill="#8a8a8a" text-anchor="end">LIVE</text>',
        f'<circle class="rec" cx="{W-m-4:.0f}" cy="40" r="5" fill="{RED}"/>',
        name_dots([(" ".join(NAME), 0)], x0, y0, P, 4.8),
        f'<text class="t" x="{m:.0f}" y="196" font-size="19" font-weight="700" fill="#fff">{e(ROLE)}</text>',
        f'<text class="t" x="{m:.0f}" y="220" font-size="13.5" fill="#9a9a9a" letter-spacing="1.5">{e(WHERE)}</text>',
        f'<text class="t" x="{W-m:.0f}" y="196" font-size="12" fill="#8a8a8a" text-anchor="end">NOW BUILDING</text>',
        f'<text class="t" x="{W-m:.0f}" y="220" font-size="13.5" fill="#fff" text-anchor="end">{e(now_building(d))}</text>',
        seg_bar(m, 238, W - 2 * m, n=60, h=8)]
    return svg(W, H, "\n".join(b), HEAD_CSS)


# ------------------------------------------------------------------ activity
# The field follows git-huh's widget (DotFieldRenderer): days run down each
# column, oldest top-left, so today is always the bottom-right mark (a plus).
# A mark's size and weight are its level. Three weeks or more of nothing is
# folded into a wave three columns wide with its length written over it, and
# each side of the wave keeps one column of the silence's own empty days.
SCALES = [.26, .44, .62, .82, 1.0]
ALPHAS = [.24, .52, .72, .88, 1.0]  # a touch heavier than the widget: this sits on pure black
GAP_SHARE, QUIET_DAYS, QUIET_COLUMNS = .30, 21, 3


def slots_of(days, rows):
    """days: levels oldest first, last is today. Returns slots newest first.
    ("day", level, is_today, index) or ("quiet", run, to_edge, oldest index, newest hidden index)."""
    slots, cells, i, last = [], 0, len(days) - 1, len(days) - 1
    while i >= 0:
        if days[i] > 0 or i == last:
            slots.append(("day", days[i], i == last, i)); cells += 1; i -= 1
            continue
        j = i
        while j >= 0 and days[j] == 0 and j != last:
            j -= 1
        run, to_edge = i - j, j < 0
        lead = (rows - cells % rows) % rows + rows
        trail = 0 if to_edge else rows
        hidden = run - lead - trail
        folds = run >= QUIET_DAYS and (hidden > 0 if to_edge else hidden > QUIET_COLUMNS * rows)
        if folds:
            slots += [("day", 0, False, m) for m in range(i, i - lead, -1)]
            slots.append(("quiet", run, to_edge, j + 1, i - lead))
            slots += [("day", 0, False, m) for m in range(j + trail, j, -1)]
            cells += lead + trail + QUIET_COLUMNS * rows
        else:
            slots += [("day", 0, False, m) for m in range(i, j, -1)]
            cells += run
        i = j
    return slots


def how_long(days):
    if days < 56: return f"{round(days / 7)} wk"
    if days < 365: return f"{max(2, round(days / 30.44))} mo"
    return f"{max(1, round(days / 365.25))} yr"


def wave_path(x, y, length, amp, wl):
    steps = max(2, math.ceil(length / 2))
    return " ".join(f'{"M" if s == 0 else "L"}{x + length*s/steps:.1f} {y + math.sin(length*s/steps / wl * 2 * math.pi) * amp:.1f}'
                    for s in range(steps + 1))


def field(days, left, top, columns, rows, pitch, label_size):
    cell = pitch * (1 - GAP_SHARE)
    cap = columns * rows
    cx = lambda k: left + (columns - 1 - k // rows) * pitch + pitch / 2
    cy = lambda k: top + (rows - 1 - k % rows) * pitch + pitch / 2
    delay = lambda k: .2 + (k // rows) * .035
    out, k, oldest = [], 0, len(days) - 1

    def mark(k, lv, today):
        x, y, dl = cx(k), cy(k), delay(k)
        if today:
            a, bar = cell * .5, cell * .22
            return (f'<g class="today"><rect x="{x-a:.1f}" y="{y-bar/2:.1f}" width="{2*a:.1f}" height="{bar:.1f}" fill="{RED}"/>'
                    f'<rect x="{x-bar/2:.1f}" y="{y-a:.1f}" width="{bar:.1f}" height="{2*a:.1f}" fill="{RED}"/></g>')
        s = cell * SCALES[lv]
        if lv >= 4:
            return (f'<rect class="m" style="animation-delay:{dl:.2f}s" x="{x-s/2:.1f}" y="{y-s/2:.1f}" width="{s:.1f}" '
                    f'height="{s:.1f}" rx="{s*.22:.1f}" fill="{INK}"/>')
        return f'<circle class="m" style="animation-delay:{dl:.2f}s" cx="{x:.1f}" cy="{y:.1f}" r="{s/2:.2f}" fill="{INK}" fill-opacity="{ALPHAS[lv]}"/>'

    for slot in slots_of(days, rows):
        if k >= cap:
            break
        if slot[0] == "day":
            out.append(mark(k, slot[1], slot[2])); k += 1
            oldest = slot[3]
            continue
        remaining = columns - k // rows
        span = remaining if slot[2] else min(QUIET_COLUMNS, remaining)
        if span < 2:
            n = cap - k
            while k < cap:
                out.append(mark(k, 0, False)); k += 1
            oldest = slot[4] - n + 1
            break
        x1, x2 = left + (remaining - span) * pitch, left + remaining * pitch
        inset, mid = pitch * .35, top + pitch * rows * .58
        amp, wl = 2.6, 13
        length = x2 - x1 - 2 * inset
        dl = delay(k)
        out.append(f'<path class="w" style="--l:{length*1.25:.0f};animation-delay:{dl:.2f}s" d="{wave_path(x1+inset, mid, length, amp, wl)}" '
                   f'fill="none" stroke="{INK}" stroke-opacity=".5" stroke-width="1.4" stroke-linecap="round"/>')
        out.append(f'<text class="t m" style="animation-delay:{dl+.3:.2f}s" x="{(x1+x2)/2:.1f}" y="{mid-amp-pitch*.75:.1f}" '
                   f'font-size="{label_size}" fill="{INK}" fill-opacity=".72" text-anchor="middle" letter-spacing="0">{how_long(slot[1])}</text>')
        k += span * rows
        oldest = slot[3]
    while k < cap:  # before the history GitHub sent (only if the API gave too little)
        out.append(f'<circle cx="{cx(k):.1f}" cy="{cy(k):.1f}" r="{cell*SCALES[0]/2:.2f}" fill="{INK}" fill-opacity=".12"/>'); k += 1
    return "".join(out), oldest


FIELD_CSS = BASE_CSS + """
.m{opacity:0;animation:on .5s ease-out forwards}
.w{stroke-dasharray:var(--l);stroke-dashoffset:var(--l);animation:draw 1.2s ease-out forwards}
.today{animation:rec 1.2s steps(1) infinite}
@keyframes on{to{opacity:1}}
@keyframes draw{to{stroke-dashoffset:0}}
"""


def dot_number(s, ox, oy, pitch, r, delay0=0.0):
    pts, _ = dotmap(s)
    return "".join(f'<circle class="m" style="animation-delay:{delay0+c*.03:.2f}s" cx="{ox+c*pitch:.1f}" cy="{oy+rr*pitch:.1f}" r="{r}"/>'
                   for c, rr in pts)


def stats(d, x, y, w, pitch, r, label_y):
    cols = [("REPOS", d["repos"]), ("FOLLOWERS", d["followers"]), ("STARS", d["stars"])]
    cw, out = w / 3, []
    for k, (lab, v) in enumerate(cols):
        sx = x + k * cw
        out.append(f'<g fill="{INK}">{dot_number(str(v), sx + 2, y, pitch, r, .6 + k * .25)}</g>')
        out.append(f'<text class="t" x="{sx:.1f}" y="{label_y}" font-size="12" fill="#8a8a8a">{lab}</text>')
        if k:
            out.append(f'<line x1="{sx-12:.1f}" x2="{sx-12:.1f}" y1="{y-6}" y2="{label_y+4}" stroke="#1e1e1e"/>')
    return "".join(out)


def day_rows(d):
    rows = d.get("days") or [[None, 0, 0]]
    return [r if isinstance(r, list) else [None, r, 0] for r in rows]


def field_labels(rows, oldest):
    """'SINCE MAR 2025' and the contributions in exactly the days drawn."""
    first = rows[oldest][0]
    since = datetime.fromisoformat(first).strftime("SINCE %b %Y").upper() if first else "LAST YEAR"
    return since, sum(r[2] for r in rows[oldest:])


def activity(d):
    W, H, P = 480, 262, 12
    rows = day_rows(d)
    cols = int((W - 48) // P)
    left = (W - cols * P) / 2
    dots, oldest = field([r[1] for r in rows], left, 54, cols, 7, P, 11)
    since, count = field_labels(rows, oldest)
    b = [panel(W, H, 26),
         f'<text class="t" x="24" y="36" font-size="12" fill="#8a8a8a">ACTIVITY · {since}</text>',
         f'<text class="t" x="{W-24}" y="36" font-size="12" fill="#fff" text-anchor="end">{count} CONTRIBUTIONS</text>',
         dots,
         f'<line x1="24" x2="{W-24}" y1="158" y2="158" stroke="#1e1e1e"/>',
         stats(d, 24, 182, W - 48, 6, 2.4, 244)]
    return svg(W, H, "\n".join(b), FIELD_CSS)


def activity_wide(d):
    W, H, P = 960, 188, 13.5
    rows = day_rows(d)
    cols = int(540 // P)
    fx = 32 + cols * P
    dots, oldest = field([r[1] for r in rows], 32, 58, cols, 7, P, 12)
    since, count = field_labels(rows, oldest)
    b = [panel(W, H, 24),
         f'<text class="t" x="32" y="40" font-size="12" fill="#8a8a8a">ACTIVITY · {since}</text>',
         f'<text class="t" x="{fx:.0f}" y="40" font-size="12" fill="#fff" text-anchor="end">{count} CONTRIBUTIONS</text>',
         dots,
         f'<line x1="{fx+28:.0f}" x2="{fx+28:.0f}" y1="28" y2="{H-28}" stroke="#1e1e1e"/>',
         stats(d, fx + 56, 70, W - (fx + 56) - 32, 6, 2.4, 140)]
    return svg(W, H, "\n".join(b), FIELD_CSS)


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
THEMES = [("#f2f2f2", "#0a0a0a", "#d6d6d6", "#555"), ("#000", INK, "#242424", "#8a8a8a"),
          ("#000", INK, "#242424", "#8a8a8a"), ("#d71921", "#fff", "#b3141b", "#ffd5d6")]


def icon(kind, ox, oy, fg, off, seed):
    P, R = 10, 3.2
    rnd = random.Random(seed)
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
                    g.append(f'<circle class="rt" style="animation-delay:{c*.16:.2f}s" cx="{cx}" cy="{cy}" r="{R}" fill="{RED if c == 7 else fg}"/>')
                else:
                    g.append(f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="{off}"/>')
            else:
                dd = math.hypot(c - 3.5, r - 2.5)
                g.append(f'<circle class="rp" style="animation-delay:{int(dd*1.2)*.18:.2f}s" cx="{cx}" cy="{cy}" r="{R}" fill="{fg}"/>')
    return "".join(g)


def tile_parts(i, name, info):
    bg, fg, off, mute = THEMES[i % 4]
    lang = LANG_CODE.get(info.get("lang"), (info.get("lang") or "").upper()[:5])
    stars = f" ★{info['stars']}" if info.get("stars") else ""
    nm = name if len(name) <= 13 else name[:12] + "…"
    pushed = ago(info["pushed"]) if info.get("pushed") else None
    return bg, fg, off, mute, f"{lang}{stars}", nm, pushed


def tile_bg(W, H, bg):
    return panel(W, H, 26, bg) if bg == "#000" else f'<rect width="{W}" height="{H}" rx="26" fill="{bg}"/>'


def index_dots(i, right, top, fg):
    pts, _ = dotmap(f"{i+1:02d}")
    return "".join(f'<circle cx="{right-40+c*4:.1f}" cy="{top+r*4}" r="1.6" fill="{fg}"/>' for c, r in pts)


def pushed_line(x, y, pushed, bg, mute):
    if not pushed:
        return ""
    when, hot = pushed
    s = f'<circle class="rec" cx="{x+4}" cy="{y-4}" r="3.5" fill="{RED if bg != "#d71921" else "#fff"}"/>' if hot else ""
    return s + f'<text class="t" x="{x+14 if hot else x}" y="{y}" font-size="10" fill="{mute}" letter-spacing="1.5">PUSHED {when}</text>'


def tile(i, name, info, desc):
    W = H = 200
    bg, fg, off, mute, meta, nm, pushed = tile_parts(i, name, info)
    b = [tile_bg(W, H, bg), icon(ICONS.get(name, "heat"), 24, 26, fg, off, i * 7 + 3),
         index_dots(i, W - 22, 26, fg),
         f'<text class="t" x="{W-22}" y="72" font-size="11" fill="{mute}" text-anchor="end" letter-spacing="1">{e(meta)}</text>',
         f'<text x="22" y="120" font-family="{MONO}" font-size="{21 if len(nm) <= 11 else 18}" font-weight="800" fill="{fg}" letter-spacing="-.5">{e(nm)}</text>']
    b += [f'<text x="22" y="{145+k*19}" font-size="14.5" fill="{mute}">{e(ln)}</text>' for k, ln in enumerate(wrap(desc, 21))]
    b.append(pushed_line(22, 185, pushed, bg, mute))
    return svg(W, H, "\n".join(b), TILE_CSS)


def tile_wide(i, name, info, desc):
    """Desktop: a short horizontal card, the icon beside the words."""
    W, H = 400, 150
    bg, fg, off, mute, meta, nm, pushed = tile_parts(i, name, info)
    b = [tile_bg(W, H, bg), icon(ICONS.get(name, "heat"), 30, 50, fg, off, i * 7 + 3),
         index_dots(i, W - 24, 24, fg),
         f'<text x="130" y="58" font-family="{MONO}" font-size="21" font-weight="800" fill="{fg}" letter-spacing="-.5">{e(nm)}</text>']
    b += [f'<text x="130" y="{84+k*19}" font-size="14.5" fill="{mute}">{e(ln)}</text>' for k, ln in enumerate(wrap(desc, 30))]
    b.append(pushed_line(130, 128, pushed, bg, mute))
    b.append(f'<text class="t" x="{W-24}" y="128" font-size="11" fill="{mute}" text-anchor="end" letter-spacing="1">{e(meta)}</text>')
    return svg(W, H, "\n".join(b), TILE_CSS)


# ------------------------------------------------------------------ stack
def stack(W=480, H=64):
    cw, pad, gap = 8.6, 15, 9
    widths = [len(t) * cw + pad * 2 for t in STACK]
    x = (W - sum(widths) - gap * (len(STACK) - 1)) / 2
    css = f".m{{font-family:{MONO};font-size:13px;font-weight:700}}"
    b = [panel(W, H, 22)]
    y = (H - 32) / 2
    for k, (t, w) in enumerate(zip(STACK, widths)):
        tl = len(t) * cw
        b.append(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="32" rx="16" fill="none" stroke="#444"/>'
                 f'<text class="m" x="{x+pad:.1f}" y="{y+21}" fill="#eee" textLength="{tl:.1f}">{t}</text>')
        x += w + gap
    return svg(W, H, "\n".join(b), css)


# ------------------------------------------------------------------ readme
def pic(name, alt, width, files):
    """A phone image with a desktop image in front of it. ?v= busts GitHub's image cache."""
    v = lambda fn: hashlib.sha1(files[fn].encode()).hexdigest()[:8]
    return (f'<picture><source media="{DESKTOP}" srcset="{RAW}assets/d-{name}?v={v("d-" + name)}">'
            f'<img src="assets/{name}?v={v(name)}" width="{width}" alt="{e(alt)}"></picture>')


def readme(d, files):
    return jelly.readme(d, files, PROJECTS, SOCIALS, pic)


def main():
    d = json.load(open(os.path.join(ASSETS, "data.json"))) if "--cached" in sys.argv else load()
    out = {"header.svg": header(d), "d-header.svg": header_wide(d),
           "activity.svg": activity(d), "d-activity.svg": activity_wide(d),
           "stack.svg": stack(), "d-stack.svg": stack(960, 64)}
    for i, n in enumerate(PROJECTS):
        info = d["projects"].get(n, {})
        desc = PROJECTS[n] or info.get("desc") or ""
        out[f"tile-{i+1}.svg"] = tile(i, n, info, desc)
        out[f"d-tile-{i+1}.svg"] = tile_wide(i, n, info, desc)
    out.update(jelly.files(PROJECTS))
    jelly.write_demo(ROOT, d, PROJECTS)
    for fn, s in out.items():
        with open(os.path.join(ASSETS, fn), "w") as f:
            f.write(s)
    with open(os.path.join(ROOT, "README.md"), "w") as f:
        f.write(readme(d, out))
    print("built", len(out), "svgs:", {k: d[k] for k in ("repos", "followers", "stars")}, "total", d.get("total"))


if __name__ == "__main__":
    main()
