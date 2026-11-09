"""IGCSE ICT (4IT1) chapters for the test builder and worksheet generator.

Chapters are the sections of topics 1-5 of the Pearson Edexcel International GCSE
ICT specification (Issue 2, May 2018), which Paper 1 (written) assesses. Topic 6,
Software skills, is assessed only by Paper 2, an on-screen practical that needs
data files; it is not offered as PDF questions.
"""
from __future__ import annotations

from lib.commerce_chapters import Subject

T1, T2, T3 = 'Digital devices', 'Connectivity', 'Operating online'
T4, T5 = 'Online goods and services', 'Applying information and communication technology'

CHAPTERS: dict[str, tuple[str, str]] = {
    '1.1': ('Types of digital devices', T1),
    '1.2': ('Features of digital devices', T1),
    '1.3': ('Software', T1),
    '1.4': ('Peripheral devices: input and output', T1),
    '1.5': ('Peripheral devices: storage', T1),
    '1.6': ('Memory', T1),
    '1.7': ('Processors', T1),
    '1.8': ('ICT systems to meet specified needs', T1),
    '2.1': ('Types of digital communications', T2),
    '2.2': ('Choosing a digital communication method', T2),
    '2.3': ('Connecting to a network', T2),
    '2.4': ('Benefits of a LAN or home network', T2),
    '2.5': ('Securing data on a network', T2),
    '3.1': ('Risks to data and personal information', T3),
    '3.2': ('Impact of the internet on individuals', T3),
    '3.3': ('Online working from home', T3),
    '3.4': ('Impact of the internet on organisations', T3),
    '3.5': ('Impact of the internet on society', T3),
    '3.6': ('Types of online communities', T3),
    '3.7': ('Use of online communities', T3),
    '3.8': ('Implications of digital technologies', T3),
    '3.9': ('Availability of information online', T3),
    '4.1': ('Types of online services', T4),
    '4.2': ('Impact of online services', T4),
    '4.3': ('Online software and cloud computing', T4),
    '5.1': ('Software applications', T5),
    '5.2': ('Data and information', T5),
    '5.3': ('Using software applications', T5),
    '5.4': ('Reviewing outcomes', T5),
}

SUBJECT = Subject(code='4IT1', subject_id='2536143d-e5da-4d29-970a-85e5a9d57b76',
                  chapters=CHAPTERS, spec_label='4IT1 specification')
