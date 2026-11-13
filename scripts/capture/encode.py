"""Encode original-renderer RGBA frames without baking in stale profile data.

Usage: python scripts/capture/encode.py /tmp/jai-opus-frames
Requires Pillow==11.3.0 with WebP support; browser capture uses jelly.html.
"""
from pathlib import Path
import sys
from PIL import Image
ROOT = Path(__file__).resolve().parents[2]
SRC = Path(sys.argv[1])
OUT = ROOT / 'assets/opus-jelly'
OUT.mkdir(parents=True, exist_ok=True)
for folder in sorted(SRC.iterdir()):
    paths = sorted(folder.glob('*.png'))
    if not paths:
        continue
    sizes = {'header': (480,360), 'd-header': (960,268), 'activity': (480,262), 'd-activity': (960,188), 'tile': (200,200), 'd-tile': (400,150), 'stack': (480,64), 'd-stack': (960,64)}
    frames = [Image.open(p).convert('RGBA').resize(sizes[folder.name], Image.Resampling.LANCZOS) for p in paths]
    target = OUT / (folder.name + '.webp')
    frames[0].save(target, save_all=True, append_images=frames[1:], duration=[83,83,84] * 28,
                   loop=0, lossless=False, quality=92, method=4, kmin=12, kmax=24)
    with Image.open(target) as check:
        assert check.is_animated and check.n_frames > 1
        assert check.size == frames[0].size
    print(folder.name, len(frames), target.stat().st_size, flush=True)
