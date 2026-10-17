"""Apply the established GradeMax finishing protocol to all seven question books.

Uses the approved GradeMax artwork and shared watermark code: centred,
horizontal, 55% page width, 10% ink, under the page. A numbered title sheet
aligns the existing contents with continuous interior page numbers. Both covers
stay unnumbered and unwatermarked. Originals are backed up; every output is
checked before the seven-book package is replaced.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import shutil
import sys
import zipfile
from pathlib import Path

import fitz
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_requested_yearwise_questions as build
from lib.watermark_editions import EDITIONS
from lib.workbook_finish import load_watermark, stamp, OPACITY, WIDTH_FRACTION
from lib.yearwise_all_layout import INK, MARGIN, MUTED, Volume, header, put, title_page, width
from lib.yearwise_all_pages import trim_box
from lib.yearwise_layout import HEADER_BAND, FOOTER_BAND

ROOT, OUT, WORK = build.ROOT, build.OUT, build.WORK
BACKUP = WORK / "unformatted_books"
STAGING = WORK / "formatted_books"
EDITION = next(e for e in EDITIONS if e.name == "GradeMax")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def norm(text):
    return " ".join(text.replace("\u00a0", " ").split())


def crop_bleed(page):
    if page.rect.width > 620:
        page.set_cropbox(trim_box(page))


def multiply_original(doc, page, blend_xref):
    """Keep a true underlay visible even beneath an opaque scanned white sheet.

    Multiply makes the original white paper show the underlying faint mark;
    original black question text remains black. No source images are edited.
    Only the original content streams use this state: new headers and footers
    retain their normal appearance, and their white bands erase old furniture.
    """
    resource_kind, resource_value = doc.xref_get_key(page.xref, "Resources")
    if resource_kind == "xref":
        resource_value=doc.xref_object(int(resource_value.split()[0]))
    elif resource_kind != "dict":
        raise ValueError(f"page has no usable resource dictionary: {resource_kind}")
    # Composite the whole original page as an isolated transparency group.
    # Source GS operators can reset their own blend mode without concealing
    # the watermark beneath the completed group. Text and images stay intact.
    resource = doc.get_new_xref()
    doc.update_object(resource,resource_value)
    source_form=doc.get_new_xref()
    box=page.mediabox
    doc.update_object(source_form,
        f"<< /Type /XObject /Subtype /Form /FormType 1 "
        f"/BBox [{box.x0} {box.y0} {box.x1} {box.y1}] /Resources {resource} 0 R "
        "/Group << /S /Transparency /I true /K false >> >>")
    doc.update_stream(source_form,b"\n".join(doc.xref_stream(x) for x in page.get_contents()))
    new_resources=doc.get_new_xref()
    # Retain the original font entries as well: PyMuPDF caches page fonts
    # and reuses their names when drawing our added furniture.
    doc.update_object(new_resources,resource_value)
    doc.xref_set_key(new_resources,"XObject",f"<< /GMSource {source_form} 0 R >>")
    doc.xref_set_key(new_resources,"ExtGState",f"<< /GMUnderlayBlend {blend_xref} 0 R >>")
    doc.xref_set_key(page.xref,"Resources",f"{new_resources} 0 R")
    content=doc.get_new_xref()
    doc.update_object(content,"<< >>")
    doc.update_stream(content,b"q\n/GMUnderlayBlend gs\n/GMSource Do\nQ\n")
    doc.xref_set_key(page.xref,"Contents",f"{content} 0 R")


def back_cover(doc, subject, code):
    page = doc.new_page(width=595, height=842)
    page.draw_rect(page.rect, color=None, fill=INK)
    put(page, MARGIN, 650, "GRADEMAX", 19, True, (1, 1, 1))
    put(page, MARGIN, 688, subject, 16, True, (1, 1, 1))
    put(page, MARGIN, 719, f"{code} | Yearwise Question Papers | 2019 - 2026", 11, color=(.8, .82, .86))


def format_book(receipt, reuse_staged=False):
    source = BACKUP / Path(receipt["file"]).name
    out_path = STAGING / source.name
    code = source.name.split("_")[1]
    subject = build.SUBJECTS[code][0]
    if reuse_staged and out_path.exists():
        with fitz.open(source) as original:
            return out_path, formatted_receipt(receipt,source,len(original))
    doc = fitz.open(source)
    old_count = len(doc)
    bookmarks = doc.get_toc()
    links = []
    for i, page in enumerate(doc):
        for link in page.get_links():
            if link["kind"] == fitz.LINK_GOTO:
                links.append((i, dict(link)))
                page.delete_link(link)

    front_matter = fitz.open()
    title_page(front_matter, Volume(subject, code, "IGCSE", "questions", 1, 1, "2019 - 2026"),
               len(receipt["papers"]),
               "Standard question papers arranged by year and session.\n"
               "Contents use the printed page numbers throughout this book.")
    doc.insert_pdf(front_matter, start_at=1)
    front_matter.close()
    back_cover(doc, subject, code)

    for i, link in links:
        original_target = link["page"]
        doc[i + (i > 0)].insert_link({"kind":fitz.LINK_GOTO, "from":link["from"],
                                     "page":original_target + (original_target > 0)})
    doc.set_toc([[level, text, page + (page > 1)] for level, text, page in bookmarks])
    doc.set_page_labels([
        {"startpage":0, "prefix":"Front cover"},
        {"startpage":1, "style":"D", "firstpagenum":1},
        {"startpage":len(doc)-1, "prefix":"Back cover"},
    ])

    owners = {}
    for p in receipt["papers"]:
        for source_index in range(p["pages"]):
            owners[p["book_page"] + source_index] = p
    blend = doc.get_new_xref()
    doc.update_object(blend, "<< /Type /ExtGState /BM /Multiply >>")
    mark = load_watermark(EDITION.artwork)
    watermark_xref = 0
    for printed in range(1, len(doc)-1):
        page = doc[printed]
        crop_bleed(page)
        multiply_original(doc, page, blend)
        w, h = page.rect.width, page.rect.height
        page.draw_rect(fitz.Rect(0,0,w,HEADER_BAND), color=None, fill=(1,1,1))
        page.draw_rect(fitz.Rect(0,h-FOOTER_BAND,w,h), color=None, fill=(1,1,1))
        p = owners.get(printed)
        left = f"Paper {p['paper']} | {build.LABELS[p['season']]} {p['year']}" if p else "GradeMax | Yearwise Question Papers"
        header(page, left, f"{subject} ({code})")
        number = str(printed)
        put(page, (w-width(number,9,True))/2, h-18, number, 9, True)
        footer = f"GradeMax | {code} | Yearwise Question Papers"
        put(page, MARGIN, h-18, footer, 7.2, color=MUTED)
        watermark_xref = stamp(page, mark, watermark_xref)
    doc.set_metadata({**doc.metadata, "title":f"{subject} - Yearwise Questions 2019-2026 - GradeMax Edition"})
    # Resources are deliberately shared already (one watermark image and
    # reused font xrefs); remove unreachable originals without a quadratic
    # search for duplicate objects across these large compilations.
    doc.save(out_path, garbage=1, deflate=True)
    doc.close()

    return out_path, formatted_receipt(receipt,source,old_count)


def formatted_receipt(receipt,source,old_count):
    report = copy.deepcopy(receipt)
    for p in report["papers"]:
        p["printed_page"] = p["book_page"]
        p["book_page"] += 1
    report["formatting"] = {
        "edition":"GradeMax", "watermark":EDITION.wording,
        "watermark_artwork_sha256":sha(EDITION.artwork),
        "watermark_width_fraction":WIDTH_FRACTION, "watermark_ink_opacity":OPACITY,
        "watermark_position":"centred horizontal underlay",
        "page_numbering":"continuous interior 1..N; covers excluded",
        "table_of_contents":"printed page numbers with verified PDF links",
        "source_book_sha256":sha(source), "source_book_pages":old_count,
    }
    return report


def image_array(page):
    pix = page.get_pixmap(matrix=fitz.Matrix(.35,.35), alpha=False)
    return np.frombuffer(pix.samples,dtype=np.uint8).reshape(pix.height,pix.width,3).copy()


def verify_finished(path, report):
    source = BACKUP / path.name
    mark = load_watermark(EDITION.artwork)
    with fitz.open(path) as doc, fitz.open(source) as original:
        assert len(doc) == len(original)+2, "source sheets missing or duplicated"
        toc = doc.get_toc()
        assert [int(t[1]) for t in toc if t[0]==2] == list(range(2019,2027))
        assert [t[2] for t in toc if t[0]==3] == [p["book_page"] for p in report["papers"]]
        assert len(report["papers"]) == len({(p["year"],p["season"],p["paper"]) for p in report["papers"]})
        assert not report.get("session_gaps")
        watermark_xrefs, numbered, visible, fidelity = set(), 0, 0, 0
        for printed in range(1,len(doc)-1):
            page = doc[printed]
            assert abs(page.rect.width-595)<1.5 and abs(page.rect.height-842)<1.5, "page not trimmed to A4"
            target = mark.rect_on(page.rect)
            # Some source pages share resource dictionaries. Count actual
            # painted images rather than aliases declared in those dictionaries.
            marks = [(im["xref"],fitz.Rect(im["bbox"])) for im in page.get_image_info(xrefs=True)
                     if (im["width"],im["height"]) == (mark.width_px,mark.height_px)
                     and max(abs(im["bbox"][k]-target[k]) for k in range(4))<.05]
            assert len(marks)==1, f"missing/duplicate/misplaced watermark on printed p{printed}"
            watermark_xrefs.add(marks[0][0])
            foot = fitz.Rect(page.rect.width*.42,page.rect.height-30,page.rect.width*.58,page.rect.height)
            blocks = page.get_text("dict",clip=foot)["blocks"]
            labels=[span["text"] for block in blocks for line in block.get("lines",[])
                    for span in line["spans"] if "Arial" in span["font"] and abs(span["size"]-9)<.1]
            assert labels==[str(printed)], f"wrong printed number on p{printed}: {labels}"
            assert page.get_label()==str(printed), "PDF page label disagrees with printed number"
            numbered += 1
            for link in page.get_links():
                if link["kind"] != fitz.LINK_GOTO:
                    continue
                area=link["from"]
                digits=norm(page.get_text(clip=fitz.Rect(page.rect.width-80,area.y0,page.rect.width,area.y1)))
                assert digits.isdigit(), "contents page number unreadable"
                assert int(digits)==link["page"], "contents printed number does not match target's printed number"
                assert link["page"]+1 in [p["book_page"] for p in report["papers"]], "contents points outside a paper start"

            # The new numbered title page has no old counterpart.
            if printed==1:
                continue
            before=original[printed-1]
            crop_bleed(before)
            form=int(doc.xref_get_key(page.xref,'Resources/XObject/GMSource')[1].split()[0])
            assert doc.xref_stream(form)==b'\n'.join(original.xref_stream(x) for x in before.get_contents()), f"source drawing commands changed on p{printed}"
            # Image inspection above primes MuPDF's full-resolution image
            # cache. Prime the original identically: otherwise small raster
            # previews can use different image subsampling, especially for
            # Separation-colour photographs in English reading inserts.
            before.get_image_info(xrefs=True)
            body=fitz.Rect(0,HEADER_BAND,page.rect.width,page.rect.height-FOOTER_BAND)
            assert norm(before.get_text(clip=body))==norm(page.get_text(clip=body)), f"question text changed on p{printed}"
            a,b=image_array(before),image_array(page)
            assert a.shape==b.shape, "raster dimensions changed"
            # Source ink remains intact even under the watermark. White space
            # may acquire the faint brand, but existing dark text cannot vanish.
            y0,y1=math.ceil(HEADER_BAND*.35),math.floor((page.rect.height-FOOTER_BAND)*.35)
            ink=a[y0:y1].min(axis=2)<160
            lightening=(b[y0:y1].astype(np.int16)-a[y0:y1].astype(np.int16)).max(axis=2)
            assert not np.any(ink & (lightening>16)), f"source ink obscured on p{printed}"
            difference=np.abs(b.astype(np.int16)-a.astype(np.int16))
            center=difference[max(0,int(target.y0*.35)):math.ceil(target.y1*.35),
                              max(0,int(target.x0*.35)):math.ceil(target.x1*.35)]
            assert np.any(center>0), f"watermark hidden beneath a source background on p{printed}"
            visible += 1
            difference[:y0]=0;difference[y1:]=0
            difference[max(0,int(target.y0*.35)-2):math.ceil(target.y1*.35)+2,
                       max(0,int(target.x0*.35)-2):math.ceil(target.x1*.35)+2]=0
            # A changed PDF graphics state can alter a few pale antialiasing
            # fringe pixels. Require negligible overall change, a tight bound
            # on stronger differences, and preserved dark source ink above.
            stronger=np.count_nonzero(difference.max(axis=2)>16)
            assert (difference.max()<=64 and difference.mean()<=1
                    and stronger<=max(10,a.shape[0]*a.shape[1]*.00025)), f"body content moved/changed outside watermark on p{printed}"
            fidelity += 1
            if printed % 200 == 0:
                print(f"{path.name.split('_')[1]}: verified {printed}/{len(doc)-2} interior pages",flush=True)
        assert len(watermark_xrefs)==1, "watermark image embedded more than once"
        mark_xref=next(iter(watermark_xrefs))
        # Compare to the canonical PDF encoding, including its shape mask.
        # MuPDF zeroes fully transparent RGB pixels and rounds partial alpha
        # during PNG insertion, so a raw PIL RGB comparison is inappropriate.
        with fitz.open() as reference:
            ref_xref=reference.new_page().insert_image(fitz.Rect(0,0,200,100),stream=mark.stream)
            assert fitz.Pixmap(doc,mark_xref).samples==fitz.Pixmap(reference,ref_xref).samples, "wrong watermark artwork/ink colour"
            mask=int(doc.xref_get_key(mark_xref,'SMask')[1].split()[0])
            ref_mask=int(reference.xref_get_key(ref_xref,'SMask')[1].split()[0])
            assert fitz.Pixmap(doc,mask).samples==fitz.Pixmap(reference,ref_mask).samples, "wrong watermark transparency shape"
        for cover in (doc[0],doc[-1]):
            assert not cover.get_image_rects(mark_xref), "watermark leaked onto a cover"
            assert 'Front cover'==doc[0].get_label() and 'Back cover'==doc[-1].get_label()
        return {"status":"PASS", "pages":len(doc), "papers":len(report["papers"]),
                "years":list(range(2019,2027)), "numbered_interior_pages":numbered,
                "watermarked_interior_pages":numbered, "visibly_watermarked_source_pages":visible,
                "source_pages_compared":fidelity, "contents_links":"PASS"}


def package(reports):
    inventory=json.loads((WORK/'inventory.json').read_text(encoding='utf-8'))
    inventory={code:inventory[code] for code in build.SUBJECTS}
    build.write_outputs(inventory,reports)
    readme=OUT/'README.md'
    text=readme.read_text(encoding='utf-8')
    text += ("\nFormatting follows the GradeMax edition protocol: the approved **Maximize your grades with GradeMax** watermark on every interior sheet, centred at 55% page width and 10% ink. Front and back covers are excluded. Every interior page has a continuous printed number and matching PDF page label. Contents entries and links match those printed numbers. Source question ink and English inserts were checked after formatting.\n"
             "\nRun `python scripts/finish_requested_yearwise_questions.py` from the project root to regenerate and verify these editions from the saved unformatted originals. The JSON report records watermark artwork and source hashes, page counts, and verification results.\n")
    readme.write_text(text,encoding='utf-8')
    canvas=Image.new('RGB',(1500,1100),'white')
    for col,code in enumerate(['4PM1','4HB1','4EB1']):
        report=next(r for r in reports if f'_{code}_' in r['file'])
        with fitz.open(ROOT/report['file']) as doc:
            for row,index in enumerate([2,report['papers'][-1]['book_page']]):
                pix=doc[index].get_pixmap(matrix=fitz.Matrix(.65,.65),alpha=False)
                im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
                im.thumbnail((490,540));canvas.paste(im,(col*500,row*550))
    canvas.save(OUT/'preview.png')
    pdfs=[ROOT/r['file'] for r in reports]
    (OUT/'SHA256SUMS.txt').write_text('\n'.join(f'{sha(p)}  {p.name}' for p in pdfs)+'\n',encoding='utf-8')
    archive=ROOT/'output/GradeMax_Yearwise_Questions_2019-2026.zip'
    temporary=archive.with_suffix('.tmp.zip')
    with zipfile.ZipFile(temporary,'w',compression=zipfile.ZIP_STORED) as z:
        for path in pdfs+[OUT/'README.md',OUT/'build_report.json',OUT/'SHA256SUMS.txt',OUT/'preview.png']:
            z.write(path,arcname=OUT.name+'/'+path.name)
    with zipfile.ZipFile(temporary) as z:
        assert z.testzip() is None
        assert sum(name.endswith('.pdf') for name in z.namelist())==7
    temporary.replace(archive)


def main(subjects=None,reuse_staged=False):
    assert EDITION.artwork.is_file(), f"approved artwork missing: {EDITION.artwork}"
    BACKUP.mkdir(parents=True,exist_ok=True);STAGING.mkdir(parents=True,exist_ok=True)
    receipts=json.loads((OUT/'build_report.json').read_text(encoding='utf-8'))
    # Save the unformatted receipts once; subsequent runs always use originals
    # so neither the watermark nor the extra covers/title are applied twice.
    source_report=BACKUP/'build_report.json'
    if not source_report.exists() and not all('formatting' in r for r in receipts):
        source_report.write_text(json.dumps(receipts,indent=2),encoding='utf-8')
        for receipt in receipts:
            if 'formatting' not in receipt:
                shutil.copy2(ROOT/receipt['file'],BACKUP/Path(receipt['file']).name)
    originals=json.loads(source_report.read_text(encoding='utf-8'))
    complete=[]
    for receipt in originals:
        code=Path(receipt['file']).name.split('_')[1]
        if subjects and code not in subjects:
            continue
        print(f'{code}: applying GradeMax watermark, printed numbering and contents links',flush=True)
        path,report=format_book(receipt,reuse_staged)
        report['verification']=verify_finished(path,report)
        complete.append(report)
        (STAGING/'build_report.json').write_text(json.dumps(complete,indent=2),encoding='utf-8')
        print(f"{code}: {report['verification']}",flush=True)
    if subjects:
        return
    assert len(complete)==7 and sum(r['verification']['papers'] for r in complete)==216
    for report in complete:
        shutil.copy2(STAGING/Path(report['file']).name,ROOT/report['file'])
    package(complete)
    print('All seven GradeMax editions verified and packaged.',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--subjects',nargs='+',choices=build.SUBJECTS,help='stage and check a subset before finishing all books')
    parser.add_argument('--reuse-staged',action='store_true',help='recheck existing staged PDFs rather than reformatting them')
    args=parser.parse_args()
    main(args.subjects,args.reuse_staged)
