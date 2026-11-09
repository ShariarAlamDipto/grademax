"""IAL Business (WBS11-WBS14) chapters for the test builder and worksheet generator.

Chapters are the 20 topics of the Pearson Edexcel IAL Business specification
(Issue 1, September 2017): unit content sections 1.3.1-4.3.4, coded by unit and
topic ("1.4" = Unit 1, topic 4). Each question is a whole section of a paper
(its extracts and every part), so one question usually spans several topics.
"""
from __future__ import annotations

from lib.commerce_chapters import Subject

U1, U2 = 'Unit 1: Marketing and people', 'Unit 2: Managing business activities'
U3, U4 = 'Unit 3: Business decisions and strategy', 'Unit 4: Global business'

CHAPTERS: dict[str, tuple[str, str]] = {
    '1.1': ('Meeting customer needs', U1),
    '1.2': ('The market', U1),
    '1.3': ('Marketing mix and strategy', U1),
    '1.4': ('Managing people', U1),
    '1.5': ('Entrepreneurs and leaders', U1),
    '2.1': ('Planning a business and raising finance', U2),
    '2.2': ('Financial planning', U2),
    '2.3': ('Managing finance', U2),
    '2.4': ('Resource management', U2),
    '2.5': ('External influences', U2),
    '3.1': ('Business objectives and strategy', U3),
    '3.2': ('Business growth', U3),
    '3.3': ('Decision-making techniques', U3),
    '3.4': ('Influences on business decisions', U3),
    '3.5': ('Assessing competitiveness', U3),
    '3.6': ('Managing change', U3),
    '4.1': ('Globalisation', U4),
    '4.2': ('Global markets and business expansion', U4),
    '4.3': ('Global marketing', U4),
    '4.4': ('Global industries and companies (multinational corporations)', U4),
}

SUBJECT = Subject(code='WBS', subject_id='655d8d23-7f9c-4713-81fb-26c4dbca8143',
                  chapters=CHAPTERS, spec_label='IAL Business specification')
