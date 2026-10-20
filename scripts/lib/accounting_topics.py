"""IGCSE Accounting (4AC1) chapter taxonomy for the test builder and worksheet generator.

Codes are the 4AC1 specification sections (Issue 1, October 2016, pp. 13-23).
Topic 5 repeats two Paper 1 sections word for word -- 5.1 "Application of
accounting concepts" is 1.2 and 5.2 "Depreciation" is 2.5 -- so those two are
served once, under their first code, and a student filtering on Depreciation
gets every depreciation question from both papers. That leaves 20 chapters,
matching the 18-topic Chapterwise Formats booklet plus the two Topic 1
sections it does not cover (technology, ethics).

The lexicon only PROPOSES chapters for the reviewer; nothing is published from
it without a recorded read (classify_accounting_tool_topics.py).
"""
from __future__ import annotations

import re

SUBJECT_ID = '488dbe3c-f9fd-41c7-88e5-69afa4e94caa'
CODE = '4AC1'

# code -> (name, specification topic it belongs to)
CHAPTERS: dict[str, tuple[str, str]] = {
    '1.1': ('Types of business organisation', 'The accounting environment'),
    '1.2': ('Accounting concepts', 'The accounting environment'),
    '1.3': ('Use of technology in accounting', 'The accounting environment'),
    '1.4': ('Professional ethics', 'The accounting environment'),
    '2.1': ('Business documentation', 'Introduction to bookkeeping'),
    '2.2': ('Books of original entry', 'Introduction to bookkeeping'),
    '2.3': ('Ledger accounting', 'Introduction to bookkeeping'),
    '2.4': ('Capital and revenue expenditure', 'Introduction to bookkeeping'),
    '2.5': ('Depreciation', 'Introduction to bookkeeping'),
    '3.1': ('Trial balance', 'Introduction to control processes'),
    '3.2': ('Control accounts', 'Introduction to control processes'),
    '3.3': ('Correction of errors', 'Introduction to control processes'),
    '3.4': ('Bank reconciliation statements', 'Introduction to control processes'),
    '4.1': ('Financial statements of a sole trader', 'The preparation of financial statements'),
    '4.2': ('Financial statements of a partnership', 'The preparation of financial statements'),
    '4.3': ('Incomplete records', 'The preparation of financial statements'),
    '4.4': ('Accounting ratios', 'The preparation of financial statements'),
    '4.5': ('Manufacturing accounts', 'The preparation of financial statements'),
    '5.3': ('Irrecoverable debts', 'Accounting for end of period adjustments'),
    '5.4': ('Other receivables and payables', 'Accounting for end of period adjustments'),
}

# Each pattern adds weight to a chapter when it appears in the question text.
LEXICON: dict[str, list[str]] = {
    '1.1': [r'public sector', r'private sector', r'stakeholder', r'sole trader\b(?! ?\'?s? (?:income|statement))',
            r'characteristics? of (?:a )?(?:sole trader|partnership)', r'unlimited liability'],
    '1.2': [r'\bprudence\b', r'\bconsistency\b', r'accruals concept', r'\bmateriality\b',
            r'money measurement', r'business entity', r'accounting concepts?'],
    '1.3': [r'\bsoftware\b', r'spreadsheet', r'data loss', r'\bpassword', r'back-?up', r'firewall',
            r'\bhardware\b', r'\bvirus', r'technology', r'computeri[sz]ed'],
    '1.4': [r'\bethic', r'\bintegrity\b', r'\bobjectivity\b', r'professional competence', r'due care',
            r'professional behaviour', r'public interest'],
    '2.1': [r'\binvoice', r'credit note', r'purchase order', r'statement of account', r'remittance advice',
            r'petty cash voucher', r'cash receipt', r'trade discount', r'business documents?'],
    '2.2': [r'day ?book', r'returns (?:day )?book', r'cash book', r'petty cash book', r'\bthe journal\b',
            r'\bimprest\b', r'books? of (?:original|prime) entry', r'cash discount'],
    '2.3': [r'\bledger\b', r'double[- ]entry', r'balance c/d', r'balance b/d', r'drawings account',
            r'nominal ledger', r'receivables ledger', r'payables ledger'],
    '2.4': [r'capital expenditure', r'revenue expenditure', r'capital income', r'revenue income'],
    '2.5': [r'depreciation', r'reducing balance', r'straight[- ]line', r'\bdisposal\b', r'carrying (?:amount|value)',
            r'net book value', r'non-current asset'],
    '3.1': [r'trial balance'],
    '3.2': [r'control account', r'receivables control', r'payables control', r'sales ledger control',
            r'purchases ledger control', r'\bcontra\b'],
    '3.3': [r'suspense', r'correction of errors?', r'error of (?:commission|omission|principle|original entry)',
            r'complete reversal', r'compensating error', r'correct(?:ing)? (?:the )?errors?'],
    '3.4': [r'bank reconciliation', r'bank statement', r'unpresented', r'uncredited|lodgements? not',
            r'dishonoured', r'standing order', r'direct debit', r'bank charges'],
    '4.1': [r'income statement', r'statement of financial position', r'gross profit\b(?! (?:percentage|margin))',
            r'profit for the year\b(?! as a percentage)', r'cost of sales'],
    '4.2': [r'appropriation', r'\bpartners?\'? ?(?:current|capital) accounts?', r'interest on (?:capital|drawings)',
            r'partners?\'? salar', r'partnership act', r'profit[- ]sharing ratio', r'limited liability partnership',
            r'\bLLP\b'],
    '4.3': [r'incomplete records', r'opening (?:capital|equity)', r'closing (?:capital|equity)',
            r'statement of affairs', r'\bmark-?up\b', r'\bmargin\b'],
    '4.4': [r'\bratio', r'return on capital employed', r'\bROCE\b', r'acid test', r'liquid (?:\(acid test\) )?ratio',
            r'current (?:\(working capital\) )?ratio', r'gross profit (?:percentage|margin)', r'profitability',
            r'liquidity'],
    '4.5': [r'manufactur', r'prime cost', r'work[- ]in[- ]progress', r'raw materials', r'factory overheads?',
            r'production cost', r'direct labour'],
    '5.3': [r'irrecoverable', r'bad debts?', r'provision for (?:doubtful|irrecoverable)'],
    '5.4': [r'\baccrued\b', r'\bprepaid\b', r'other receivables', r'other payables', r'\baccruals?\b(?! concept)',
            r'prepayments?'],
}
_COMPILED = {code: [re.compile(p, re.I) for p in pats] for code, pats in LEXICON.items()}


def propose(text: str, paper: str) -> list[tuple[str, int]]:
    """Return (code, hits) ranked best first. `paper` is '1' or '2'."""
    scores = {code: sum(len(rx.findall(text)) for rx in rxs) for code, rxs in _COMPILED.items()}
    if paper == '2':
        # Paper 2 is built on Topics 4-5. "Partnership" there means the accounts,
        # and statements are the subject, not a type of organisation.
        scores['4.2'] += scores.pop('1.1')
    return sorted(((c, n) for c, n in scores.items() if n), key=lambda x: -x[1])


def difficulty(marks: int) -> str:
    """4AC1 has three question sizes: 1-mark MCQ, 5-mark short answer, 15/25-mark
    structured questions. The bands follow those sizes."""
    if marks <= 2:
        return 'easy'
    return 'medium' if marks <= 8 else 'hard'
