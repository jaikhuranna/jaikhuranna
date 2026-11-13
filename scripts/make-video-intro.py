"""Manual asset build: original name card, a 16-bit wall, and one native play tap.

node scripts/render-video-header.mjs /tmp/jai-native-intro
python scripts/make-video-intro.py /tmp/jai-native-intro
Requires Pillow and ffmpeg. Upload assets/jai.mp4 as a GitHub attachment afterward.
"""
from pathlib import Path
import hashlib
import json
import random
import subprocess
import sys
from PIL import Image,ImageDraw
import brick_cover as art

root=Path(__file__).resolve().parents[1]
work=Path(sys.argv[1]);work.mkdir(parents=True,exist_ok=True)
base=Image.open(work/'identity.png').convert('RGB')
w,h=base.size
logical=(w//4,h//4)
wall=art.wall(*logical,'JAI KHURANA',1,prompt='TAP PLAY TO BREAK').resize((w,h),Image.Resampling.NEAREST)
wall.save(root/'assets/intro-poster.png')
rng=random.Random(160016)
pieces=[]
for y in range(0,logical[1],12):
 for x in range(0,logical[0],32):
  # Crack along the mortar, then scatter the actual wall pixels.
  crop=wall.crop((x*4,y*4,min((x+32)*4,w),min((y+12)*4,h)))
  direction=(x+16-logical[0]/2)/(logical[0]/2)
  pieces.append((x*4,y*4,crop,direction*160+rng.uniform(-90,90),rng.uniform(-230,-80),rng.uniform(0,.16)))
for i in range(84):
 t=i/30
 im=base.copy()
 if t<.17:im=wall.copy()
 elif t<1.45:
  for x,y,crop,vx,vy,delay in pieces:
   age=max(0,t-.17-delay)
   dx=round(vx*age*4);dy=round((vy*age+460*age*age)*4)
   im.paste(crop,(x+dx,y+dy))
 im.save(work/f'frame-{i:03d}.png')
subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate','30','-i',str(work/'frame-%03d.png'),'-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(root/'assets/jai.mp4')],check=True)
print('Built native video:',(root/'assets/jai.mp4').stat().st_size,'bytes')
