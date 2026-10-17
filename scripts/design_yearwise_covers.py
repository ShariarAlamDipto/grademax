"""Non-destructive GradeMax yearwise cover collection, 16 October 2026.

Uses the audited 13-book manifest. Generates vector covers, proofs and new book
copies; never alters the source PDFs or their question/contents pages.
Run with .venv/Scripts/python.exe -X utf8 scripts/design_yearwise_covers.py.
"""
from __future__ import annotations
import argparse, io, json, math, hashlib, shutil, zipfile
from pathlib import Path
import fitz
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor, Color
from reportlab.lib.utils import ImageReader
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT/'output/book-cover-redesign-2026-10-16'
OUT = ROOT/'output/pdf/GradeMax_Yearwise_2026_Designed'
W,H = 595.0,842.0
BLEED = 3*72/25.4
INK,CREAM = '#091827','#F2EFE7'
FONT = ROOT/'scripts/lib/fonts'
for name,file in [('Saira','SairaCondensed-Regular.ttf'),('SairaBold','SairaCondensed-SemiBold.ttf'),('Mono','IBMPlexMono-Regular.ttf')]:
    pdfmetrics.registerFont(TTFont(name,str(FONT/file)))
# Helvetica is the built-in body face; all display faces are embedded above.
PALETTES={'4MB1':('#F2B450','#90ABE5'),'4PM1':('#EDAD43','#65C1CC'),
'WMA11':('#DFAE5B','#9AAFE7'),'WMA12':('#52B6D2','#B6CDDF'),
'WMA13':('#B49DDF','#D4BA7D'),'WMA14':('#6DCAA9','#EDBE6B'),
'WME01':('#F19B53','#91C4E0'),'WST01':('#61C4CB','#B4A1DE')}
SLUGS={'4BI1':'biology','4CH1':'chemistry','4EB1':'english-language-b','4HB1':'human-biology','4MB1':'maths-b','4PH1':'physics','4PM1':'further-pure-maths','WMA11':'pure-mathematics-1','WMA12':'pure-mathematics-2','WMA13':'pure-mathematics-3','WMA14':'pure-mathematics-4','WME01':'mechanics-1','WST01':'statistics-1'}
TITLES={'4BI1':['BIOLOGY'],'4CH1':['CHEMISTRY'],'4EB1':['ENGLISH','LANGUAGE B'],
'4HB1':['HUMAN','BIOLOGY'],'4MB1':['MATHEMATICS','B'],'4PH1':['PHYSICS'],
'4PM1':['FURTHER PURE','MATHEMATICS'],'WMA11':['PURE MATHEMATICS','P1'],
'WMA12':['PURE MATHEMATICS','P2'],'WMA13':['PURE MATHEMATICS','P3'],
'WMA14':['PURE MATHEMATICS','P4'],'WME01':['MECHANICS','M1'],'WST01':['STATISTICS','S1']}

def rgb(h):return HexColor(h)
def colour(c,h,stroke=False):
    (c.setStrokeColor if stroke else c.setFillColor)(rgb(h))
def txt(c,x,y,text,size=11,font='Saira',color=INK):
    colour(c,color);c.setFont(font,size);c.drawString(x,y,text)
def right(c,x,y,text,size=11,font='Saira',color=INK):
    colour(c,color);c.setFont(font,size);c.drawRightString(x,y,text)
def tracked(c,x,y,text,size=8,tracking=2,color=INK,font='Mono'):
    colour(c,color);t=c.beginText(x,y);t.setFont(font,size);t.setCharSpace(tracking);t.textOut(text);t.setCharSpace(0);c.drawText(t)
def line(c,x1,y1,x2,y2,color,width=.7):
    colour(c,color,True);c.setLineWidth(width);c.line(x1,y1,x2,y2)
def path(c,points,color,width=1.2,close=False,fill=None):
    p=c.beginPath();p.moveTo(*points[0])
    for xy in points[1:]:p.lineTo(*xy)
    if close:p.close()
    colour(c,color,True);c.setLineWidth(width)
    if fill:colour(c,fill)
    c.drawPath(p,stroke=1,fill=int(bool(fill)))
def arrow(c,a,b,color,width=1.2,head=6):
    line(c,*a,*b,color,width);t=math.atan2(b[1]-a[1],b[0]-a[0])
    path(c,[(b[0]-head*math.cos(t-.45),b[1]-head*math.sin(t-.45)),b,(b[0]-head*math.cos(t+.45),b[1]-head*math.sin(t+.45))],color,width)
def circle(c,x,y,r,color,width=.7,fill=None):
    colour(c,color,True);c.setLineWidth(width)
    if fill:colour(c,fill)
    c.circle(x,y,r,stroke=1,fill=int(bool(fill)))
def wrap(text,size,font,max_width):
    lines=[];cur=''
    for word in text.split():
        test=(cur+' '+word).strip()
        if cur and pdfmetrics.stringWidth(test,font,size)>max_width:lines.append(cur);cur=word
        else:cur=test
    if cur:lines.append(cur)
    return lines

def body(c,x,y,text,width=450,size=11,leading=16,color=INK):
    for row in wrap(text,size,'Helvetica',width):txt(c,x,y,row,size,'Helvetica',color);y-=leading
    return y

def grid(c,dark=True):
    colour(c,INK if dark else CREAM);c.rect(-BLEED,-BLEED,W+2*BLEED,H+2*BLEED,stroke=0,fill=1)
    # Each grid is restrained, keeping the book readable at thumbnail size.
    gc='#142C3D' if dark else '#DEDCD4'
    for x in range(0,int(W)+1,20):line(c,x,0,x,H,gc,.24)
    for y in range(0,int(H)+1,20):line(c,0,y,W,y,gc,.24)
    for x,y,sx,sy in [(23,23,1,1),(W-23,23,-1,1),(23,H-23,1,-1),(W-23,H-23,-1,-1)]:
        line(c,x,y,x+sx*24,y,'#60717B' if dark else '#82949A',.45)
        line(c,x,y,x,y+sy*24,'#60717B' if dark else '#82949A',.45)

def polar_grid(c,cx,cy,r,dark=True):
    cl='#284253' if dark else '#C9D1CC'
    for f in [.25,.5,.75,1]:circle(c,cx,cy,r*f,cl,.45)
    for i in range(24):
        a=i*math.pi/12;line(c,cx+math.cos(a)*r*.16,cy+math.sin(a)*r*.16,cx+math.cos(a)*r,cy+math.sin(a)*r,cl,.35)
    for i in range(60):
        a=i*math.pi/30;r0=r*(.966 if i%5 else .94)
        line(c,cx+r0*math.cos(a),cy+r0*math.sin(a),cx+r*math.cos(a),cy+r*math.sin(a),cl,.5)

def math_art(c,code,cx,cy,r,dark=True):
    a,b=PALETTES[code];muted='#5C7789' if dark else '#A6B5B7'
    polar_grid(c,cx,cy,r,dark)
    # All motifs are vector drawings with a bounded clip.
    c.saveState();p=c.beginPath();p.rect(cx-r,cy-r,2*r,2*r);c.clipPath(p,stroke=0)
    if code=='4MB1':
        rr=r*.69
        circle(c,cx,cy,rr,b,1.5)
        colour(c,b,True);c.setLineWidth(.9)
        c.ellipse(cx-rr,cy+rr*.65,cx+rr,cy+rr*1.18,stroke=1,fill=0)
        c.ellipse(cx-rr,cy-rr*1.18,cx+rr,cy-rr*.65,stroke=1,fill=0)
        line(c,cx-rr,cy+rr*.9,cx-rr,cy-rr*.9,b,.9);line(c,cx+rr,cy+rr*.9,cx+rr,cy-rr*.9,b,.9)
        path(c,[(cx-rr,cy-rr*.9),(cx,cy+rr*.9),(cx+rr,cy-rr*.9)],a,2)
        line(c,cx,cy,cx+rr,cy,a,1.3)
        for k in range(12):
            t=(k+1)/13;line(c,cx,cy+rr*.9,cx-rr+2*rr*t,cy-rr*.9,muted,.28)
    elif code=='4PM1':
        rr=r*.79
        arrow(c,(cx-rr,cy),(cx+rr,cy),b,.8);arrow(c,(cx,cy-rr),(cx,cy+rr),b,.8)
        pts=[(cx+r*.82*t,cy+r*.48*math.sin(math.pi*t)) for t in [i/100 for i in range(-100,101)]];path(c,pts,a,2)
        for i in range(31):
            t=-.95+i*.9/30;line(c,cx+r*.82*t,cy,cx+r*.82*t,cy+r*.48*math.sin(math.pi*t),b,.45)
        theta=.9;end=(cx+rr*.76*math.cos(theta),cy+rr*.76*math.sin(theta));arrow(c,(cx,cy),end,b,1.8)
        path(c,[(cx-r*.60,cy-r*.15),(cx-r*.18,cy-r*.58),(cx+r*.20,cy-r*.20)],a,1.5)
    elif code in ('WMA11','WMA13'):
        arrow(c,(cx-r*.86,cy-r*.55),(cx+r*.87,cy-r*.55),b,.9)
        arrow(c,(cx-r*.55,cy-r*.8),(cx-r*.55,cy+r*.85),b,.9)
        if code=='WMA11':
            pts=[(cx+r*.75*t,cy+r*(.92*t*t-.56)) for t in [i/100 for i in range(-100,101)]];path(c,pts,a,2.2)
            t=.54;tx=cx+r*.75*t;ty=cy+r*(.92*t*t-.56)
            line(c,tx-r*.33,ty-r*.33*(1.84*t/.75),tx+r*.33,ty+r*.33*(1.84*t/.75),b,1.5);circle(c,tx,ty,3,a,1,a)
            for i in range(20):
                x=-.55+i*.85/19;line(c,cx+r*.75*x,cy-r*.56,cx+r*.75*x,cy+r*(.92*x*x-.56),b,.45)
        else:
            pts=[(cx+r*(t-.5)*.85,cy+r*(math.exp(t*.8)-1.4)*.55) for t in [i/100 for i in range(-60,121)]];path(c,pts,a,2)
            pts=[(cx+r*(math.exp(t*.8)-1.4)*.55,cy+r*(t-.5)*.85) for t in [i/100 for i in range(-60,121)]];path(c,pts,b,1.6)
            line(c,cx-r*.65,cy-r*.65,cx+r*.65,cy+r*.65,muted,.6)
    elif code=='WMA12':
        arrow(c,(cx-r*.9,cy),(cx+r*.9,cy),b,.9)
        for phase,cl in [(0,a),(math.pi/2,b)]:
            pts=[(cx+r*.86*t,cy+r*.48*math.sin(math.pi*1.25*t+phase)) for t in [i/120 for i in range(-120,121)]];path(c,pts,cl,1.8)
        for i in range(28):
            t=i/36;line(c,cx+r*.86*t,cy,cx+r*.86*t,cy+r*.48*math.sin(math.pi*1.25*t),a,.5)
    elif code=='WMA14':
        o=(cx-r*.45,cy-r*.35);u=(r*.99,r*.18);v=(r*.25,r*.89)
        d=(o[0]+u[0]+v[0],o[1]+u[1]+v[1])
        path(c,[o,(o[0]+u[0],o[1]+u[1]),d,(o[0]+v[0],o[1]+v[1])],muted,.9,True)
        for i in range(1,8):
            f=i/8;line(c,o[0]+u[0]*f,o[1]+u[1]*f,o[0]+u[0]*f+v[0],o[1]+u[1]*f+v[1],muted,.4)
            line(c,o[0]+v[0]*f,o[1]+v[1]*f,o[0]+v[0]*f+u[0],o[1]+v[1]*f+u[1],muted,.4)
        arrow(c,o,(o[0]+u[0],o[1]+u[1]),a,2);arrow(c,o,(o[0]+v[0],o[1]+v[1]),b,2);arrow(c,o,d,a,2)
        circle(c,*d,3,a,1,a)
    elif code=='WME01':
        base=cy-r*.48;line(c,cx-r*.89,base,cx+r*.89,base,b,1)
        pts=[(cx+r*.82*t,base+r*1.12*(1-t*t)) for t in [i/100 for i in range(-100,101)]];path(c,pts,a,2.2)
        for t in [-.7,-.3,.15,.55]:
            x=cx+r*.82*t;y=base+r*1.12*(1-t*t);circle(c,x,y,3,b,1,b);arrow(c,(x,y),(x+r*.16,y-r*.16*(2.24*t/.82)),b,1.2)
        x=cx;y=base+r*1.12;arrow(c,(x,y-8),(x,y-r*.27),a,1.5)
        for i in range(18):line(c,cx-r*.85+i*r*.10,base,cx-r*.91+i*r*.10,base-r*.06,muted,.5)
    elif code=='WST01':
        base=cy-r*.50;line(c,cx-r*.90,base,cx+r*.90,base,b,.9)
        pts=[(cx+r*.88*t,base+r*1.15*math.exp(-4.5*t*t)) for t in [i/100 for i in range(-100,101)]];path(c,pts,a,2)
        for i in range(-19,20):
            t=i*.028;line(c,cx+r*.88*t,base,cx+r*.88*t,base+r*1.15*math.exp(-4.5*t*t),b,.55)
        for i,h in enumerate([.06,.16,.32,.55,.74,.86,.77,.59,.35,.17,.07]):
            x=cx-r*.81+i*r*.145;colour(c,b,True);c.setLineWidth(.6);c.rect(x,base,r*.135,r*.9*h,stroke=1,fill=0)
    c.restoreState()

def draw_art(c,code,cx,cy,r,dark=True):
    if code in PALETTES:math_art(c,code,cx,cy,r,dark)
    else:
        from lib.yearwise_cover_motifs import draw_motif
        draw_motif(c,code,cx,cy,r,dark)

def palette(code):
    if code in PALETTES:return PALETTES[code]
    from lib.yearwise_cover_motifs import PALETTES as P
    return P[code]['accent'], P[code]['secondary']

def logo(c):
    p=WORK/'tri-axis-logo.jpeg';c.drawImage(str(p),W-108,H-125,width=59,height=73.25,mask='auto')
def footer(c,dark=True):
    muted='#9CB2BF' if dark else '#58737D';text='#F9F5EC' if dark else '#173B49'
    line(c,48,86,W-48,86,'#3C5360' if dark else '#A8B5B4',.65)
    tracked(c,48,65,'PUBLISHED BY',6.5,1.5,muted)
    txt(c,48,44,'TRI AXIS EDUCATION',15,'SairaBold',text)
    right(c,W-48,64,'POWERED BY',7,'Mono',muted)
    right(c,W-48,44,'GRADEMAX',20,'SairaBold',text)
    right(c,W-48,27,'grademax.me',8,'Mono',muted)

def front(c,b):
    code=b['code'];accent,second=palette(code);grid(c,True);logo(c)
    tracked(c,49,788,'THE YEARWISE COLLECTION',7,2,'#F1C277')
    titles=TITLES[code]
    if len(titles)==1:
        size=83
        while pdfmetrics.stringWidth(titles[0],'SairaBold',size)>438:size-=1
        txt(c,46,705,titles[0],size,'SairaBold','#F9F7F1')
    else:
        for i,t in enumerate(titles):
            size=64 if i==0 else 65
            # Upper title leaves the publisher logo its own clear column.
            maxw=420 if i==0 else W-96
            while pdfmetrics.stringWidth(t,'SairaBold',size)>maxw:size-=1
            txt(c,46,736-i*62,t,size,'SairaBold','#F9F7F1' if i==0 else accent)
    line(c,49,651,268,651,accent,2)
    level='IGCSE' if b['level']=='IGCSE' else 'INTERNATIONAL A LEVEL'
    tracked(c,49,629,f'PEARSON EDEXCEL  /  {level}',7,1.3,'#C0D1D8')
    txt(c,49,601,code,12,'Mono',second)
    right(c,W-49,601,f"{b['first_session']['year']}-{b['last_session']['year']}",12,'Mono',accent)
    draw_art(c,code,W/2,397,174,True)
    tracked(c,49,195,'YEARWISE QUESTION BOOK',10.5,1.2,'#F9F7F1','SairaBold')
    txt(c,48,152,f"{b['papers']:02d}",35,'SairaBold',accent)
    txt(c,89,156,'EXAM PAPERS',10,'Mono','#B4C8D3')
    txt(c,274,152,f"{b['sessions_count']:02d}",35,'SairaBold',accent)
    txt(c,315,156,'SITTINGS',10,'Mono','#B4C8D3')
    txt(c,49,124,'Through May/June 2026  |  Standard sittings',10.5,'Saira','#C0D1D8')
    txt(c,49,104,'Compiled by Shariar Alam Dipto',10.5,'Saira','#C0D1D8')
    footer(c,True)

def qr(c,url,x,y,size=62):
    widget=QrCodeWidget(url);bounds=widget.getBounds();d=Drawing(size,size,transform=[size/(bounds[2]-bounds[0]),0,0,size/(bounds[3]-bounds[1]),0,0]);d.add(widget);renderPDF.draw(d,c,x,y)

def back(c,b):
    code=b['code'];accent,second=palette(code);grid(c,False);logo(c)
    tracked(c,49,788,f"{code}  /  {b['title'].upper()}",6.8,1.2,'#55717C')
    txt(c,46,735,'EVERY SITTING.',44,'SairaBold','#103543')
    txt(c,46,687,'A CLEARER PLAN.',44,'SairaBold','#103543')
    body(c,49,651,'A focused collection of exam questions, arranged by year and session. Choose a paper, practise to time, and return to the topics that need work.',width=449,size=11,leading=17,color='#304F5B')
    # Informative stats use only audited facts; no promises about bound solutions.
    line(c,49,576,W-49,576,'#91A6AA',.7)
    for x,n,label in [(49,str(b['papers']),'EXAM PAPERS'),(215,str(b['sessions_count']),'SITTINGS'),(380,f"{b['first_session']['year']}-{b['last_session']['year']}",'COVERAGE')]:
        txt(c,x,535,n,29 if x<380 else 26,'SairaBold','#123948');tracked(c,x,515,label,6.7,1.0,'#5E7A83')
    line(c,49,496,W-49,496,'#91A6AA',.7)
    tracked(c,49,473,'THE YEARS, IN ORDER',7,1.5,'#5D7982')
    ys=b['years'];gap=498/len(ys)
    for i,y in enumerate(ys):
        x=49+i*gap;txt(c,x,447,str(y),15,'SairaBold','#173F4D');line(c,x,438,x+gap-14,438,accent,2)
    c.saveState();c.setStrokeAlpha(.18);c.setFillAlpha(.18);draw_art(c,code,478,285,134,False);c.restoreState()
    tracked(c,49,399,'A PRACTICAL ROUTINE',7,1.4,'#51727D')
    steps=[('01','CHOOSE YOUR PAPER','Use the contents to find a year and session.'),('02','PRACTISE TO TIME','Follow the time and instructions on the paper.'),('03','REVIEW, THEN RETURN','Use the mark scheme online; revisit weak topics.')]
    y=371
    for num,title,desc in steps:
        txt(c,49,y,num,10,'Mono','#B47729');txt(c,80,y,title,15,'SairaBold','#153B49')
        body(c,80,y-17,desc,310,9.5,14,'#47626C');y-=60
    line(c,49,183,W-49,183,'#91A6AA',.7)
    tracked(c,49,160,'MARK SCHEMES & MORE',7,1.5,'#51727D')
    body(c,49,140,'Scan for past papers and mark schemes. Find current printed editions and Bangladesh delivery details at grademax.me/store.',350,9.5,14,'#355560')
    qr(c,'https://www.grademax.me/past-papers/'+SLUGS[code],W-113,105,64)
    txt(c,49,99,'Questions edition. Mark schemes are not bound inside.',8.4,'Saira','#58717B')
    footer(c,False)
    # Rights statement is restrained and never uses an exam-board logo.
    txt(c,49,14,'Independent compilation; not endorsed by Pearson. Original exam material retains its copyright.',7,'Saira','#607882')

def cover_pdf(b,path,bleed=False):
    buff=io.BytesIO();delta=BLEED if bleed else 0
    c=canvas.Canvas(buff,pagesize=(W+2*delta,H+2*delta),pageCompression=1)
    c.setTitle(f"GradeMax {b['title']} - Yearwise front and back covers")
    c.setAuthor('GradeMax / Tri Axis Education')
    for fn in (front,back):
        c.saveState();c.translate(delta,delta);fn(c,b);c.restoreState();c.showPage()
    c.save();data=buff.getvalue()
    with fitz.open(stream=data,filetype='pdf') as d:
        if bleed:
            for p in d:
                p.set_trimbox(fitz.Rect(delta,delta,delta+W,delta+H));p.set_bleedbox(p.mediabox)
        d.save(path,garbage=3,deflate=True)

def apply_cover(b,cover,out):
    """Replace page contents in place; keep original page objects and destinations."""
    with fitz.open(b['source_pdf']) as src, fitz.open(cover) as art:
        for index,artpage in [(0,0),(len(src)-1,1)]:
            p=src[index]
            # A new content stream hides the old cover without touching page tree,
            # labels, bookmarks, internal destinations or any interior page.
            xref=src.get_new_xref();src.update_object(xref,'<<>>');src.update_stream(xref,b'')
            p.set_contents(xref)
            p.show_pdf_page(p.rect,art,artpage,keep_proportion=False)
        src.set_metadata({**src.metadata,'title':f"GradeMax {b['title']} - Yearwise Questions {b['first_session']['year']}-2026",'author':'GradeMax / Tri Axis Education'})
        src.save(out,garbage=3,deflate=True)

def verify_book(b,cover,book):
    errors=[]
    with fitz.open(b['source_pdf']) as old,fitz.open(book) as new,fitz.open(cover) as cv:
        if len(new)!=len(old):errors.append('Page count changed')
        def toc(doc):
            return [[*row[:3], {k:v for k,v in row[3].items() if k!='xref'}] for row in doc.get_toc(False)]
        if toc(old)!=toc(new):errors.append('Contents/bookmark destinations changed')
        if old.get_page_labels()!=new.get_page_labels():errors.append('Page labels changed')
        # Every interior content stream, text and link destination stays identical.
        for i in range(1,len(old)-1):
            if old[i].read_contents()!=new[i].read_contents():errors.append(f'Interior content stream changed: {i}')
            if old[i].rect!=new[i].rect:errors.append(f'Interior dimensions changed: {i}')
            if old[i].get_text()!=new[i].get_text():errors.append(f'Interior text changed: {i}')
            before=[{k:v for k,v in x.items() if k!='xref'} for x in old[i].get_links()]
            after=[{k:v for k,v in x.items() if k!='xref'} for x in new[i].get_links()]
            if before!=after:errors.append(f'Interior links changed: {i}')
        # Pixel-check deterministic samples, including every paper's first page.
        # Byte-identical content streams are checked across ALL interiors above.
        audit=next(x for x in json.loads((ROOT/'output/Yearwise_Questions_2019-2026/build_report.json').read_text(encoding='utf-8')) if Path(x['file']).name==Path(b['source_pdf']).name)
        sample=set(range(1,len(old)-1,37))|{1,len(old)-2}
        sample.update(x['book_page']-1 for x in audit['papers'] if 0<x['book_page']-1<len(old)-1)
        for i in sorted(sample):
            a=old[i].get_pixmap(matrix=fitz.Matrix(.20,.20),colorspace=fitz.csGRAY,alpha=False)
            z=new[i].get_pixmap(matrix=fitz.Matrix(.20,.20),colorspace=fitz.csGRAY,alpha=False)
            if a.samples!=z.samples:errors.append(f'Interior pixels changed: {i}')
        for index,cvi in [(0,0),(len(new)-1,1)]:
            a=new[index].get_pixmap(matrix=fitz.Matrix(.6,.6),alpha=False)
            z=cv[cvi].get_pixmap(matrix=fitz.Matrix(.6,.6),alpha=False)
            if a.samples!=z.samples:errors.append(f'Cover pixels differ: {index}')
        if 'YEARWISE QUESTION BOOK' not in new[0].get_text():errors.append('Front cover title missing')
        if b['code'] not in new[0].get_text():errors.append('Subject code missing')
    if hashlib.sha256(Path(b['source_pdf']).read_bytes()).hexdigest() != b.get('_source_hash', hashlib.sha256(Path(b['source_pdf']).read_bytes()).hexdigest()):errors.append('Original source file changed')
    return errors

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--covers-only',action='store_true');ap.add_argument('--resume',action='store_true');args=ap.parse_args()
    catalog=json.loads((WORK/'catalog.json').read_text(encoding='utf-8'))
    for sub in ['Covers','Print_Covers_3mm_Bleed','Books','Previews']:(OUT/sub).mkdir(parents=True,exist_ok=True)
    results=[];proof=fitz.open()
    for b in catalog:
        stem=f"GradeMax_{b['code']}_Yearwise_2026";trim=OUT/'Covers'/f'{stem}_Covers.pdf';press=OUT/'Print_Covers_3mm_Bleed'/f'{stem}_Covers_3mm.pdf'
        cover_pdf(b,trim);cover_pdf(b,press,True)
        with fitz.open(trim) as d:
            proof.insert_pdf(d)
            for i,label in enumerate(['Front','Back']):d[i].get_pixmap(matrix=fitz.Matrix(1.6,1.6),alpha=False).save(OUT/'Previews'/f"{b['code']}_{label}.png")
        record={'source_sha256':hashlib.sha256(Path(b['source_pdf']).read_bytes()).hexdigest(),'code':b['code'],'title':b['title'],'cover':str(trim.relative_to(ROOT)),'print_cover':str(press.relative_to(ROOT)),'source':b['source_pdf'],'errors':[]}
        if not args.covers_only:
            b['_source_hash']=record['source_sha256']
            out=OUT/'Books'/Path(b['source_pdf']).name
            reusable=False
            if args.resume and out.is_file():
                try:
                    with fitz.open(out) as existing,fitz.open(trim) as art:
                        reusable=len(existing)==b['pages'] and existing[0].get_text()==art[0].get_text() and existing[-1].get_text()==art[1].get_text()
                except Exception:pass
            if not reusable:apply_cover(b,trim,out)
            record['book']=str(out.relative_to(ROOT));record['errors']=verify_book(b,trim,out)
        results.append(record);print(b['code'],'PASS' if not record['errors'] else record['errors'],flush=True)
    proof.save(OUT/'GradeMax_All_13_Cover_Proofs.pdf',garbage=3,deflate=True);proof.close()
    (OUT/'manifest.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    assert not any(x['errors'] for x in results),'Cover/book integrity failed; see manifest.json'
    # Cover-only delivery pack is small enough to share with the printer.
    with zipfile.ZipFile(OUT/'GradeMax_13_Cover_Design_Pack.zip','w',zipfile.ZIP_DEFLATED) as z:
        for folder in ['Covers','Print_Covers_3mm_Bleed','Previews']:
            for p in sorted((OUT/folder).glob('*')):z.write(p,p.relative_to(OUT))
        for name in ['GradeMax_All_13_Cover_Proofs.pdf','manifest.json']:z.write(OUT/name,name)
    print('Saved',OUT,flush=True)
if __name__=='__main__':main()
