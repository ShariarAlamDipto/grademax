"""Compile and audit the 2019-2026 questions edition; never writes production.

Keep original question/diagram sheets and at most ONE original spare answer
sheet per question. Every removed sheet has a recorded reason. Contents are
regenerated after trimming. Reopen and compare source ink on every kept sheet.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path
from urllib.parse import quote

import fitz
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_requested_yearwise_questions as original
import finish_requested_yearwise_questions as finish
from lib import m1_paper_pages
from lib.ial_chapterwise_sources import Unit, check_qp, check_ms
from lib.watermark_editions import EDITIONS
from lib.workbook_finish import load_watermark, stamp
from lib.yearwise_all_layout import put, header, width, INK, MUTED, MARGIN
from lib.yearwise_all_pages import label_paper, pages_to_keep, trim_box

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'data/yearwise_all/request_2019_2026/completion'
OUT = ROOT / 'output/Yearwise_Questions_2019-2026'
NAMES = {'WMA11': 'Pure Mathematics P1', 'WMA12': 'Pure Mathematics P2',
         'WMA13': 'Pure Mathematics P3', 'WMA14': 'Pure Mathematics P4',
         'WME01': 'Mechanics M1', 'WST01': 'Statistics S1'}
TOKENS = dict(zip(NAMES, ['p1', 'p2', 'p3', 'p4', 'm1', 's1']))
FIRST = {'WMA11': (2019, 'jan'), 'WMA12': (2019, 'may-jun'),
         'WMA13': (2020, 'jan'), 'WMA14': (2020, 'oct-nov'),
         'WME01': (2019, 'jan'), 'WST01': (2019, 'jan')}
SEASONS = ['jan', 'may-jun', 'oct-nov']
LABELS = original.LABELS


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path):
    return path.relative_to(ROOT).as_posix()


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding='utf-8')


def expected(code):
    first = FIRST[code]
    return [(y, s) for y in range(2019, 2027) for s in SEASONS
            if (y, SEASONS.index(s)) >= (first[0], SEASONS.index(first[1]))
            and (y, s) != (2020, 'may-jun')
            and (y, SEASONS.index(s)) <= (2026, 1)]


def download(url, path):
    import httpx
    if not path.exists():
        r = httpx.get(url, follow_redirects=True, timeout=60)
        if r.status_code != 200 or not r.content.startswith(b'%PDF'):
            return None
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(r.content)
    return path


def prepare_sources():
    assets = json.loads((original.WORK / 'ial_catalogue.json').read_text())
    linkage = json.loads((ROOT / 'data/yearwise_all/linkage/ial_pure.json').read_text())
    result = {}
    for code, name in NAMES.items():
        token = TOKENS[code]
        saved = ROOT / 'data/workbook/ial_sources' / token
        records = []
        for year, season in expected(code):
            options = []
            local = saved / f'{year}_{season}'
            if (local / 'QP.pdf').exists():
                options.append(('verified local sources', local / 'QP.pdf', local / 'MS.pdf'))
            for u in linkage:
                if u['unit'] != code:
                    continue
                for s in u['sittings']:
                    if s['sitting'] == f"{year} {dict(zip(SEASONS,['Jan','May-Jun','Oct-Nov']))[season]}" and s['verdict'] == 'LINKED':
                        options.append(('verified linkage', ROOT / s['qp']['path'], ROOT / s['ms']['path']))
            unit = Unit(token=token.upper(), code=code)
            selected = None
            rejected = []
            for origin, qp, ms in options:
                if qp.is_file() and ms.is_file():
                    errors = check_qp(qp, unit, year, season) + check_ms(ms, unit, year, season)
                    if not errors:
                        selected = (origin, qp, ms)
                        break
                    rejected += errors
            if selected is None:
                # Exact URLs from the publisher catalogue; adapted 01A excluded.
                got = {}
                for h in assets:
                    url = h.get('url', '')
                    cats = ' '.join(h.get('category', []))
                    match = re.search(r'Exam-Series/(\w+)-(20\d\d)', cats)
                    if not match:
                        continue
                    hs = {'January':'jan','June':'may-jun','October':'oct-nov'}.get(match[1])
                    if (int(match[2]), hs) != (year, season) or not re.search(rf'{code.lower()}[-_]01[-_]', url.lower()):
                        continue
                    kind = 'QP' if 'Document-Type/Question-paper' in cats else 'MS' if 'Document-Type/Mark-scheme' in cats else None
                    if kind:
                        target = WORK / 'sources' / Path(url).name
                        path = download('https://qualifications.pearson.com' + quote(url, safe='/:-_'), target)
                        if path:
                            got[kind] = path
                if season == 'oct-nov':
                    for kind in ['QP','MS']:
                        if kind in got:
                            continue
                        url = f'https://archive.paperlords.org/library/IAL/Maths/Oct%20{year}/IAL_MATHS_{year}_Oct_{token.upper()}_{kind}.pdf'
                        p = download(url, WORK / 'sources' / f'paperlords_{token}_{year}_oct_{kind}.pdf')
                        if p:
                            got[kind] = p
                if 'QP' in got and 'MS' in got:
                    errors = check_qp(got['QP'], unit, year, season) + check_ms(got['MS'], unit, year, season)
                    if not errors:
                        selected = ('publisher catalogue / original cover', got['QP'], got['MS'])
                    else:
                        rejected += errors
            if not selected:
                raise RuntimeError(f'{code} {year} {season}: missing verified sources; {rejected}')
            origin, qp, ms = selected
            with fitz.open(qp) as d:
                text = '\n'.join(p.get_text() for p in d)
                item = re.search(r'(P\d{5}R{0,2}A)\d{4}', text)
                assert item, f'{qp}: missing paper item code'
                records.append({'year':year, 'season':season, 'paper':1, 'path':rel(qp),
                                'ms_path':rel(ms), 'source':origin, 'pages':len(d),
                                'item':item[1], 'sha256':sha(qp), 'legacy':False})
            print(code, year, season, origin, flush=True)
        assert len({p['item'] for p in records}) == len(records), f'{code}: duplicate paper'
        result[code] = {'subject':name, 'papers':records, 'unfilled_slots':[]}
        dump(WORK / 'ial_inventory.json', result)
    return result


def fast_has_image(page):
    # get_text('dict') decodes every full-resolution scan. Rectangles suffice.
    for im in page.get_image_info():
        b = fitz.Rect(im['bbox'])
        if min(b.width,b.height) >= 40 and max(b.width,b.height)/min(b.width,b.height) <= 5:
            return True
    return False


m1_paper_pages._has_image = fast_has_image


def prepare_fpm():
    info=json.loads((original.WORK/'inventory.json').read_text())['4PM1']
    assets=json.loads((original.WORK/'pearson_catalogue.json').read_text())
    for p in info['papers']:
        with fitz.open(ROOT/p['path']) as d:
            text='\n'.join(page.get_text() for page in d)
        if m1_paper_pages.TOTAL_MODERN.search(text) or m1_paper_pages.TOTAL_LEGACY.search(text):
            continue
        candidates=[a for a in assets if a['code']=='4PM1' and a['kind']=='QP'
                    and (a['year'],a['season'],int(a['variant']))==(p['year'],p['season'],p['paper'])]
        selected=None
        for a in candidates:
            url='https://qualifications.pearson.com'+quote(a['url'],safe='/:-_')
            path=download(url,WORK/'sources'/Path(a['url']).name)
            if not path:continue
            proof=original.check(path,'4PM1',p['year'],p['season'],p['paper'])
            if proof['errors']==['cover date unreadable']:
                proof.update(errors=[],identity='Pearson catalogue and original cover code')
            with fitz.open(path) as d:
                txt='\n'.join(pg.get_text() for pg in d)
            if (p['year'],p['season'],p['paper'],sha(path)) == (2019,'may-jun',1,'f639cc036aaa3937c2acc577b5428f5db315fcf3f22bdd88a382fd80646a15c6'):
                # All 36 original sheets reviewed in fpm_2019_june_p1_review.png.
                # Cover: Monday 17 June 2019, 4PM1/01, P58286A. Total bands
                # independently OCR-read (4+3+6+6+5+11+12+10+12+14+17=100).
                selected={**p,'path':rel(path),'sha256':sha(path),'item':'P58286A',
                          'source':'Pearson original scan; visual page review','identity_url':url,
                          'identity':'visual cover and all-page review', 'errors':[],
                          'manual_scan_review':True}
                break
            if not proof['errors'] and m1_paper_pages.TOTAL_MODERN.search(txt):
                selected={**p,**proof,'path':rel(path),'source':'Pearson accessible-text original','identity_url':url}
                break
        assert selected, f"No readable original for {p['year']} {p['season']} P{p['paper']}"
        p.update(selected)
        print('4PM1 replaced scan with publisher original',p['year'],p['season'],p['paper'],flush=True)
    dump(WORK/'fpm_inventory.json',info)


def trim_paper(p):
    if p.get('manual_scan_review'):
        assert sha(ROOT/p['path'])=='f639cc036aaa3937c2acc577b5428f5db315fcf3f22bdd88a382fd80646a15c6'
        content=[3,4,6,8,10,12,16,20,24,28,32]
        ends=[3,5,7,9,11,15,19,23,27,31,36]
        marks=[4,3,6,6,5,11,12,10,12,14,17]
        kept=sorted(set(content+ends))
        questions=[{'question':q,'marks':m,'content_pages':[a],
                    'answer_pages':[b] if b!=a else []}
                   for q,(a,b,m) in enumerate(zip(content,ends,marks),1)]
        return {**p,'kept_source_pages':kept,'question_audit':questions,'marks':100,
                'removed_pages':[{'source_page':n,'role':'cover' if n==1 else 'reference' if n==2 else 'space',
                                  'question':next((q['question'] for q,e in zip(questions,ends) if n<=e),None)}
                                 for n in range(1,37) if n not in kept]}
    labelled = label_paper(ROOT / p['path'], p['item'])
    assert labelled.base.questions, f"{p['path']}: no readable questions"
    assert not labelled.problems, f"{p['path']}: {labelled.problems}"
    kept = pages_to_keep(labelled, 1)
    indexes = {s.index for s in kept}
    per_question = []
    for q in labelled.base.questions:
        spaces = [s for s in labelled.sheets if s.question == q.number and s.role == 'space' and s.index in indexes]
        assert len(spaces) <= 1, f'{p}: excess answer sides for Q{q.number}'
        per_question.append({'question':q.number, 'marks':q.marks,
                             'answer_pages':[s.index+1 for s in spaces],
                             'content_pages':[s.index+1 for s in kept if s.question==q.number and s.role!='space']})
    removed = [{'source_page':s.index+1, 'role':s.role, 'question':s.question}
               for s in labelled.sheets if s.index not in indexes]
    # Every content page and every question mark tariff survives.
    assert all(s.index in indexes for s in labelled.sheets if s.role in ('start','content','insert'))
    assert all(s.index in indexes for s in labelled.sheets if s.has_total)
    return {**p, 'kept_source_pages':[s.index+1 for s in kept], 'removed_pages':removed,
            'question_audit':per_question, 'marks':labelled.base.total_marks}


def build_compact(code, info):
    print(code, 'classifying original sheets', flush=True)
    papers = [trim_paper(p) for p in info['papers']]
    if code in NAMES:
        assert all(p['marks']==75 for p in papers),f'{code}: question marks do not sum to 75'
    nrows = sum(1 + (i==0 or p['year'] != papers[i-1]['year']) for i,p in enumerate(papers))
    # Every contents page has at most 27 lines; year and paper stay together.
    rows, chunk, oldyear = [], [], None
    for p in papers:
        need = 2 if p['year'] != oldyear else 1
        if len(chunk)+need > 27:
            rows.append(chunk); chunk=[]; oldyear=None
        if p['year'] != oldyear:
            chunk.append(('year',p['year']));oldyear=p['year']
        chunk.append(('paper',p))
    if chunk:
        rows.append(chunk)
    doc = fitz.open()
    name = info['subject']
    level = 'IAL' if code in NAMES else 'IGCSE'
    front = doc.new_page(width=595,height=842)
    front.draw_rect(front.rect, color=None, fill=INK)
    for y,t,size in [(175,'GRADEMAX',21),(235, f'Pearson Edexcel International {"Advanced Level" if level=="IAL" else "GCSE"}',12),
                     (325,name,27),(367,code,17),(452,'YEARWISE QUESTION PAPERS',16),
                     (500,'2019 - 2026',25),(580,f'{len(papers)} papers in chronological order',12)]:
        put(front,MARGIN,y,t,size,True,(1,1,1))
    page=doc.new_page(width=595,height=842)
    put(page,MARGIN,160,name,28,True)
    put(page,MARGIN,205,f'{code} | Yearwise Question Papers',14,True)
    lines=['Question pages and diagrams retain the original exam layout.',
           'Each question keeps at most one additional answer-space page.',
           'Contents show the printed page numbers, with clickable links.',
           'The last included series is May/June 2026.',
           'The cancelled summer 2020 paper appears once as October 2020.']
    if code in ('WMA12','WMA13','WMA14'):
        y,s=FIRST[code];lines.append(f'This unit first sat in {LABELS[s]} {y}; earlier sittings do not exist.')
    for i,line in enumerate(lines):put(page,MARGIN,275+i*31,line,10.5)
    toc_indexes=[doc.new_page(width=595,height=842).number for _ in rows]
    bookmarks=[[1,'Question Papers 2019-2026',1]]
    seen_year=None
    for p in papers:
        p['book_page']=len(doc)+1
        p['printed_page']=len(doc)
        if p['year']!=seen_year:
            bookmarks.append([2,str(p['year']),p['book_page']]);seen_year=p['year']
        bookmarks.append([3,f"{LABELS[p['season']]} {p['year']} | Paper {p['paper']}",p['book_page']])
        with fitz.open(ROOT/p['path']) as source:
            # Direct insertion preserves original layers, vectors, text, and scans.
            for number in p['kept_source_pages']:
                doc.insert_pdf(source,from_page=number-1,to_page=number-1)
        print(code,p['year'],p['season'],p['paper'],p['pages'],'->',len(p['kept_source_pages']),flush=True)
    for index,chunk in zip(toc_indexes,rows):
        page=doc[index]
        put(page,MARGIN,93,'Contents',24,True)
        put(page,MARGIN,122,f'{name} ({code}) | Printed page numbers',10,color=MUTED)
        y=166
        for kind,value in chunk:
            if kind=='year':put(page,MARGIN,y,str(value),12,True)
            else:
                label=f"{LABELS[value['season']]} | Paper {value['paper']}"
                if value['legacy']:label+=' (previous specification)'
                put(page,MARGIN+15,y,label,10)
                put(page,510,y,str(value['printed_page']),10,True)
                page.insert_link({'kind':fitz.LINK_GOTO,'from':fitz.Rect(MARGIN,y-12,550,y+4),'page':value['book_page']-1})
            y+=21
    finish.back_cover(doc,name,code)
    owners={p['book_page']-1+j:p for p in papers for j in range(len(p['kept_source_pages']))}
    blend=doc.get_new_xref();doc.update_object(blend,'<< /Type /ExtGState /BM /Multiply >>')
    mark=load_watermark(EDITIONS[0].artwork);xref=0
    for i in range(1,len(doc)-1):
        page=doc[i]
        finish.crop_bleed(page)
        finish.multiply_original(doc,page,blend)
        w,h=page.rect.width,page.rect.height
        page.draw_rect(fitz.Rect(0,0,w,34),color=None,fill=(1,1,1))
        page.draw_rect(fitz.Rect(0,h-46,w,h),color=None,fill=(1,1,1))
        p=owners.get(i)
        left=f"Paper {p['paper']} | {LABELS[p['season']]} {p['year']}" if p else 'GradeMax | Yearwise Question Papers'
        header(page,left,f'{name} ({code})')
        put(page,(w-width(str(i),9,True))/2,h-18,str(i),9,True)
        put(page,MARGIN,h-18,f'GradeMax | {code} | Yearwise Question Papers',7.2,color=MUTED)
        xref=stamp(page,mark,xref)
    doc.set_toc(bookmarks)
    doc.set_page_labels([{'startpage':0,'prefix':'Front cover'},{'startpage':1,'style':'D','firstpagenum':1},
                         {'startpage':len(doc)-1,'prefix':'Back cover'}])
    doc.set_metadata({'title':f'{name} - Yearwise Questions 2019-2026 - Compact Edition','author':'GradeMax'})
    path=WORK/'staging'/f'GradeMax_{code}_Yearwise_Questions_2019-2026.pdf'
    path.parent.mkdir(parents=True,exist_ok=True)
    doc.save(path,garbage=1,deflate=True);doc.close()
    report={'file':rel(OUT/path.name),'subject':name,'code':code,'level':level,'papers':papers,
            'answer_page_allowance':1,'source_pages':sum(p['pages'] for p in papers),
            'kept_source_pages':sum(len(p['kept_source_pages']) for p in papers),
            'removed_source_pages':sum(len(p['removed_pages']) for p in papers),
            'session_gaps':[]}
    report['verification']=verify_book(path,report)
    dump(WORK/'receipts'/f'{code}.json',report)
    return report


def verify_book(path,report):
    with fitz.open(path) as doc:
        papers=report['papers'];code=report['code']
        assert [t[2] for t in doc.get_toc() if t[0]==3] == [p['book_page'] for p in papers]
        got=[(p['year'],p['season']) for p in papers]
        if code in NAMES:
            assert got==expected(code), f'{code}: incomplete coverage'
        else:
            assert not original.coverage(code,papers)
        assert len({p['item'] for p in papers})==len(papers),'duplicate exam item'
        starts={p['book_page']-1:p for p in papers}
        links=0
        for i in range(1,len(doc)-1):
            pg=doc[i]
            assert pg.get_label()==str(i)
            foot=pg.get_text('dict',flags=fitz.TEXTFLAGS_DICT & ~fitz.TEXT_PRESERVE_IMAGES,
                             clip=fitz.Rect(250,pg.rect.height-30,345,pg.rect.height))
            labels=[s['text'] for b in foot['blocks'] for line in b.get('lines',[]) for s in line['spans']
                    if 'Arial' in s['font'] and abs(s['size']-9)<.1]
            assert labels==[str(i)],f'printed number {i}: {labels!r}'
            for link in pg.get_links():
                if link['kind']!=fitz.LINK_GOTO:continue
                assert link['page'] in starts
                box=link['from'];number=pg.get_text(clip=fitz.Rect(505,box.y0,550,box.y1)).strip()
                assert number==str(link['page']),f'contents number {number}, target {link["page"]}'
                links+=1
        assert links==len(papers)
        compared=0
        for p in papers:
            assert sha(ROOT/p['path'])==p['sha256']
            with fitz.open(ROOT/p['path']) as source:
                for j,num in enumerate(p['kept_source_pages']):
                    before=source[num-1];finish.crop_bleed(before)
                    after=doc[p['book_page']-1+j]
                    body=fitz.Rect(0,34,before.rect.width,before.rect.height-46)
                    assert finish.norm(before.get_text(clip=body))==finish.norm(after.get_text(clip=body)),f'{code}: source text lost'
                    before.get_image_info(xrefs=True);after.get_image_info(xrefs=True)
                    a,b=finish.image_array(before),finish.image_array(after)
                    assert a.shape==b.shape
                    a=a[13:-18];b=b[13:-18]
                    dark=a.max(axis=2)<145
                    loss=dark & (b.min(axis=2)>200)
                    assert np.count_nonzero(loss)<=max(5,np.count_nonzero(dark)*.002),f'{code} source p{num}: ink clipped'
                    compared+=1
        return {'status':'PASS','pages':len(doc),'papers':len(papers),
                'years':sorted({p['year'] for p in papers}),'source_pages_compared':compared,
                'contents_links':'PASS','answer_space_cap':'PASS'}


def audit_existing():
    reports=json.loads((OUT/'build_report.json').read_text())
    results=[]
    for r in reports:
        code=Path(r['file']).name.split('_')[1]
        if code=='4PM1' or code not in original.SUBJECTS:continue
        print(code,'rechecking original formatted book',flush=True)
        v=finish.verify_finished(ROOT/r['file'],r)
        r['verification']=v
        results.append(r)
    dump(WORK/'existing_verified.json',results)
    return results


def optimize_books():
    for receipt in sorted((WORK/'receipts').glob('*.json')):
        r=json.loads(receipt.read_text())
        if r.get('optimization'):
            continue
        path=WORK/'staging'/Path(r['file']).name
        target=path.with_suffix('.optimized.pdf')
        before_size=path.stat().st_size
        with fitz.open(path) as d:
            if not target.exists():
                d.save(target,garbage=4,deflate=True,use_objstms=1)
        with fitz.open(path) as a,fitz.open(target) as b:
            assert len(a)==len(b) and a.get_toc()==b.get_toc()
            for i,(x,y) in enumerate(zip(a,b)):
                assert x.get_text()==y.get_text(),f'optimization text {path.name} {i}'
                assert x.get_label()==y.get_label()
                assert [(k['page'],tuple(k['from'])) for k in x.get_links() if k['kind']==fitz.LINK_GOTO] == [(k['page'],tuple(k['from'])) for k in y.get_links() if k['kind']==fitz.LINK_GOTO]
                assert x.get_pixmap(matrix=fitz.Matrix(.25,.25),alpha=False).samples==y.get_pixmap(matrix=fitz.Matrix(.25,.25),alpha=False).samples, f'optimization render {path.name} {i}'
        target.replace(path)
        r['optimization']={'original_bytes':before_size,'optimized_bytes':path.stat().st_size,
                           'all_page_text_links_render_comparison':'PASS'}
        dump(receipt,r)
        print(path.name,'optimized',round(before_size/1e6,1),'->',round(path.stat().st_size/1e6,1),'MB',flush=True)


def package():
    reports=json.loads((WORK/'existing_verified.json').read_text())
    reports += [json.loads((WORK/'receipts'/f'{c}.json').read_text()) for c in ['4PM1',*NAMES]]
    reports.sort(key=lambda r:Path(r['file']).name)
    assert len(reports)==13 and all(r['verification']['status']=='PASS' for r in reports)
    assert sum(len(r['papers']) for r in reports)==340
    prior_report=WORK/'prior_editions'/'build_report.json'
    if not prior_report.exists():
        prior_report.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(OUT/'build_report.json',prior_report)
    for r in reports:
        path=ROOT/r['file']; staged=WORK/'staging'/path.name
        if staged.exists():
            backup=WORK/'prior_editions'/path.name
            if path.exists() and not backup.exists():
                backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,backup)
            shutil.copy2(staged,path)
    dump(OUT/'build_report.json',reports)
    text=['# Audited yearwise question books, 2019-2026','',
          'Completed 15 October 2026. Includes all expected standard sittings through May/June 2026.',
          'The requested maths units are P1-P4, M1 and S1. Regional/adapted variants and the autumn 2026 series are outside this edition.',
          'P2 starts June 2019, P3 January 2020 and P4 October 2020; these earlier non-existent sittings are not gaps.',
          'Summer 2020 was cancelled; its reissued paper appears once under October 2020.','',
          'Further Pure and all six IAL maths books keep every question/diagram page and at most one original spare answer page per question.',
          'Other subjects retain their original question layouts and English reading inserts.',
          'Every book has printed page numbers, clickable contents and PDF bookmarks. Original source PDFs remain preserved.','',
          '| Subject | Papers | Pages | Source pages removed | Audit |','|---|---:|---:|---:|---|']
    for r in reports:
        code=Path(r['file']).name.split('_')[1]
        name=r.get('subject', original.SUBJECTS.get(code,('',))[0])
        v=r['verification']
        text.append(f'| [{name} ({code})]({Path(r["file"]).name}) | {v["papers"]} | {v["pages"]} | {r.get("removed_source_pages",0)} | {v["status"]} |')
    text += ['', '## Papers per year', '',
             '| Code | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |',
             '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in reports:
        code=Path(r['file']).name.split('_')[1]
        counts=collections.Counter(p['year'] for p in r['papers'])
        text.append('| '+code+' | '+' | '.join(str(counts[y]) if counts[y] else 'N/A' for y in range(2019,2027))+' |')
    text += ['', 'All retained maths source pages were compared with the finished PDF for text and rendered dark ink. Every discarded maths page is listed in build_report.json.',
             'Contents links and printed numbers were checked after compilation. Audit reports are local; no live website or store publication was performed.',
             '', 'The older M1/S1/P4 editions in data/workbook remain archival editions; use the expanded books in this package.',
             '', '[Pearson P2 first-assessment evidence](https://www.pearson.com/content/dam/one-dot-com/one-dot-com/international-schools/pdfs/secondary-curriculum/international-old/maths/iAL_Pure_Maths_2_SB.pdf)',
             '[Pearson IAL Mathematics catalogue](https://qualifications.pearson.com/en/qualifications/edexcel-international-advanced-levels/mathematics-2018.html)']
    text += ['', 'Regenerate locally: `python -u scripts/complete_yearwise_questions.py --build` then `--audit-existing`, `--optimize`, and `--package`.',
             'The audit was also tested against a deleted question page, an incorrect contents link, and a white rectangle covering question text. All three deliberate faults were detected.']
    (OUT/'README.md').write_text('\n'.join(text)+'\n',encoding='utf-8')
    (OUT/'SHA256SUMS.txt').write_text('\n'.join(f'{sha(ROOT/r["file"])}  {Path(r["file"]).name}' for r in reports)+'\n',encoding='utf-8')
    for source,name in [(WORK/'all_maths_preview.png','preview.png'),
                        (WORK/'audit_mutation_checks.json','audit_mutation_checks.json'),
                        (WORK/'dropped_page_audit.json','dropped_page_audit.json')]:
        shutil.copy2(source,OUT/name)
    archive=ROOT/'output/GradeMax_Yearwise_Questions_2019-2026.zip'
    with zipfile.ZipFile(archive.with_suffix('.tmp.zip'),'w',compression=zipfile.ZIP_STORED) as z:
        for r in reports:z.write(ROOT/r['file'],arcname=OUT.name+'/'+Path(r['file']).name)
        for name in ['README.md','build_report.json','SHA256SUMS.txt','preview.png','audit_mutation_checks.json','dropped_page_audit.json']:
            z.write(OUT/name,arcname=OUT.name+'/'+name)
    with zipfile.ZipFile(archive.with_suffix('.tmp.zip')) as z:
        assert z.testzip() is None
        assert sum(n.endswith('.pdf') for n in z.namelist())==13
    archive.with_suffix('.tmp.zip').replace(archive)
    print('Packaged 13 verified books.',flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--prepare',action='store_true');ap.add_argument('--build',nargs='*')
    ap.add_argument('--audit-existing',action='store_true');ap.add_argument('--package',action='store_true')
    ap.add_argument('--prepare-fpm',action='store_true')
    ap.add_argument('--optimize',action='store_true')
    args=ap.parse_args()
    if args.prepare:prepare_sources()
    if args.prepare_fpm:prepare_fpm()
    if args.build is not None:
        inventory=json.loads((original.WORK/'inventory.json').read_text())
        inventory.update(json.loads((WORK/'ial_inventory.json').read_text()))
        if (WORK/'fpm_inventory.json').exists():inventory['4PM1']=json.loads((WORK/'fpm_inventory.json').read_text())
        for c in args.build or ['4PM1',*NAMES]:build_compact(c,inventory[c])
    if args.audit_existing:audit_existing()
    if args.optimize:optimize_books()
    if args.package:package()
