"""Reproducible procedural artwork for Yama Hajime."""
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT=Path(__file__).resolve().parents[1]/"assets"/"images"
W,H=960,720

def gradient(top,bottom):
    y=np.linspace(0,1,H)[:,None,None]
    a=np.array(top)[None,None,:]*(1-y)+np.array(bottom)[None,None,:]*y
    return np.repeat(a,W,axis=1)

def make(name,seed,kind):
    rng=np.random.default_rng(seed)
    arr=gradient((70,88,80),(20,38,31))
    noise=rng.normal(0,7,(H,W,1)); arr=np.clip(arr+noise,0,255).astype('uint8')
    im=Image.fromarray(arr).filter(ImageFilter.GaussianBlur(1.2)); d=ImageDraw.Draw(im,'RGBA')
    # layered mist and distant ridges
    for layer in range(5):
        base=250+layer*65
        pts=[(0,H)]+[(x,int(base+45*np.sin(x/130+layer)+rng.integers(-20,21))) for x in range(0,W+80,80)]+[(W,H)]
        d.polygon(pts,fill=(16+layer*5,38+layer*6,30+layer*5,170))
        d.rectangle((0,base-20,W,base+20),fill=(180,194,187,18))
    if kind in ('forest','hero','trail'):
        for x in rng.integers(-20,W+20,34):
            width=int(rng.integers(7,18)); top=int(rng.integers(50,260))
            d.polygon([(x-width,top+130),(x,top),(x+width,top+130)],fill=(9,29,22,205))
            d.rectangle((x-3,top+100,x+4,H),fill=(12,29,23,220))
    if kind=='trail':
        d.polygon([(410,H),(560,H),(515,430),(475,430)],fill=(87,75,61,185))
        d.line([(430,H),(492,430)],fill=(190,196,185,80),width=3)
    if kind=='water':
        d.rectangle((0,405,W,H),fill=(45,73,68,190))
        for _ in range(90):
            y=int(rng.integers(420,H)); x=int(rng.integers(0,W)); ln=int(rng.integers(20,150))
            d.line((x,y,min(W,x+ln),y),fill=(184,203,196,int(rng.integers(10,45))),width=1)
    # rain and fog veil
    for _ in range(520):
        x=int(rng.integers(0,W)); y=int(rng.integers(-30,H)); ln=int(rng.integers(8,30))
        d.line((x,y,x-4,y+ln),fill=(205,218,211,int(rng.integers(18,65))),width=1)
    fog=Image.new('RGBA',(W,H),(0,0,0,0)); fd=ImageDraw.Draw(fog)
    for _ in range(12):
        x=int(rng.integers(-200,W)); y=int(rng.integers(80,H)); rx=int(rng.integers(180,420))
        fd.ellipse((x-rx,y-55,x+rx,y+55),fill=(205,214,208,18))
    im=Image.alpha_composite(im.convert('RGBA'),fog.filter(ImageFilter.GaussianBlur(24))).convert('RGB')
    # Fine film grain keeps the damp, tactile texture after the broad fog blur.
    pix=np.asarray(im).astype(np.int16)
    grain=rng.normal(0,7.0,(H,W,1))
    im=Image.fromarray(np.clip(pix+grain,0,255).astype('uint8'),'RGB')
    im.save(OUT/name,'JPEG',quality=82,optimize=True,progressive=True)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    for args in [('hero-rain-forest.jpg',11,'hero'),('mountain-mist.jpg',23,'forest'),('wet-trekking-trail.jpg',37,'trail'),('quiet-water.jpg',51,'water')]: make(*args)
if __name__=='__main__': main()
