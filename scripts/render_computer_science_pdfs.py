"""Render every staged Computer Science PDF and write visual review sheets."""
import sys, json
from pathlib import Path
import fitz
from PIL import Image, ImageDraw
import numpy as np
sys.path.insert(0,'scripts')
from onboard_igcse_computer_science import BASE, ROOT
rows=json.loads((BASE/'verdicts.json').read_text())['rows']
out=BASE/'review'
out.mkdir(exist_ok=True)
papers=sorted({r['paper'] for r in rows})
all_pages, issues = 0, []
for paper in papers:
    sheet=Image.new('RGB',(1290,2520),'#ddd')
    draw=ImageDraw.Draw(sheet)
    paper_rows=[r for r in rows if r['paper']==paper]
    for idx,(row,kind) in enumerate((r,k) for k in ('qp','ms') for r in paper_rows):
        with fitz.open(ROOT/row[kind]) as doc:
            for page in doc:
                pix=page.get_pixmap(dpi=40,colorspace=fitz.csRGB,alpha=False)
                a=np.frombuffer(pix.samples,dtype=np.uint8).reshape(pix.height,pix.width,3)
                if ((a[:,:,0]>180)&(a[:,:,1]<140)&(a[:,:,2]<140)).mean()>0.004:
                    issues.append(f"{paper} q{row['question']} {kind}: red overlay")
                all_pages+=1
            pix=doc[0].get_pixmap(dpi=60,colorspace=fitz.csRGB,alpha=False)
        img=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
        img.thumbnail((420,595))
        x,y=(idx%3)*430,(idx//3)*630
        sheet.paste(img,(x,y+25))
        draw.text((x+6,y+5),f"{paper} Q{row['question']} {kind}",fill='black')
    sheet.save(out/f'{paper}.png')
(BASE/'render_audit.json').write_text(json.dumps({'pdfs':len(rows)*2,'rendered_pages':all_pages,'failures':issues},indent=2))
print(f'Rendered {all_pages} pages across {len(rows)*2} PDFs; issues: {issues}')
