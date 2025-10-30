"""
Physics Segmentation Rule Validator

Tests the segmentation rules on sample papers and validates:
1. Question count is reasonable (not too many/few)
2. Question numbers are sequential
3. Each question has mark scheme pages
4. No duplicate question numbers
5. Question page ranges make sense

Provides detailed feedback for rule refinement.
"""

import os
import sys
import json
from pathlib import Path
from collections import Counter
import pdfplumber
import re

# Load rules
RULES_PATH = Path(__file__).parent.parent / "config" / "physics_segmentation_rules.json"

with open(RULES_PATH, 'r', encoding='utf-8') as f:
    RULES = json.load(f)

RAW_DATA_DIR = Path("data/raw/IGCSE/Physics")


def extract_lines_with_positions(pdf_path):
    """Extract text lines with position information."""
    pages_data = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                words = page.extract_words(x_tolerance=3, y_tolerance=3)
                
                # Group into lines by y-position
                lines = {}
                for word in words:
                    y_pos = round(word['top'], 1)
                    if y_pos not in lines:
                        lines[y_pos] = []
                    lines[y_pos].append(word)
                
                # Sort lines top to bottom
                page_lines = []
                for y_pos in sorted(lines.keys()):
                    line_words = lines[y_pos]
                    line_text = " ".join([w['text'] for w in line_words])
                    min_x = min([w['x0'] for w in line_words])
                    
                    page_lines.append({
                        "text": line_text,
                        "x_pos": min_x,
                        "y_pos": y_pos
                    })
                
                pages_data.append({
                    "page_index": page_num,
                    "lines": page_lines
                })
    
    except Exception as e:
        print(f"Error extracting from {pdf_path}: {e}")
    
    return pages_data


def segment_qp_questions(qp_pages_data):
    """Segment QP using current rules."""
    questions = []
    current_question = None
    
    start_pattern = re.compile(RULES['qp_rules']['question_start']['text_pattern'])
    end_pattern = RULES['qp_rules']['question_end']['primary_pattern']
    max_qnum = RULES['qp_rules']['question_start'].get('max_question_number', 20)
    
    for page_data in qp_pages_data:
        page_idx = page_data['page_index']
        
        for line in page_data['lines']:
            text = line['text'].strip()
            x_pos = line['x_pos']
            
            # Position validation - updated for 2011-2024 papers
            if x_pos < 40 or x_pos > 170:
                continue
            
            # Check for question start
            if start_pattern.match(text):
                qnum_str = text.split()[0].rstrip('.')
                
                try:
                    qnum_int = int(qnum_str)
                    if qnum_int < 1 or qnum_int > max_qnum:
                        continue
                except:
                    continue
                
                if current_question:
                    questions.append(current_question)
                
                current_question = {
                    "qnum": qnum_str,
                    "start_page": page_idx,
                    "qp_pages": [page_idx],
                    "start_text": text[:80]  # For validation
                }
            
            elif end_pattern in text and current_question:
                current_question['end_page'] = page_idx
                current_question['end_text'] = text[:80]
                if page_idx not in current_question['qp_pages']:
                    current_question['qp_pages'].append(page_idx)
            
            elif current_question and page_idx not in current_question['qp_pages']:
                current_question['qp_pages'].append(page_idx)
    
    if current_question:
        questions.append(current_question)
    
    return questions


def link_ms_pages(questions, ms_pages_data):
    """Link MS pages using improved rules."""
    ms_total_pattern = re.compile(r"Total for [Qq]uestion (\d+)", re.IGNORECASE)
    
    # Get rules
    x_min, x_max = RULES['ms_rules']['question_detection']['x_range']
    intro_keywords = RULES['ms_rules']['page_detection']['intro_keywords']
    
    ms_sections = {}
    current_qnum = None
    in_content = False
    
    for page_data in ms_pages_data:
        page_idx = page_data['page_index']
        
        # Check if past intro
        page_text = " ".join([line['text'] for line in page_data['lines']])
        
        if not in_content:
            if any(keyword in page_text for keyword in intro_keywords):
                continue
            if "Question" in page_text and "Answer" in page_text and "Marks" in page_text:
                in_content = True
                # Process this page - it may contain Q1
        
        if not in_content:
            continue
        
        # Find question numbers
        for line in page_data['lines']:
            text = line['text'].strip()
            x_pos = line['x_pos']
            
            if x_pos < x_min or x_pos > x_max:
                continue
            
            match = re.match(r'^(\d+)\s*[\(]?[a-z]?', text)
            if match and len(text.split()[0]) <= 3:
                qnum = match.group(1)
                
                if text.startswith(qnum + " ") or text.startswith(qnum + "("):
                    current_qnum = qnum
                    if current_qnum not in ms_sections:
                        ms_sections[current_qnum] = []
            
            match = ms_total_pattern.search(text)
            if match:
                end_qnum = match.group(1)
                if end_qnum in ms_sections and page_idx not in ms_sections[end_qnum]:
                    ms_sections[end_qnum].append(page_idx)
                current_qnum = None
        
        if current_qnum:
            if page_idx not in ms_sections.get(current_qnum, []):
                if current_qnum not in ms_sections:
                    ms_sections[current_qnum] = []
                ms_sections[current_qnum].append(page_idx)
    
    for question in questions:
        qnum = question['qnum']
        question['ms_pages'] = sorted(set(ms_sections.get(qnum, [])))
    
    return questions


def validate_segmentation(paper_info, questions):
    """
    Validate the segmentation and return detailed feedback.
    
    Returns: dict with validation results and issues
    """
    validation = {
        "paper": paper_info,
        "num_questions": len(questions),
        "issues": [],
        "warnings": [],
        "stats": {},
        "passed": True
    }
    
    # Check 1: Question count
    if len(questions) == 0:
        validation['issues'].append("❌ No questions detected")
        validation['passed'] = False
    elif len(questions) < 5:
        validation['warnings'].append(f"⚠️  Only {len(questions)} questions detected (expected 7-15)")
    elif len(questions) > 20:
        validation['issues'].append(f"❌ Too many questions: {len(questions)} (expected 7-15)")
        validation['passed'] = False
    
    # Check 2: Sequential question numbers
    qnums = [int(q['qnum']) for q in questions]
    qnums_sorted = sorted(qnums)
    
    if qnums != qnums_sorted:
        validation['warnings'].append(f"⚠️  Question numbers not sequential: {qnums}")
    
    # Check 3: Duplicate question numbers
    duplicates = [num for num, count in Counter(qnums).items() if count > 1]
    if duplicates:
        validation['issues'].append(f"❌ Duplicate question numbers: {duplicates}")
        validation['passed'] = False
    
    # Check 4: Question number gaps
    expected_range = range(1, max(qnums) + 1)
    missing = [n for n in expected_range if n not in qnums]
    if missing and len(missing) < 5:  # Allow some gaps
        validation['warnings'].append(f"⚠️  Missing question numbers: {missing}")
    
    # Check 5: Mark scheme linking
    no_ms = [q['qnum'] for q in questions if not q.get('ms_pages')]
    if no_ms:
        if len(no_ms) > len(questions) * 0.3:  # More than 30% have no MS
            validation['issues'].append(f"❌ {len(no_ms)}/{len(questions)} questions have no mark schemes")
            validation['passed'] = False
        else:
            validation['warnings'].append(f"⚠️  {len(no_ms)} questions missing mark schemes: {no_ms}")
    
    # Check 6: Question page ranges
    for q in questions:
        num_pages = len(q['qp_pages'])
        if num_pages > 10:
            validation['warnings'].append(f"⚠️  Q{q['qnum']} spans {num_pages} pages (seems too many)")
        elif num_pages == 0:
            validation['issues'].append(f"❌ Q{q['qnum']} has no pages")
            validation['passed'] = False
    
    # Stats
    validation['stats'] = {
        "avg_pages_per_question": sum(len(q['qp_pages']) for q in questions) / len(questions) if questions else 0,
        "questions_with_ms": len([q for q in questions if q.get('ms_pages')]),
        "total_qp_pages": paper_info.get('qp_pages', 0),
        "total_ms_pages": paper_info.get('ms_pages', 0)
    }
    
    return validation


def test_paper(year, season, paper_num, qp_path, ms_path):
    """Test segmentation on a single paper."""
    print(f"\n{'='*80}")
    print(f"Testing: {year} {season} Paper {paper_num}")
    print(f"{'='*80}")
    
    # Extract layout
    qp_data = extract_lines_with_positions(qp_path)
    ms_data = extract_lines_with_positions(ms_path)
    
    paper_info = {
        "year": year,
        "season": season,
        "paper": paper_num,
        "qp_pages": len(qp_data),
        "ms_pages": len(ms_data)
    }
    
    print(f"  QP: {len(qp_data)} pages, MS: {len(ms_data)} pages")
    
    # Segment
    questions = segment_qp_questions(qp_data)
    questions = link_ms_pages(questions, ms_data)
    
    # Validate
    validation = validate_segmentation(paper_info, questions)
    
    # Display results
    print(f"\n  📊 Results:")
    print(f"     Questions detected: {validation['num_questions']}")
    print(f"     With mark schemes: {validation['stats']['questions_with_ms']}/{validation['num_questions']}")
    print(f"     Avg pages/question: {validation['stats']['avg_pages_per_question']:.1f}")
    
    # Show sample questions
    print(f"\n  📝 Sample Questions:")
    for q in questions[:5]:
        print(f"     Q{q['qnum']}: {len(q['qp_pages'])} QP pages, {len(q.get('ms_pages', []))} MS pages")
        print(f"       Start: {q.get('start_text', 'N/A')[:60]}...")
        if 'end_text' in q:
            print(f"       End: {q.get('end_text', '')[:60]}...")
    
    if len(questions) > 5:
        print(f"     ... and {len(questions) - 5} more")
    
    # Show issues
    if validation['issues']:
        print(f"\n  ❌ Issues:")
        for issue in validation['issues']:
            print(f"     {issue}")
    
    if validation['warnings']:
        print(f"\n  ⚠️  Warnings:")
        for warning in validation['warnings']:
            print(f"     {warning}")
    
    if validation['passed'] and not validation['warnings']:
        print(f"\n  ✅ VALIDATION PASSED")
    elif validation['passed']:
        print(f"\n  ✅ PASSED (with warnings)")
    else:
        print(f"\n  ❌ VALIDATION FAILED")
    
    return validation


def analyze_validation_results(results):
    """Analyze all validation results and suggest rule improvements."""
    print(f"\n\n{'='*80}")
    print("VALIDATION ANALYSIS")
    print(f"{'='*80}")
    
    total_papers = len(results)
    passed = sum(1 for r in results if r['passed'])
    
    print(f"\n📊 Overall Results:")
    print(f"   Tested: {total_papers} papers")
    print(f"   Passed: {passed}/{total_papers} ({passed/total_papers*100:.1f}%)")
    
    # Collect common issues
    all_issues = []
    all_warnings = []
    
    for r in results:
        all_issues.extend(r['issues'])
        all_warnings.extend(r['warnings'])
    
    if all_issues:
        print(f"\n❌ Common Issues:")
        issue_counts = Counter(all_issues)
        for issue, count in issue_counts.most_common(5):
            print(f"   [{count}x] {issue}")
    
    if all_warnings:
        print(f"\n⚠️  Common Warnings:")
        warning_counts = Counter(all_warnings)
        for warning, count in warning_counts.most_common(5):
            print(f"   [{count}x] {warning}")
    
    # Stats
    avg_questions = sum(r['num_questions'] for r in results) / len(results)
    avg_with_ms = sum(r['stats']['questions_with_ms'] for r in results) / len(results)
    
    print(f"\n📈 Statistics:")
    print(f"   Avg questions per paper: {avg_questions:.1f}")
    print(f"   Avg questions with MS: {avg_with_ms:.1f}")
    
    # Suggestions
    print(f"\n💡 Rule Improvement Suggestions:")
    
    if avg_questions < 8:
        print(f"   • Questions under-detected (avg {avg_questions:.1f})")
        print(f"     → Check if regex pattern is too strict")
        print(f"     → Check if position rules (x_pos) are too narrow")
    
    if avg_questions > 15:
        print(f"   • Questions over-detected (avg {avg_questions:.1f})")
        print(f"     → Pattern may be matching non-question numbers")
        print(f"     → Consider stricter validation")
    
    if avg_with_ms < avg_questions * 0.7:
        print(f"   • MS linking weak ({avg_with_ms:.1f}/{avg_questions:.1f})")
        print(f"     → MS detection pattern needs refinement")
        print(f"     → Check MS table structure recognition")
    
    non_sequential = sum(1 for r in results if any('not sequential' in w for w in r['warnings']))
    if non_sequential > 0:
        print(f"   • {non_sequential} papers have non-sequential questions")
        print(f"     → May be detecting incorrect question starts")


def main():
    """Main validator function."""
    print("="*80)
    print("PHYSICS SEGMENTATION RULE VALIDATOR")
    print("="*80)
    print(f"\nRules version: {RULES['version']}")
    print(f"Description: {RULES['description']}\n")
    
    # Test papers from different years - expanded set
    test_papers = [
        # Old papers
        {
            "year": 2011,
            "season": "May-Jun",
            "paper": 1,
            "qp": r"data\raw\IGCSE\Physics\2011\May-Jun\Paper 1.pdf",
            "ms": r"data\raw\IGCSE\Physics\2011\May-Jun\Paper 1_MS.pdf"
        },
        {
            "year": 2012,
            "season": "Jan",
            "paper": 2,
            "qp": r"data\raw\IGCSE\Physics\2012\Jan\Paper 2.pdf",
            "ms": r"data\raw\IGCSE\Physics\2012\Jan\Paper 2_MS.pdf"
        },
        {
            "year": 2013,
            "season": "May-Jun",
            "paper": 1,
            "qp": r"data\raw\IGCSE\Physics\2013\May-Jun\Paper 1.pdf",
            "ms": r"data\raw\IGCSE\Physics\2013\May-Jun\Paper 1_MS.pdf"
        },
        # Mid papers
        {
            "year": 2015,
            "season": "Jan",
            "paper": 1,
            "qp": r"data\raw\IGCSE\Physics\2015\Jan\Paper 1.pdf",
            "ms": r"data\raw\IGCSE\Physics\2015\Jan\Paper 1_MS.pdf"
        },
        {
            "year": 2017,
            "season": "May-Jun",
            "paper": 2,
            "qp": r"data\raw\IGCSE\Physics\2017\May-Jun\Paper 2.pdf",
            "ms": r"data\raw\IGCSE\Physics\2017\May-Jun\Paper 2_MS.pdf"
        },
        {
            "year": 2018,
            "season": "Jan",
            "paper": 1,
            "qp": r"data\raw\IGCSE\Physics\2018\Jan\Paper 1.pdf",
            "ms": r"data\raw\IGCSE\Physics\2018\Jan\Paper 1_MS.pdf"
        },
        {
            "year": 2019,
            "season": "May-Jun",
            "paper": 1,
            "qp": r"data\raw\IGCSE\Physics\2019\May-Jun\Paper 1.pdf",
            "ms": r"data\raw\IGCSE\Physics\2019\May-Jun\Paper 1_MS.pdf"
        },
        # Recent papers
        {
            "year": 2020,
            "season": "Jan",
            "paper": 1,
            "qp": r"data\raw\IGCSE\Physics\2020\Jan\Paper 1.pdf",
            "ms": r"data\raw\IGCSE\Physics\2020\Jan\Paper 1_MS.pdf"
        },
        {
            "year": 2021,
            "season": "May-Jun",
            "paper": 2,
            "qp": r"data\raw\IGCSE\Physics\2021\May-Jun\Paper 2.pdf",
            "ms": r"data\raw\IGCSE\Physics\2021\May-Jun\Paper 2_MS.pdf"
        },
        {
            "year": 2022,
            "season": "May-Jun",
            "paper": 2,
            "qp": r"data\raw\IGCSE\Physics\2022\May-Jun\Paper 2.pdf",
            "ms": r"data\raw\IGCSE\Physics\2022\May-Jun\Paper 2_MS.pdf"
        },
        {
            "year": 2023,
            "season": "Jan",
            "paper": 1,
            "qp": r"data\raw\IGCSE\Physics\2023\Jan\Paper 1.pdf",
            "ms": r"data\raw\IGCSE\Physics\2023\Jan\Paper 1_MS.pdf"
        },
        {
            "year": 2024,
            "season": "May-Jun",
            "paper": 1,
            "qp": r"data\raw\IGCSE\Physics\2024\May-Jun\Paper 1.pdf",
            "ms": r"data\raw\IGCSE\Physics\2024\May-Jun\Paper 1_MS.pdf"
        }
    ]
    
    results = []
    
    for paper in test_papers:
        if not Path(paper['qp']).exists() or not Path(paper['ms']).exists():
            print(f"\n⚠️  Skipping {paper['year']} {paper['season']} Paper {paper['paper']} - files not found")
            continue
        
        try:
            result = test_paper(
                paper['year'],
                paper['season'],
                paper['paper'],
                paper['qp'],
                paper['ms']
            )
            results.append(result)
        except Exception as e:
            print(f"\n❌ Error testing paper: {e}")
            import traceback
            traceback.print_exc()
    
    if results:
        analyze_validation_results(results)
        
        # Save validation report
        report_path = Path(__file__).parent.parent / "config" / "validation_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n📄 Detailed report saved to: {report_path}")
    else:
        print("\n❌ No papers were successfully tested")


if __name__ == "__main__":
    main()
