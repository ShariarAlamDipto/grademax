"""Vibrant Grade Max series: researched colour system, covers and correct watermarks.

All inputs and earlier editions remain untouched. Run with the project venv.
"""
from __future__ import annotations
import argparse, hashlib, io, json, math, re, sys, zipfile
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import fitz
import numpy as np
from PIL import Image, ImageDraw
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
import design_yearwise_covers as base

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'output/book-cover-redesign-2026-10-16'
OUT=ROOT/'output/pdf/GradeMax_Yearwise_2026_Vibrant'
W,H=595.,842.
BLEED=3*72/25.4
CREAM='#FFF9E9';DARK='#102C33'
SLOGAN='Maximize your marks with Grade Max'
# These are deliberate editorial associations, not claims about colour psychology.
COLOURS={
 '4BI1':('#16B77E','#FFE366','Verdant green','Living systems; fresh, botanical and distinct.'),
 '4CH1':('#7135D2','#C9F37E','Chemical violet','Laboratory precision with a sharp lime counterpoint.'),
 '4EB1':('#FB5A65','#FFD76C','Editorial vermilion','A literary red, with a warm paper-like accent.'),
 '4HB1':('#F27767','#A1E8D1','Human coral','An organic warm hue, separated from botanical green.'),
 '4MB1':('#FF9A31','#8CD7DD','Geometric tangerine','A bright geometric family anchored in warm orange.'),
 '4PH1':('#2458DD','#FFE16B','Electric cobalt','An energetic blue for waves, motion and physical systems.'),
 '4PM1':('#BD268B','#E4ED80','Further fuchsia','A deeper mathematical colour with a precise acid accent.'),
 'WMA11':('#F4CC35','#75C6CC','P1 golden yellow','A clear entry-point colour for the pure-maths sequence.'),
 'WMA12':('#37BDE0','#FFE184','P2 vivid cyan','A cooler next step, kept separate from cobalt physics.'),
 'WMA13':('#7759DF','#B8EBC9','P3 iris violet','An intermediate mathematical colour with a pale mint accent.'),
 'WMA14':('#0BA886','#F3DE76','P4 rich jade','A deeper pure-maths colour, paired with a warm vector accent.'),
 'WME01':('#F06D25','#A6D9E0','Kinetic orange','A warm motion-led colour, stronger than the P1 yellow.'),
 'WST01':('#31C9BA','#FED47A','Statistical turquoise','A lucid cool colour for distributions and data.'),
}
REFS=[
 ('Jim Stoddart: series art direction','https://www.jimstoddart.co.uk/art-direction/series'),
 ('Penguin: the Modern Classics / Marber grid','https://www.penguin.co.uk/discover/articles/penguin-modern-classics-design'),
 ('Penguin: Pelican publishing identity','https://www.penguin.co.uk/about/publishing-houses/penguin-press/pelican'),
 ('Pinterest discovery: Time Life Mathematics','https://www.pinterest.com/pin/431712314270512039/'),
]

def luminance(h):
 v=[int(h[i:i+2],16)/255 for i in (1,3,5)]
 v=[x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in v]
 return .2126*v[0]+.7152*v[1]+.0722*v[2]
def contrast(a,b):
 x,y=sorted([luminance(a),luminance(b)]);return (y+.05)/(x+.05)
def ink(code):
 bg=COLOURS[code][0];return max([CREAM,DARK],key=lambda x:contrast(bg,x))
def fill(c,col):c.setFillColor(base.rgb(col))
def stroke(c,col,width=1):c.setStrokeColor(base.rgb(col));c.setLineWidth(width)
def text(c,x,y,s,size=11,font='Saira',col=DARK):base.txt(c,x,y,s,size,font,col)
def line(c,x1,y1,x2,y2,col,width=.8):base.line(c,x1,y1,x2,y2,col,width)
def polygon(c,pts,col,outline=None,width=1):
 p=c.beginPath();p.moveTo(*pts[0])
 for x,y in pts[1:]:p.lineTo(x,y)
 p.close();fill(c,col);stroke(c,outline or col,width);c.drawPath(p,fill=1,stroke=int(bool(outline)))
def circle(c,x,y,r,col,outline=None,width=1):
 fill(c,col);stroke(c,outline or col,width);c.circle(x,y,r,stroke=int(bool(outline)),fill=1)
def plot(c,pts,col,width=2):base.path(c,pts,col,width)
def ellipse(c,x,y,rx,ry,col,outline=None,width=1):
 fill(c,col);stroke(c,outline or col,width);c.ellipse(x-rx,y-ry,x+rx,y+ry,fill=1,stroke=int(bool(outline)))
def safe_body(c,x,y,s,width=470,size=11,leading=16,col=DARK):return base.body(c,x,y,s,width,size,leading,col)
def title(c,x,y,s,maxwidth,size=62,col=DARK):
 while pdfmetrics.stringWidth(s,'SairaBold',size)>maxwidth:size-=.5
 text(c,x,y,s,size,'SairaBold',col)
def background(c,code):
 fill(c,COLOURS[code][0]);c.rect(-BLEED,-BLEED,W+2*BLEED,H+2*BLEED,fill=1,stroke=0)
def logo(c):
 c.drawImage(str(WORK/'tri-axis-logo.jpeg'),W-101,H-119,width=53,height=65.8,mask='auto')
def footer(c):
 fill(c,CREAM);c.rect(-BLEED,-BLEED,W+2*BLEED,100+BLEED,fill=1,stroke=0)
 base.tracked(c,46,76,'PUBLISHED BY',6.2,1.4,DARK)
 text(c,46,51,'TRI AXIS EDUCATION',17,'SairaBold',DARK)
 base.right(c,W-46,75,'POWERED BY',6.2,'Mono',DARK)
 base.right(c,W-46,49,'GRADE MAX',22,'SairaBold',DARK)
 text(c,46,24,SLOGAN,10,'Saira',DARK)
 base.right(c,W-46,24,'grademax.me',8.5,'Mono',DARK)

def motif(c,code,cx=297.5,cy=389,r=150):
 """One original flat graphic; no textures, glow, stock art or decorative grids."""
 bg,accent,_,_=COLOURS[code];fg=ink(code)
 c.saveState();c.translate(cx,cy);c.scale(r,r)
 def L(a,b,col=fg,w=.012):line(c,*a,*b,col,w)
 def P(p,col=fg,w=.012):plot(c,p,col,w)
 if code=='4BI1':
  # Organic cells with a reduced DNA study: intentional large geometry.
  ellipse(c,-.40,-.10,.49,.70,CREAM)
  ellipse(c,.43,.16,.42,.60,accent)
  circle(c,-.44,.06,.18,bg,fg,.014);circle(c,.40,.26,.14,bg,fg,.014)
  for sign,col in [(1,fg),(-1,fg)]:P([(.05+sign*.22*math.sin(t*math.pi*2),t) for t in np.linspace(-.80,.80,120)],col,.018)
  for t in np.linspace(-.72,.72,13):L((.05-.22*math.sin(t*math.pi*2),t),(.05+.22*math.sin(t*math.pi*2),t),fg,.010)
 elif code=='4HB1':
  # Simplified thoracic anatomy; no medical labels or faux detail.
  for side,col in [(-1,CREAM),(1,accent)]:
   p=c.beginPath();p.moveTo(side*.10,.56);p.curveTo(side*.62,.74,side*.90,-.60,side*.38,-.60);p.curveTo(side*.02,-.62,side*.08,-.05,side*.10,.56)
   fill(c,col);c.drawPath(p,fill=1,stroke=0)
  L((0,.88),(0,.23),fg,.040)
  for side in [-1,1]:
   P([(0,.26),(side*.22,.01),(side*.34,-.33)],fg,.024)
   L((side*.22,.01),(side*.50,.20),fg,.016);L((side*.29,-.18),(side*.55,-.09),fg,.016)
 elif code=='4CH1':
  a=[(.66*math.cos(math.pi/6+i*math.pi/3),.66*math.sin(math.pi/6+i*math.pi/3)) for i in range(6)]
  polygon(c,a,accent)
  P(a+[a[0]],fg,.022)
  for i in [0,2,4]:L((a[i][0]*.80,a[i][1]*.80),(a[(i+1)%6][0]*.80,a[(i+1)%6][1]*.80),fg,.016)
  for i in [0,2,4]:
   x,y=a[i];L((x,y),(x*1.35,y*1.35),fg,.020);circle(c,x*1.35,y*1.35,.10,CREAM)
 elif code=='4EB1':
  # An editorial open-book silhouette, with three deliberate typographic rules.
  for side,col in [(-1,CREAM),(1,accent)]:
   p=c.beginPath();p.moveTo(0,-.56);p.lineTo(side*.83,-.39);p.lineTo(side*.83,.59);p.curveTo(side*.45,.69,side*.20,.56,0,.39);p.close()
   fill(c,col);c.drawPath(p,fill=1,stroke=0)
   for y in [.25,.03,-.19]:L((side*.17,y),(side*.65,y+.09),fg,.022)
  L((0,-.56),(0,.39),fg,.016)
 elif code=='4PH1':
  circle(c,-.32,.10,.68,accent)
  P([(t,.43*math.sin(t*math.pi*2)) for t in np.linspace(-1,1,160)],fg,.036)
  for t in [-.75,-.25,.25,.75]:circle(c,t,.43*math.sin(t*math.pi*2),.037,fg)
  L((-.96,-.68),(.96,-.68),fg,.012)
 elif code=='4MB1':
  # A compact axonometric solid: three flat planes and a geometric diagonal.
  top=[(-.78,.33),(0,.78),(.78,.33),(0,-.12)]
  left=[(-.78,.33),(0,-.12),(0,-.90),(-.78,-.45)]
  right=[(0,-.12),(.78,.33),(.78,-.45),(0,-.90)]
  polygon(c,top,CREAM,fg,.012);polygon(c,left,accent,fg,.012);polygon(c,right,bg,fg,.012)
  L((-.78,-.45),(.78,.33),fg,.020)
 elif code=='4PM1':
  circle(c,0,0,.79,accent)
  polygon(c,[(-.66,-.42),(.73,-.42),(.18,.84)],bg)
  P([(t,.57*math.sin(t*math.pi)) for t in np.linspace(-.92,.92,160)],fg,.025)
  L((-.92,0),(.92,0),fg,.012);L((0,-.88),(0,.88),fg,.012)
 elif code=='WMA11':
  polygon(c,[(-.86,-.58),(.86,-.58),(.86,.78),(-.86,.78)],CREAM)
  L((-.98,-.58),(.98,-.58),fg,.012);L((0,-.78),(0,.95),fg,.012)
  P([(t,1.53*t*t-.58) for t in np.linspace(-.88,.88,120)],fg,.030)
  yp=1.53*.48**2-.58;L((.24,yp+1.4688*(.24-.48)),(.88,yp+1.4688*(.88-.48)),fg,.014);circle(c,.48,yp,.035,bg)
 elif code=='WMA12':
  circle(c,0,0,.83,CREAM)
  P([(t,.46*math.sin(t*math.pi*1.3)) for t in np.linspace(-1,1,160)],fg,.029)
  P([(t,.46*math.cos(t*math.pi*1.3)) for t in np.linspace(-1,1,160)],bg,.020)
  L((-.99,0),(.99,0),fg,.010)
 elif code=='WMA13':
  polygon(c,[(-.80,-.80),(.80,-.80),(.80,.80)],accent)
  L((-.92,-.68),(.92,-.68),fg,.012);L((-.68,-.92),(-.68,.92),fg,.012)
  vals=[(t*.72,(math.exp(t*.8)-1.3)*.54) for t in np.linspace(-.95,.9,120)]
  P(vals,fg,.026);P([(y,x) for x,y in vals],fg,.026)
 elif code=='WMA14':
  a=(-.70,-.55);u=(1.15,.20);v=(.34,1.15)
  polygon(c,[a,(a[0]+u[0],a[1]+u[1]),(a[0]+u[0]+v[0],a[1]+u[1]+v[1]),(a[0]+v[0],a[1]+v[1])],accent)
  for b in [(a[0]+u[0],a[1]+u[1]),(a[0]+v[0],a[1]+v[1]),(a[0]+u[0]+v[0],a[1]+u[1]+v[1])]:base.arrow(c,a,b,fg,.025,.075)
 elif code=='WME01':
  polygon(c,[(-1,-.59),(1,-.59),(1,-.86),(-1,-.86)],accent)
  P([(t,1.13*(1-t*t)-.59) for t in np.linspace(-.94,.94,120)],fg,.032)
  for t in [-.70,-.30,.14,.56]:
   y=1.13*(1-t*t)-.59;circle(c,t,y,.035,CREAM)
   base.arrow(c,(t,y),(t+.16,y-.16*2.26*t),fg,.014,.055)
  base.arrow(c,(0,.45),(0,.05),fg,.020,.07)
 elif code=='WST01':
  pts=[(t,1.30*math.exp(-4.5*t*t)-.60) for t in np.linspace(-1,1,160)]
  polygon(c,[(-1,-.60)]+pts+[(1,-.60)],CREAM)
  polygon(c,[(t,1.30*math.exp(-4.5*t*t)-.60) for t in np.linspace(-.37,.37,70)]+[(.37,-.60),(-.37,-.60)],accent)
  P(pts,fg,.028);L((-1,-.60),(1,-.60),fg,.012)
 c.restoreState()

def front(c,b):
 code=b['code'];fg=ink(code);bg,accent,_,_=COLOURS[code]
 background(c,code);logo(c)
 base.tracked(c,46,791,'THE YEARWISE COLLECTION',7,1.9,fg)
 names=base.TITLES[code]
 if len(names)==1:title(c,43,704,names[0],W-90,86,fg)
 else:
  title(c,43,735,names[0],416,65,fg)
  size=99 if len(names[1])<=2 else 63
  title(c,43,660,names[1],W-90,size,fg)
 level='IGCSE' if b['level']=='IGCSE' else 'INTERNATIONAL A LEVEL'
 base.tracked(c,46,625,f'PEARSON EDEXCEL / {level}',7,1.25,fg)
 line(c,46,608,W-46,608,fg,.7)
 text(c,46,582,f"{code} / YEARWISE QUESTIONS",10,'Mono',fg)
 base.right(c,W-46,582,f"{b['first_session']['year']}-{b['last_session']['year']}",11,'Mono',fg)
 motif(c,code)
 text(c,46,199,f"{b['papers']} EXAM PAPERS  /  {b['sessions_count']} SITTINGS",13,'SairaBold',fg)
 text(c,46,175,'Standard papers through May/June 2026',11,'Saira',fg)
 text(c,46,139,'Compiled by Shariar Alam Dipto',11,'Saira',fg)
 footer(c)

def back(c,b):
 code=b['code'];fg=ink(code);background(c,code);logo(c)
 base.tracked(c,46,791,f"{code} / {b['title'].upper()}",6.8,1.2,fg)
 for i,t in enumerate(['PRACTISE.','REVIEW.','PROGRESS.']):title(c,43,727-i*55,t,420,53,fg)
 line(c,46,586,W-46,586,fg,.7)
 text(c,46,546,str(b['papers']),31,'SairaBold',fg);base.tracked(c,46,527,'EXAM PAPERS',6.5,1.1,fg)
 text(c,213,546,str(b['sessions_count']),31,'SairaBold',fg);base.tracked(c,213,527,'SITTINGS',6.5,1.1,fg)
 text(c,380,548,f"{b['first_session']['year']}-{b['last_session']['year']}",26,'SairaBold',fg);base.tracked(c,380,527,'COVERAGE',6.5,1.1,fg)
 safe_body(c,46,485,'Original exam questions, arranged by year and session. Choose a paper, practise to time, and return to the topics that need work.',472,11.5,17,fg)
 years=b['years'];gap=503/len(years)
 for i,y in enumerate(years):
  x=46+i*gap;fill(c,CREAM);c.rect(x,394,gap-6,30,fill=1,stroke=0);text(c,x+8,403,str(y),13,'SairaBold',DARK)
 steps=[('01','CHOOSE A SITTING','Follow the contents to the year and session you need.'),('02','PRACTISE TO TIME','Use the time and instructions printed on the paper.'),('03','REVIEW AND RETURN','Check the mark scheme online and revisit weak topics.')]
 for i,(num,t,desc) in enumerate(steps):
  y=357-i*61;text(c,46,y,num,10,'Mono',fg);text(c,80,y,t,16,'SairaBold',fg);safe_body(c,80,y-19,desc,447,10.3,15,fg)
 line(c,46,196,W-46,196,fg,.7)
 base.tracked(c,46,176,'MARK SCHEMES & MORE',7,1.4,fg)
 safe_body(c,46,155,'Scan for the subject library. For current printed editions and Bangladesh delivery, visit grademax.me/store.',368,10.5,15,fg)
 text(c,46,112,'Questions edition. Mark schemes are not bound inside.',9,'Saira',fg)
 fill(c,'#FFFFFF');c.rect(W-116,114,70,70,fill=1,stroke=0)
 base.qr(c,'https://www.grademax.me/past-papers/'+base.SLUGS[code],W-113,117,64)
 footer(c)

def covers(b,path,bleed=False):
 buff=io.BytesIO();d=BLEED if bleed else 0;c=canvas.Canvas(buff,pagesize=(W+2*d,H+2*d),pageCompression=1)
 c.setTitle(f"Grade Max {b['title']} - Vibrant series covers");c.setAuthor('Grade Max / Tri Axis Education')
 for fn in [front,back]:c.saveState();c.translate(d,d);fn(c,b);c.restoreState();c.showPage()
 c.save()
 with fitz.open(stream=buff.getvalue(),filetype='pdf') as doc:
  if bleed:
   for p in doc:p.set_trimbox(fitz.Rect(d,d,d+W,d+H));p.set_bleedbox(p.mediabox)
  doc.save(path,garbage=3,deflate=True)

def watermark_art():
 """Exact existing image dimensions; pale colour is in the RGB, never alpha-only."""
 buff=io.BytesIO();c=canvas.Canvas(buff,pagesize=(203,51.9),pageCompression=1)
 c.setTitle(SLOGAN);stroke(c,'#000000',.5);c.line(0,50.3,203,50.3)
 for s,y,size,font in [('Maximize your marks',31.8,23,'SairaBold'),('with',20.8,9,'Saira'),('Grade Max',2.8,24,'SairaBold')]:
  while pdfmetrics.stringWidth(s,font,size)>201:size-=.1
  text(c,(203-pdfmetrics.stringWidth(s,font,size))/2,y,s,size,font,'#000000')
 c.save();(OUT/'Watermark_Master.pdf').write_bytes(buff.getvalue())
 with fitz.open(stream=buff.getvalue(),filetype='pdf') as doc:
  pix=doc[0].get_pixmap(matrix=fitz.Matrix(10,10),alpha=True)
  art=Image.open(io.BytesIO(pix.tobytes('png'))).convert('RGBA');assert art.size==(2030,519)
  a=np.array(art.getchannel('A'));rgb=np.full((519,2030,3),255,dtype=np.uint8);rgb[a>0]=230
  grey=Image.fromarray(rgb);grey.putalpha(Image.fromarray(a));grey.save(OUT/'Watermark_Maximize_Your_Marks.png')
 return {'rgb':rgb.tobytes(),'alpha':a.tobytes(),'width':2030,'height':519}

def normal_toc(d):return [[*r[:3],{k:v for k,v in r[3].items() if k!='xref'}] for r in d.get_toc(False)]
def normal_links(p):return [{k:v for k,v in x.items() if k!='xref'} for x in p.get_links()]
def watermark_xref(d):
 candidates=[]
 for im in d[1].get_images(full=True):
  if im[2:4]==(2030,519) and len(d[1].get_image_rects(im[0]))==1:candidates.append(im[0])
 assert len(set(candidates))==1,('Ambiguous existing watermark',candidates)
 return candidates[0]
def replace_watermark(d,xref,mark):
 mask=d.get_new_xref();d.update_object(mask,f"<< /Type /XObject /Subtype /Image /Width 2030 /Height 519 /ColorSpace /DeviceGray /BitsPerComponent 8 >>");d.update_stream(mask,mark['alpha'],compress=True)
 d.update_object(xref,f"<< /Type /XObject /Subtype /Image /Width 2030 /Height 519 /ColorSpace /DeviceRGB /BitsPerComponent 8 /SMask {mask} 0 R >>")
 d.update_stream(xref,mark['rgb'],compress=True)

def process_book(args):
 b,mark,*options=args;verify_only=bool(options and options[0]);code=b['code'];src=Path(b['source_pdf']);out=OUT/'Books'/src.name;cv=OUT/'Covers'/f'{code}_Vibrant_Covers.pdf'
 source_hash=hashlib.sha256(src.read_bytes()).hexdigest()
 if not verify_only:
  with fitz.open(src) as d,fitz.open(cv) as a:
   wm=watermark_xref(d);replace_watermark(d,wm,mark)
   for i,j in [(0,0),(len(d)-1,1)]:
    p=d[i];xref=d.get_new_xref();d.update_object(xref,'<<>>');d.update_stream(xref,b'');p.set_contents(xref);p.show_pdf_page(p.rect,a,j,keep_proportion=False)
   d.set_metadata({**d.metadata,'title':f"{b['title']} - Yearwise Questions - Grade Max Vibrant Edition",'author':'Grade Max / Tri Axis Education','keywords':SLOGAN})
   d.save(out,garbage=3,deflate=True)
 if len(options)>1 and options[1]:return {'code':code,'book':str(out.relative_to(ROOT)),'authored':True}
 errors=[];numbers=0;wm_count=0;toc_links=0
 receipts=json.loads((ROOT/'output/Yearwise_Questions_2019-2026/build_report.json').read_text(encoding='utf-8'))
 rec=next(r for r in receipts if Path(r['file']).name==src.name)
 sample=set(range(1,b['pages']-1,79))|{1,b['pages']-2}
 sample.update(p['book_page']-1 for p in rec['papers'])
 with fitz.open(src) as old,fitz.open(out) as new:
  if len(old)!=len(new):errors.append('Page count changed')
  if normal_toc(old)!=normal_toc(new):errors.append('Bookmarks changed')
  if old.get_page_labels()!=new.get_page_labels():errors.append('Page labels changed')
  nx=watermark_xref(new)
  if new.xref_stream(nx)!=mark['rgb']:errors.append('Watermark RGB mismatch')
  mask=int(new.xref_get_key(nx,'SMask')[1].split()[0])
  if new.xref_stream(mask)!=mark['alpha']:errors.append('Watermark shape mismatch')
  for i in range(1,len(old)-1):
   a=old[i];z=new[i]
   if a.read_contents()!=z.read_contents():errors.append(f'Page {i} content commands changed')
   ztext=z.get_text()
   if a.get_text()!=ztext:errors.append(f'Page {i} original text changed')
   if a.rect!=z.rect or normal_links(a)!=normal_links(z):errors.append(f'Page {i} geometry/links changed')
   spans=[sp for bl in z.get_text('dict',flags=fitz.TEXTFLAGS_DICT & ~fitz.TEXT_PRESERVE_IMAGES)['blocks'] for li in bl.get('lines',[]) for sp in li['spans']]
   number=[sp for sp in spans if sp['text']==str(i) and abs(sp['origin'][1]-(z.rect.height-18))<.3 and abs((sp['bbox'][0]+sp['bbox'][2])/2-z.rect.width/2)<.6]
   if len(number)==1:numbers+=1
   else:errors.append(f'Printed number missing/duplicated {i}')
   rects=[fitz.Rect(im['bbox']) for im in z.get_image_info(hashes=False) if im['width']==2030 and im['height']==519]
   if len(rects)!=1:errors.append(f'Watermark missing/duplicated on {i}')
   else:
    rr=rects[0]
    if abs(rr.width/W-.55)>.002 or abs((rr.x0+rr.x1)/2-W/2)>1:errors.append(f'Watermark placement changed {i}')
    wm_count+=1
   for link in z.get_links():
    if link['kind']==fitz.LINK_GOTO:
     target=link['page']
     if target<1 or target>=len(new)-1:errors.append(f'Contents link out of range {i}')
     if 'Contents' in ztext[:140]:
      row=z.get_textbox(fitz.Rect(500,link['from'].y0-2,555,link['from'].y1+2)).strip()
      if row!=str(target):errors.append(f'Contents printed target differs {i}: {row!r} vs {target}')
      toc_links+=1
   if i in sample:
    ap=a.get_pixmap(matrix=fitz.Matrix(.6,.6),colorspace=fitz.csGRAY)
    zp=z.get_pixmap(matrix=fitz.Matrix(.6,.6),colorspace=fitz.csGRAY)
    aa=np.frombuffer(ap.samples,dtype=np.uint8).reshape(ap.height,ap.width)
    zz=np.frombuffer(zp.samples,dtype=np.uint8).reshape(zp.height,zp.width)
    # Only the intended watermark footprint may change. Question ink stays dark;
    # edge anti-aliasing within that pale footprint may vary slightly.
    outside=np.ones(aa.shape,dtype=bool)
    rr=rects[0]
    x0=max(0,int(rr.x0*.6)-2);x1=min(ap.width,int(math.ceil(rr.x1*.6))+2)
    y0=max(0,int(rr.y0*.6)-2);y1=min(ap.height,int(math.ceil(rr.y1*.6))+2)
    outside[y0:y1,x0:x1]=False
    if np.any((aa!=zz)&outside):errors.append(f'Pixels changed outside watermark {i}')
    if np.count_nonzero((aa<90)&(zz>135))>5:errors.append(f'Dark question ink lost {i}')
  for p in [new[0],new[-1]]:
   t=p.get_text()
   if not all(s in t for s in ['TRI AXIS EDUCATION','GRADE MAX',SLOGAN]):errors.append('Cover brand/slogan missing')
   if p.get_image_rects(nx):errors.append('Watermark on cover')
  # Compact visual sample: contents and representative paper, numbers unchanged.
  mini=fitz.open()
  for i in [2,rec['papers'][0]['book_page']]:
   if 0<i<len(new)-1:mini.insert_pdf(new,from_page=i,to_page=i)
  mini.save(OUT/'Interior_Samples'/f'{code}_Numbering_Contents_Watermark.pdf',garbage=3,deflate=True)
 if hashlib.sha256(src.read_bytes()).hexdigest()!=source_hash:errors.append('Source file changed')
 return {'code':code,'title':b['title'],'pages':b['pages'],'watermarked_interiors':wm_count,'numbered_interiors':numbers,'toc_links_verified':toc_links,'bookmarks_preserved':not any('Bookmark' in e for e in errors),'source_sha256':source_hash,'sampled_ink_pages':len(sample),'errors':errors,'book':str(out.relative_to(ROOT))}

def colour_study(catalog,path):
 c=canvas.Canvas(str(path),pagesize=(W,H),pageCompression=1)
 fill(c,CREAM);c.rect(0,0,W,H,fill=1,stroke=0)
 base.tracked(c,40,799,'GRADE MAX / COLOUR STUDY',7,1.7,DARK)
 text(c,40,751,'A BRIGHTER SERIES.',39,'SairaBold',DARK)
 safe_body(c,40,718,'A publisher-led system: one vivid background per subject, one flat graphic, a fixed typographic grid and a shared Tri Axis / Grade Max imprint.',515,12,18,DARK)
 y=649
 for idx,b in enumerate(catalog):
  x=40+(idx%2)*265;row=idx//2;yy=y-row*77;code=b['code'];bg,acc,name,reason=COLOURS[code]
  fill(c,bg);c.rect(x,yy-37,47,47,fill=1,stroke=0)
  text(c,x+58,yy+2,code+' / '+b['title'],13,'SairaBold',DARK)
  text(c,x+58,yy-14,name,10,'Saira',DARK)
  text(c,x+58,yy-30,bg+'  |  '+f'{contrast(bg,ink(code)):.1f}:1 ink',7,'Mono',DARK)
 safe_body(c,40,84,'Contrast ratios are calculated for the main text/background pairing as a legibility check; they are not a print-colour certification. Subject associations are editorial choices, not universal psychological rules.',515,9,13,DARK)
 c.showPage();fill(c,CREAM);c.rect(0,0,W,H,fill=1,stroke=0)
 base.tracked(c,40,799,'DESIGN PRINCIPLES / RESEARCH',7,1.7,DARK)
 text(c,40,751,'LESS DECORATION.',39,'SairaBold',DARK);text(c,40,705,'MORE CHARACTER.',39,'SairaBold',DARK)
 y=655
 for head,copy in [('01 / COLOUR IS THE WAYFINDER','The backgrounds carry the subject identity. Typography, alignment, imprint and footer remain fixed across all thirteen books.'),('02 / ONE STRONG GRAPHIC','Original geometric and editorial artwork replaces the dense radial grids. No image-generation output, glow, faux texture or stock illustrations.'),('03 / KEEP THE FAMILY RESEMBLANCE','The same condensed display faces and original Tri Axis logo tie the collection to the existing Maths B and Further Pure workbooks.'),('04 / FIX THE COMPLETE BOOK','Every interior retains its page number and clickable contents. The old shared watermark is replaced once with the exact marks / Grade Max wording.')]:
  text(c,40,y,head,17,'SairaBold',DARK);y=safe_body(c,40,y-22,copy,510,11,16,DARK)-29
 text(c,40,y-4,'REFERENCE DIRECTION',14,'SairaBold',DARK);y-=29
 for name,url in REFS:
  text(c,40,y,name,10.5,'Saira',DARK);c.linkURL(url,(40,y-2,551,y+11),relative=0);y-=20
 safe_body(c,40,72,'References informed the design principles only; their artwork and publisher marks are not reproduced. Pinterest discovery was available as a search image; its page could not be fetched directly. Files remain RGB for the printer to profile.',515,9,13,DARK)
 c.save()

def overview():
 for side in ['Front','Back']:
  fs=sorted((OUT/'Previews').glob('*_'+side+'.png'));sheet=Image.new('RGB',(1120,1660),CREAM);draw=ImageDraw.Draw(sheet)
  for i,p in enumerate(fs):
   im=Image.open(p);im.thumbnail((250,354));x=15+(i%4)*278;y=20+(i//4)*407;sheet.paste(im,(x,y));draw.text((x,y+362),p.stem,fill=DARK)
  sheet.save(OUT/f'Overview_{side}s.png')

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--covers-only',action='store_true');ap.add_argument('--verify-existing',action='store_true');ap.add_argument('--author-only',action='store_true');args=ap.parse_args()
 catalog=json.loads((WORK/'catalog.json').read_text(encoding='utf-8'))
 for f in ['Covers','Print_Covers_3mm_Bleed','Previews','Books','Interior_Samples']:(OUT/f).mkdir(parents=True,exist_ok=True)
 study=OUT/'Colour_Study.pdf';colour_study(catalog,study);mark=watermark_art();proof=fitz.open()
 with fitz.open(study) as d:proof.insert_pdf(d)
 with fitz.open(OUT/'Watermark_Master.pdf') as d:proof.insert_pdf(d)
 for b in catalog:
  code=b['code'];p=OUT/'Covers'/f'{code}_Vibrant_Covers.pdf';covers(b,p);covers(b,OUT/'Print_Covers_3mm_Bleed'/f'{code}_Vibrant_Covers_3mm.pdf',True)
  with fitz.open(p) as d:
   proof.insert_pdf(d)
   for i,side in enumerate(['Front','Back']):d[i].get_pixmap(matrix=fitz.Matrix(1.6,1.6),alpha=False).save(OUT/'Previews'/f'{code}_{side}.png')
 overview();proof.save(OUT/'GradeMax_Vibrant_Colour_Study_And_Cover_Proofs.pdf',garbage=3,deflate=True);proof.close()
 if args.covers_only:return
 if args.author_only:
  with ProcessPoolExecutor(max_workers=3) as pool:
   for r in pool.map(process_book,[(b,mark,False,True) for b in catalog]):print(r['code'],'authored',flush=True)
  return
 with ProcessPoolExecutor(max_workers=3) as pool:
  results=[]
  for r in pool.map(process_book,[(b,mark,args.verify_existing) for b in catalog]):results.append(r);print(r['code'],'PASS' if not r['errors'] else r['errors'][:4],flush=True)
 (OUT/'verification.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
 assert all(not r['errors'] for r in results),'Book checks failed; see verification.json'
 with fitz.open() as d:
  for b in catalog:
   with fitz.open(OUT/'Interior_Samples'/f"{b['code']}_Numbering_Contents_Watermark.pdf") as s:d.insert_pdf(s)
  d.save(OUT/'GradeMax_Interior_Contents_Numbering_Watermark_Proofs.pdf',garbage=3,deflate=True)
 print('All thirteen books verified.',flush=True)
if __name__=='__main__':main()
