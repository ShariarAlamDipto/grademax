"""IGCSE Business (4BS1) chapter taxonomy for the test builder and worksheet generator.

Codes are the 24 sections of the 4BS1 specification (Issue 2, pp. 9-30),
grouped under its five topics. The 2011-2016 papers (4BS0) are tagged against
the same sections: every 4BS0 topic maps onto a 4BS1 section.
"""
from __future__ import annotations

from lib.commerce_chapters import Subject

T1 = 'Business activity and influences on business'
T2 = 'People in business'
T3 = 'Business finance'
T4 = 'Marketing'
T5 = 'Business operations'

CHAPTERS: dict[str, tuple[str, str]] = {
    '1.1': ('Business objectives', T1),
    '1.2': ('Types of organisations', T1),
    '1.3': ('Classification of businesses', T1),
    '1.4': ('Decisions on location', T1),
    '1.5': ('Business and the international economy', T1),
    '1.6': ('Government objectives and policies', T1),
    '1.7': ('External factors', T1),
    '1.8': ('What makes a business successful?', T1),
    '2.1': ('Internal and external communication', T2),
    '2.2': ('Recruitment and selection process', T2),
    '2.3': ('Training', T2),
    '2.4': ('Motivation and rewards', T2),
    '2.5': ('Organisation structure and employees', T2),
    '3.1': ('Business finance: sources', T3),
    '3.2': ('Cash-flow forecasting', T3),
    '3.3': ('Costs and break-even analysis', T3),
    '3.4': ('Financial documents', T3),
    '3.5': ('Accounts analysis', T3),
    '4.1': ('Market research', T4),
    '4.2': ('The market', T4),
    '4.3': ('The marketing mix', T4),
    '5.1': ('Economies and diseconomies of scale', T5),
    '5.2': ('Production', T5),
    '5.3': ('Factors of production', T5),
    '5.4': ('Quality', T5),
}

SUBJECT = Subject(code='4BS1', subject_id='7c04f33d-c76a-4e41-bd93-845008e301a6',
                  chapters=CHAPTERS, spec_label='4BS1 specification')
