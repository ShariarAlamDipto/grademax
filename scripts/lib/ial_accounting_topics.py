"""IAL Accounting (WAC11 Unit 1, WAC12 Unit 2) chapters for the test builder and
worksheet generator.

Chapters are the sub-headings of the Pearson Edexcel IAL Accounting
specification (Issue 2, September 2018, pp. 12-21). Each chapter lists the
specification sections it covers. Codes are two-digit ("1.07") so the topic
list sorts in specification order; the plain section numbers would sort
"1.3.14" before "1.3.7".

ICT is one chapter for both units: Unit 1 assesses it as 1.1.7 (recording
transactions) and Unit 2 as 2.9 (costing and management information).
"""
from __future__ import annotations

from lib.commerce_chapters import Subject

U1 = 'Unit 1: The Accounting System and Costing'
U2 = 'Unit 2: Corporate and Management Accounting'

# code -> (name, "unit -- specification sections")
CHAPTERS: dict[str, tuple[str, str]] = {
    '1.01': ('Accounting principles, double entry and concepts', f'{U1} -- 1.1.1-1.1.6, 1.1.8-1.1.10'),
    '1.02': ('Capital and revenue expenditure', f'{U1} -- 1.1.11-1.1.12'),
    '1.03': ('Depreciation and disposal of non-current assets', f'{U1} -- 1.1.13-1.1.20'),
    '1.04': ('Trial balance', f'{U1} -- 1.2.1-1.2.2'),
    '1.05': ('Control accounts', f'{U1} -- 1.2.3-1.2.4'),
    '1.06': ('Correction of errors and suspense accounts', f'{U1} -- 1.2.5-1.2.9'),
    '1.07': ('Sole trader financial statements and year-end adjustments', f'{U1} -- 1.3.1-1.3.6'),
    '1.08': ('Departmental accounts', f'{U1} -- 1.3.7'),
    '1.09': ('Incomplete records', f'{U1} -- 1.3.8'),
    '1.10': ('Partnerships', f'{U1} -- 1.3.9-1.3.13'),
    '1.11': ('Clubs and non-profit-making organisations', f'{U1} -- 1.3.14-1.3.19'),
    '1.12': ('Manufacturing accounts', f'{U1} -- 1.3.20-1.3.22'),
    '1.13': ('Inventory valuation', f'{U1} -- 1.4.1-1.4.3'),
    '1.14': ('Labour costs and remuneration', f'{U1} -- 1.4.4-1.4.6'),
    '1.15': ('Overheads: allocation, apportionment and absorption', f'{U1} -- 1.4.7-1.4.11'),
    '1.16': ('Job and batch costing', f'{U1} -- 1.4.12-1.4.13'),
    '1.17': ('Ratio analysis', f'{U1} -- 1.5.1-1.5.3'),
    '1.18': ('Social and ethical accounting', f'{U1} -- 1.6.1-1.6.4'),
    '2.01': ('Limited company financial statements and reports', f'{U2} -- 2.1.1-2.1.3'),
    '2.02': ('Capital structure: reserves, shares and debentures', f'{U2} -- 2.1.4-2.1.11'),
    '2.03': ('Mergers and purchase of limited companies', f'{U2} -- 2.1.12-2.1.15'),
    '2.04': ('Investment ratios', f'{U2} -- 2.2.1'),
    '2.05': ('Statement of cash flows', f'{U2} -- 2.3.1-2.3.2'),
    '2.06': ('Budgeting', f'{U2} -- 2.4.1-2.4.5'),
    '2.07': ('Standard costing and variances', f'{U2} -- 2.5.1-2.5.6'),
    '2.08': ('Project appraisal', f'{U2} -- 2.6.1-2.6.2'),
    '2.09': ('Break-even analysis', f'{U2} -- 2.7.1-2.7.3'),
    '2.10': ('Marginal and absorption costing', f'{U2} -- 2.8.1-2.8.6'),
    '2.11': ('ICT in accounting', 'Units 1 and 2 -- 1.1.7, 2.9.1-2.9.2'),
}

SUBJECT = Subject(code='WAC', subject_id='b79c64c0-1840-4755-9727-4158fd38d4ac',
                  chapters=CHAPTERS, spec_label='IAL Accounting specification')
