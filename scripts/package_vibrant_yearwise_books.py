"""Verify and package the vibrant Grade Max series after book generation."""
from __future__ import annotations
import io,json,hashlib,zipfile
from pathlib import Path
import fitz
from PIL import Image,ImageDraw
from reportlab.pdfgen import canvas
import design_vibrant_yearwise_books as d

O=d.OUT;ROOT=d.ROOT

def main():
 rows=json.loads((O/'verification.json').read_text());catalog=json.loads((d.WORK/'catalog.json').read_text())
 assert len(rows)==13 and all(not r['errors'] for r in rows)
 assert sum(r['watermarked_interiors'] for r in rows)==8285
 assert sum(r['numbered_interiors'] for r in rows)==8285
 assert sum(r['toc_links_verified'] for r in rows)==340
 receipts=json.loads((ROOT/'output/Yearwise_Questions_2019-2026/build_report.json').read_text())
 trimmed={'4PM1','WMA11','WMA12','WMA13','WMA14','WME01','WST01'}
 combined=fitz.open()
 for r,b in zip(rows,catalog):
  assert r['code']==b['code']
  assert hashlib.sha256(Path(b['source_pdf']).read_bytes()).hexdigest()==r['source_sha256']
  rec=next(x for x in receipts if Path(x['file']).name==Path(b['source_pdf']).name)
  # Trimmed maths begins with the question; untrimmed sciences begin with an exam cover.
  paper=rec['papers'][0]['book_page']-1+(0 if b['code'] in trimmed else 1)
  with fitz.open(ROOT/r['book']) as full,fitz.open() as sample:
   for index in [2,paper]:sample.insert_pdf(full,from_page=index,to_page=index)
   target=O/'Interior_Samples'/f"{b['code']}_Numbering_Contents_Watermark.pdf"
   if target.exists():target.unlink()
   sample.save(target,garbage=4,deflate=True);combined.insert_pdf(sample)
 target=O/'GradeMax_Interior_Contents_Numbering_Watermark_Proofs.pdf'
 if target.exists():target.unlink()
 combined.save(target,garbage=4,deflate=True);combined.close()
 # Review page for the master and its actual pale, 55%-width application.
 p=O/'Watermark_Application_Study.pdf';c=canvas.Canvas(str(p),pagesize=(595,842),pageCompression=1)
 d.fill(c,d.CREAM);c.rect(0,0,595,842,fill=1,stroke=0)
 d.base.tracked(c,42,797,'GRADE MAX / WATERMARK CHECK',7,1.7,d.DARK)
 d.text(c,42,748,'THE EXACT WORDING.',36,'SairaBold',d.DARK)
 d.safe_body(c,42,714,d.SLOGAN,510,15,21,d.DARK)
 d.text(c,42,658,'WORDING MASTER',13,'SairaBold',d.DARK)
 c.showPage();c.save()
 with fitz.open(p) as page,fitz.open(O/'Watermark_Master.pdf') as master:
  pg=page[0];pg.show_pdf_page(fitz.Rect(80,205,515,316),master,0)
  pg.draw_rect(fitz.Rect(85,392,510,502),color=None,fill=(1,1,1))
  pg.insert_image(fitz.Rect(133.875,405,461.125,488.6664),filename=str(O/'Watermark_Maximize_Your_Marks.png'))
  font=fitz.Font(fontfile=str(d.base.FONT/'SairaCondensed-Regular.ttf'));pg.insert_font(fontname='SairaBody',fontbuffer=font.buffer)
  for y,s in [(380,'ACTUAL PALE MARK - centred at 55% of page width'),(550,'Applied to every interior page, including title and contents pages.'),(573,'Covers retain the branding and slogan without an interior watermark.'),(615,'8,285 watermarked and numbered interior pages.'),(638,'340 contents links verified against their printed destinations.'),(708,'Question text, graphics, page dimensions, bookmarks and page labels preserved.')]:pg.insert_text((42,y),s,fontname='SairaBody',fontsize=12,color=(.06,.17,.20))
  final=O/'Watermark_Application_Study_Final.pdf'
  if final.exists():final.unlink()
  page.save(final,garbage=4,deflate=True)
  pg.get_pixmap(matrix=fitz.Matrix(1.1,1.1)).save(O/'Watermark_Application_Study_Preview.png')
 review=fitz.open()
 for name in ['Colour_Study.pdf','Watermark_Application_Study_Final.pdf']:
  with fitz.open(O/name) as q:review.insert_pdf(q)
 for b in catalog:
  with fitz.open(O/'Covers'/f"{b['code']}_Vibrant_Covers.pdf") as q:review.insert_pdf(q)
 with fitz.open(O/'GradeMax_Interior_Contents_Numbering_Watermark_Proofs.pdf') as q:review.insert_pdf(q)
 assert len(review)==55
 review.set_metadata({'title':'Grade Max - Vibrant Colour Study, Covers and Interior Proofs','author':'Grade Max / Tri Axis Education'})
 final=O/'GradeMax_Vibrant_Review.pdf'
 if final.exists():final.unlink()
 review.save(final,garbage=4,deflate=True);review.close()
 with fitz.open(O/'GradeMax_Interior_Contents_Numbering_Watermark_Proofs.pdf') as proof:
  sheet=Image.new('RGB',(1040,2600),'#e8e5df');draw=ImageDraw.Draw(sheet)
  for i,p in enumerate(proof):
   im=Image.open(io.BytesIO(p.get_pixmap(matrix=fitz.Matrix(.39,.39),alpha=False).tobytes('png')));x=15+(i%4)*259;y=16+(i//4)*365;sheet.paste(im,(x,y));draw.text((x,y+335),rows[i//2]['code']+(' contents' if i%2==0 else ' paper'),fill='#102c33')
  sheet.save(O/'Overview_Interiors.png')
 readme='''# Grade Max vibrant yearwise collection

Current revision: 16 October 2026. This set replaces the subdued cover direction for review; all original PDFs and the earlier design set remain untouched.

## Main files

- GradeMax_Vibrant_Review.pdf: 55 pages with the colour study, watermark application, all 26 front/back covers, and all 26 contents/question samples.
- Covers/: 13 two-page flat covers, one front and one back for every subject.
- Print_Covers_3mm_Bleed/: 13 corresponding cover PDFs with explicit trim/bleed boxes and 3 mm bleed. No assumed spine thickness.
- Books/: all 13 complete question books with vibrant covers and the corrected watermark.
- Watermark_Maximize_Your_Marks.png and Watermark_Master.pdf: the exact requested lockup, matching the existing image dimensions and position.
- verification.json and cover-qa.json: per-book/cover evidence.
- COLOUR-AND-BRANDING-STUDY.md: palette rationale and reference links.

## Required brand and design system

Each front and back carries the original Tri Axis logo, TRI AXIS EDUCATION, GRADE MAX, and Maximize your marks with Grade Max. Condensed display typography and the imprint system connect the covers to the existing workbook family. Vivid full-colour backgrounds, one flat original graphic and a fixed hierarchy give the subjects distinct identities without visual clutter. Main text/background contrast is at least 4.67:1 in the RGB design.

## Watermark, numbering and contents

Every one of the 8,285 interior pages has the corrected pale-grey Maximize your marks with Grade Max watermark and its existing continuous printed page number. The old shared image object is replaced once per book, so there are no stacked old/new marks. Its 2030 x 519 px shape, centred horizontal location and 55% page-width footprint are preserved. Pale ink is encoded in the RGB values, not solely in transparency.

All 340 contents links were checked against their printed page destinations. PDF bookmarks and page labels match the sources. Every interior text/content stream and page geometry matches the source; sampled rendered differences are confined to the intended watermark area and dark question ink remains intact. Original paper sizes can differ by fractions of a point, so footer numbers are checked against each actual page size.

These are question books through May/June 2026. Mark schemes are not bound inside. P2 starts May/June 2019, P3 January 2020, and P4 October/November 2020. The covers use actual audited counts/ranges. Nothing was published or changed in the store.

## Print and reuse

The files use RGB colour. The printer should apply its press/stock profile and confirm binding/cover stock. Large books retain their audited pagination; no unapproved split or spine size has been introduced.

Generate: .venv/Scripts/python.exe -X utf8 scripts/design_vibrant_yearwise_books.py
Recheck unchanged generated books: add --verify-existing
Package the final review and ZIPs: .venv/Scripts/python.exe -X utf8 scripts/package_vibrant_yearwise_books.py

Display fonts are Saira Condensed and IBM Plex Mono from the existing licensed series assets; the original Tri Axis logo is retained. Reference artwork was used for research and was not copied into these designs.
'''
 (O/'README.md').write_text(readme,encoding='utf-8')
 summary={'books':13,'covers':26,'watermarked_and_numbered_interiors':8285,'verified_contents_links':340,'review_pages':55,'originals_unchanged':True,'all_checks_passed':True,'exact_slogan':d.SLOGAN}
 (O/'verification-summary.json').write_text(json.dumps(summary,indent=2))
 with zipfile.ZipFile(O/'GradeMax_Vibrant_Cover_And_Brand_Pack.zip','w',zipfile.ZIP_DEFLATED) as z:
  for folder in ['Covers','Print_Covers_3mm_Bleed','Previews']:
   for p in sorted((O/folder).glob('*')):z.write(p,p.relative_to(O))
  for name in ['GradeMax_Vibrant_Review.pdf','Colour_Study.pdf','Watermark_Master.pdf','Watermark_Maximize_Your_Marks.png','Overview_Fronts.png','Overview_Backs.png','Overview_Interiors.png','COLOUR-AND-BRANDING-STUDY.md','README.md','verification.json','cover-qa.json','verification-summary.json']:z.write(O/name,name)
  z.write(d.base.FONT/'OFL.txt','Font_License_OFL.txt')
 with zipfile.ZipFile(O/'GradeMax_13_Vibrant_Complete_Books.zip','w',zipfile.ZIP_DEFLATED) as z:
  for p in sorted((O/'Books').glob('*.pdf')):z.write(p,p.relative_to(O))
  for name in ['README.md','verification.json','verification-summary.json']:z.write(O/name,name)
 for name in ['GradeMax_Vibrant_Cover_And_Brand_Pack.zip','GradeMax_13_Vibrant_Complete_Books.zip']:
  with zipfile.ZipFile(O/name) as z:assert z.testzip() is None
 print(json.dumps(summary,indent=2),flush=True)
if __name__=='__main__':main()
