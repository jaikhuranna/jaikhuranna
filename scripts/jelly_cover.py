"""Composite the original Opus jelly recordings over the current profile panels.

Run with Pillow installed: python scripts/jelly_cover.py /tmp/jai-profile-bases
The README generator loads the resulting native animations without Pillow.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
NAMES = ['header', 'activity', 'tile-1', 'tile-2', 'tile-3', 'tile-4', 'stack']


def covered_files():
    return {('d-jelly-' + name[2:] if name.startswith('d-') else 'jelly-' + name) + '.webp':
            (ROOT / 'assets' / (('d-jelly-' + name[2:] if name.startswith('d-') else 'jelly-' + name) + '.webp')).read_bytes()
            for n in NAMES for name in (n, 'd-' + n)}


def compose_one(name, bases):
    from PIL import Image
    base = Image.open(bases / (name + '.png')).convert('RGBA')
    kind = ('d-tile' if name.startswith('d-') else 'tile') if 'tile-' in name else name
    source = Image.open(ROOT / 'assets/opus-jelly' / (kind + '.webp'))
    result, durations = [], []
    for i in range(source.n_frames):
        source.seek(i)
        frame = source.convert('RGBA').resize(base.size, Image.Resampling.LANCZOS)
        combined = Image.alpha_composite(base, frame)
        combined.putalpha(base.getchannel('A'))
        result.append(combined)
        durations.append(source.info.get('duration', 83))
    target = ('d-jelly-' + name[2:] if name.startswith('d-') else 'jelly-' + name) + '.webp'
    result[0].save(ROOT / 'assets' / target, save_all=True, append_images=result[1:],
                   duration=durations, loop=0, quality=92, method=4, kmin=12, kmax=24)
    print(target, len(result), flush=True)


def compose(bases):
    from concurrent.futures import ThreadPoolExecutor
    names = [name for n in NAMES for name in (n, 'd-' + n)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda name: compose_one(name, bases), names))


def disclosure(covered, original):
    # <picture> keeps GitHub from intercepting summary clicks with image links.
    return f'<details>\n<summary><p align="center">{covered}</p></summary>\n\n{original}\n\n</details>'


if __name__ == '__main__':
    compose(Path(sys.argv[1]))
