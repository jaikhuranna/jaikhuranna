"""Deterministic 16-bit brick art for GitHub's native click-to-reveal controls."""
from io import BytesIO
import math
import random
from PIL import Image, ImageDraw

COLORS = ['#11121b','#241c28','#472634','#743443','#a94c45','#d77555','#f6ac70',
          '#ffe3a3','#8774a5','#5c536e','#dce6d9','#71b49d','#35685e','#e7bd58','#af7e3d','#ffffff']
FONT = {
'A':['01110','10001','10001','11111','10001','10001','10001'],
'B':['11110','10001','10001','11110','10001','10001','11110'],
'C':['01111','10000','10000','10000','10000','10000','01111'],
'D':['11110','10001','10001','10001','10001','10001','11110'],
'E':['11111','10000','10000','11110','10000','10000','11111'],
'F':['11111','10000','10000','11110','10000','10000','10000'],
'G':['01111','10000','10000','10111','10001','10001','01111'],
'H':['10001','10001','10001','11111','10001','10001','10001'],
'I':['11111','00100','00100','00100','00100','00100','11111'],
'J':['00111','00010','00010','00010','10010','10010','01100'],
'K':['10001','10010','10100','11000','10100','10010','10001'],
'L':['10000','10000','10000','10000','10000','10000','11111'],
'M':['10001','11011','10101','10101','10001','10001','10001'],
'N':['10001','11001','10101','10011','10001','10001','10001'],
'O':['01110','10001','10001','10001','10001','10001','01110'],
'P':['11110','10001','10001','11110','10000','10000','10000'],
'Q':['01110','10001','10001','10001','10101','10010','01101'],
'R':['11110','10001','10001','11110','10100','10010','10001'],
'S':['01111','10000','10000','01110','00001','00001','11110'],
'T':['11111','00100','00100','00100','00100','00100','00100'],
'U':['10001','10001','10001','10001','10001','10001','01110'],
'V':['10001','10001','10001','10001','10001','01010','00100'],
'W':['10001','10001','10001','10101','10101','10101','01010'],
'X':['10001','10001','01010','00100','01010','10001','10001'],
'Y':['10001','10001','01010','00100','00100','00100','00100'],
'Z':['11111','00001','00010','00100','01000','10000','11111'],
'0':['01110','10001','10011','10101','11001','10001','01110'],
'1':['00100','01100','00100','00100','00100','00100','01110'],
'2':['01110','10001','00001','00010','00100','01000','11111'],
'3':['11110','00001','00001','01110','00001','00001','11110'],
'4':['00010','00110','01010','10010','11111','00010','00010'],
'5':['11111','10000','10000','11110','00001','00001','11110'],
'6':['01110','10000','10000','11110','10001','10001','01110'],
'7':['11111','00001','00010','00100','01000','01000','01000'],
'8':['01110','10001','10001','01110','10001','10001','01110'],
'9':['01110','10001','10001','01111','00001','00001','01110'],
'-':['00000','00000','00000','11111','00000','00000','00000'],
'!':['00100','00100','00100','00100','00100','00000','00100'],
' ':['00000']*7,
}


def text(draw, label, x, y, scale=1, color=7):
    label=label.upper()
    for i,char in enumerate(label):
        for row,line in enumerate(FONT.get(char,FONT[' '])):
            for col,value in enumerate(line):
                if value=='1':
                    px=x+(i*6+col)*scale;py=y+row*scale
                    draw.rectangle((px,py,px+scale-1,py+scale-1),fill=COLORS[color])


def center(draw,label,y,width,scale=1,color=7):
    x=(width-(len(label)*6-1)*scale)//2
    text(draw,label,x+scale,y+scale,scale,0)
    text(draw,label,x,y,scale,color)


def brick(draw,x,y,w,h,shade=4):
    draw.rectangle((x,y,x+w-1,y+h-1),fill=COLORS[1])
    draw.rectangle((x+1,y+1,x+w-2,y+h-2),fill=COLORS[shade])
    draw.line((x+2,y+1,x+w-3,y+1),fill=COLORS[6])
    draw.line((x+1,y+2,x+1,y+h-3),fill=COLORS[5])
    draw.line((x+2,y+h-2,x+w-2,y+h-2),fill=COLORS[2])
    draw.line((x+w-2,y+2,x+w-2,y+h-3),fill=COLORS[2])
    draw.line((x+4,y+h-4,x+8,y+h-4),fill=COLORS[shade-1])


def wall(w,h,label,index,prompt="CLICK TO BREAK"):
    im=Image.new('RGB',(w,h),COLORS[0]);d=ImageDraw.Draw(im)
    for row,y in enumerate(range(0,h,12)):
        for col,x in enumerate(range(-24 if row%2 else 0,w,32)):
            brick(d,x,y,32,12,3+(row*3+col+index)%3)
    scale=min(3,max(1,(w-24)//max(1,len(label)*6-1)))
    tall=h>=60
    if not tall: scale=1
    plate_h=38 if tall else 25
    y=(h-plate_h)//2
    width=min(w-12,max((len(label)*6-1)*scale+16,92))
    x=(w-width)//2
    d.rectangle((x+2,y+2,x+width+2,y+plate_h+2),fill=COLORS[0])
    d.rectangle((x,y,x+width,y+plate_h),fill=COLORS[13])
    d.rectangle((x+1,y+1,x+width-1,y+plate_h-1),fill=COLORS[1])
    center(d,label,y+(5 if tall else 3),w,scale)
    if tall:
        center(d,prompt,y+plate_h-11,w,1,6)
    else:
        center(d,'CLICK',y+plate_h-8,w,1,6)
    if h>100:
        center(d,f'{index:02d}',h-13,w,1,7)
    return im


def break_frames(w,h,index):
    rng=random.Random(index+1600)
    pieces=[(rng.uniform(-17,17),rng.uniform(-72,72),rng.uniform(-95,-35),rng.randrange(3,7),rng.randrange(2,5),rng.choice([3,4,5,6,13])) for _ in range(24)]
    frames=[]
    for frame in range(30):
        t=frame/12
        im=Image.new('RGB',(w,h),COLORS[0]);d=ImageDraw.Draw(im)
        cx,cy=w//2,h//2
        if t<.42:
            brick(d,cx-17,cy-7,34,14,4)
            if t>.08:
                points=[(cx-2,cy-6),(cx+2,cy-2),(cx-1,cy+1),(cx+3,cy+6)]
                d.line(points,fill=COLORS[7 if frame%2 else 0],width=1)
        else:
            age=t-.42
            for px,vx,vy,pw,ph,c in pieces:
                x=round(cx+px+vx*age);y=round(cy+vy*age+100*age*age)
                if y<h:
                    d.rectangle((x,y,x+pw,y+ph),fill=COLORS[c])
                    d.line((x,y,x+pw-1,y),fill=COLORS[7])
            if age<.28:
                for i in range(8):
                    angle=i*math.tau/8
                    r=7+age*70
                    x=round(cx+math.cos(angle)*r);y=round(cy+math.sin(angle)*r)
                    d.rectangle((x,y,x+1,y+1),fill=COLORS[7 if frame%2 else 13])
            if age>.4:
                center(d,'UNLOCKED!',h//2-3,w,1,11)
                # Small pixel stars frame the reward without covering its text.
                for x in [cx-38,cx+36]:
                    d.line((x-2,cy,x+2,cy),fill=COLORS[13])
                    d.line((x,cy-2,x,cy+2),fill=COLORS[13])
        frames.append(im.resize((w*4,h*4),Image.Resampling.NEAREST))
    return frames


def png(im):
    out=BytesIO();im.save(out,format='PNG',optimize=True);return out.getvalue()


def assets(projects):
    labels={'header':'JAI KHURANA','activity':'ACTIVITY','stack':'STACK'}
    labels.update({f'tile-{i+1}':name.upper() for i,name in enumerate(projects)})
    dims={'header':(480,360),'d-header':(960,268),'activity':(480,262),'d-activity':(960,188),
          'stack':(480,64),'d-stack':(960,64)}
    out={}
    for index,(name,label) in enumerate(labels.items(),1):
        for wide in [False,True]:
            variant=('d-' if wide else '')+name
            w,h=dims.get(variant,(400,150) if wide else (200,200))
            prefix='d-' if wide else ''
            art=wall(w//2,h//2,label,index).resize((w*2,h*2),Image.Resampling.NEAREST)
            out[f'{prefix}brick-{name}.png']=png(art)
            frames=break_frames(w//2,24,index)
            stream=BytesIO()
            frames[0].save(stream,format='GIF',save_all=True,append_images=frames[1:],duration=[80,80,90]*10,loop=0,optimize=True)
            out[f'{prefix}break-{name}.gif']=stream.getvalue()
            out[f'{prefix}broken-{name}.png']=png(frames[-1])
    return out


def disclosure(covered,animation,original):
    return (f'<details>\n<summary><p align="center">{covered}</p></summary>\n\n'
            f'<p align="center">{animation}</p>\n\n{original}\n\n</details>')
