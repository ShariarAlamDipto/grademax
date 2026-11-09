"""IGCSE Economics (4EC1) chapter taxonomy for the test builder and worksheet generator.

Codes are the 18 subsections of the 4EC1 specification (Issue 3): Paper 1
covers 1.1-1.2 (microeconomics and business economics), Paper 2 covers
2.1-2.2 (macroeconomics and the global economy). The 2011-2017 papers (4EC0)
are tagged against the same subsections.
"""
from __future__ import annotations

from lib.commerce_chapters import Subject

T11 = 'The market system'
T12 = 'Business economics'
T21 = 'Government and the economy'
T22 = 'The global economy'

CHAPTERS: dict[str, tuple[str, str]] = {
    '1.1.1': ('The economic problem', T11),
    '1.1.2': ('Economic assumptions', T11),
    '1.1.3': ('Demand, supply and market equilibrium', T11),
    '1.1.4': ('Elasticity', T11),
    '1.1.5': ('The mixed economy', T11),
    '1.1.6': ('Externalities', T11),
    '1.2.1': ('Production', T12),
    '1.2.2': ('Productivity and division of labour', T12),
    '1.2.3': ('Business costs, revenues and profit', T12),
    '1.2.4': ('Business competition', T12),
    '1.2.5': ('The labour market', T12),
    '1.2.6': ('Government intervention', T12),
    '2.1.1': ('Macroeconomic objectives', T21),
    '2.1.2': ('Government policies', T21),
    '2.1.3': ('Relationships between objectives', T21),
    '2.2.1': ('Globalisation', T22),
    '2.2.2': ('International trade', T22),
    '2.2.3': ('Exchange rates', T22),
}

SUBJECT = Subject(code='4EC1', subject_id='c45382db-b0ac-4ec6-b893-26c07c1bd5d0',
                  chapters=CHAPTERS, spec_label='4EC1 specification')
