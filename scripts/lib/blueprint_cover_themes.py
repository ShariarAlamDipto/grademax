"""Colour system and copy for the blueprint yearwise covers.

Two families share one layout. ACID covers are bright and print dark ink; JEWEL
covers are deep and print white. M1 acid yellow, S1 lime, P4 wine and Physics
ember are the user-approved originals and are kept exactly; the other nine are
picked so no two books in the same shelf row share a hue.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    name: str
    bg: tuple[str, str, str]      # radial gradient: centre, 60%, edge
    ink: str                      # title and main plate line
    muted: str                    # thin title line, kicker, soft plate line
    accent: str                   # rule, numbers, plate highlights
    glow: str                     # plate glow
    back_ink: str
    back_mid: str                 # eyebrow, list numbers, instructor band
    back_line: str                # hairlines and dotted rules
    back_grid: str
    back_plate: str               # faded corner drawing
    dark: bool


THEMES: dict[str, Theme] = {
    # acid family
    'WME01': Theme('Acid yellow', ('#F3F98A', '#E8F329', '#D7E21A'), '#46490C', '#6B7013', '#C47A0E',
                   '#FFFFFF', '#3A3D0A', '#4F530E', '#CBD08A', '#EEF0D8', '#99A11B', False),
    'WST01': Theme('Lime', ('#CDEB80', '#A3D428', '#90C01C'), '#31400C', '#4A6112', '#B4620E',
                   '#FFFFFF', '#2A370A', '#38480D', '#BFD08F', '#E9F0D6', '#6C8D1B', False),
    'WMA11': Theme('Electric aqua', ('#B4F6F8', '#45D4E4', '#1CB4CC'), '#05323B', '#0E6573', '#D9402A',
                   '#FFFFFF', '#05323B', '#0A5A66', '#A9D9DF', '#E2F3F5', '#1B8A99', False),
    '4MB1': Theme('Tangerine', ('#FFD99A', '#FF9C33', '#F37812'), '#3F1C04', '#87410E', '#1C4C9C',
                  '#FFFFFF', '#3F1C04', '#A04A0A', '#F0C79E', '#FCEEDF', '#B3560F', False),
    '4HB1': Theme('Flamingo', ('#FFCBD8', '#FF86A8', '#F2608C'), '#4A0A22', '#8E1F47', '#0B6E6A',
                  '#FFFFFF', '#4A0A22', '#B0285A', '#F2B9CA', '#FCE9EF', '#C0396A', False),
    '4EB1': Theme('Parchment', ('#FFF7E2', '#F4D697', '#E6BA66'), '#2A1A0A', '#7A5526', '#C4311E',
                  '#FFFFFF', '#2A1A0A', '#8A5A20', '#E2CFA8', '#F7F0E1', '#9A6A2C', False),
    # jewel family
    'WMA14': Theme('Wine', ('#7C3847', '#2E0E15', '#18070B'), '#FFFFFF', '#9F6D78', '#F0B24A',
                   '#8E5360', '#2E0E15', '#551A27', '#C8ABB1', '#EBE0E2', '#481621', True),
    '4PH1': Theme('Ember', ('#E3533F', '#9A2414', '#5B150C'), '#FFFFFF', '#F2A399', '#F6C560',
                  '#FF8A70', '#5D160D', '#AD2918', '#EBB8B1', '#F8E4E1', '#932215', True),
    '4CH1': Theme('Ultraviolet', ('#7552EA', '#2D1A7A', '#12073A'), '#FFFFFF', '#AD9DF0', '#B9F25C',
                  '#8E73F5', '#1E0F52', '#4B2EB5', '#C9BFEF', '#EEEAFB', '#3A2399', True),
    '4BI1': Theme('Emerald', ('#2EAE6B', '#0C5A38', '#03271A'), '#FFFFFF', '#8FD3AE', '#F3E35B',
                  '#4CC88A', '#0A3A25', '#13804D', '#B3D8C3', '#E4F2EA', '#0F6A40', True),
    '4PM1': Theme('Obsidian gold', ('#434B5B', '#191C24', '#08090C'), '#FFFFFF', '#9AA1B0', '#E9B949',
                  '#6B7385', '#15181F', '#8A6A1E', '#CFC6B0', '#F1EDE3', '#2B2F38', True),
    'WMA12': Theme('Petrol', ('#1696A8', '#08505E', '#032530'), '#FFFFFF', '#7FC8D2', '#FF9E6B',
                   '#2BB3C4', '#04303A', '#0B6475', '#A9CDD4', '#E1EFF1', '#0B5A69', True),
    'WMA13': Theme('Ultramarine', ('#4A63EA', '#1C2A93', '#0B1042'), '#FFFFFF', '#9EA9F5', '#FFD24A',
                   '#6F84F2', '#10175A', '#2A3BB8', '#BCC3EE', '#E7EAFA', '#22308F', True),
}


@dataclass(frozen=True)
class Copy:
    title: str          # first line of the cover title
    thin: str           # second, light line ('' for one-line titles)
    subject: str        # how the blurb names the subject
    topics: str         # 'From ... to ...' clause of the second blurb
    inline: bool = False  # thin part on the same line as the title


COPY: dict[str, Copy] = {
    '4BI1': Copy('Biology', '', 'IGCSE Biology',
                 'From cells, enzymes and nutrition to transport, genetics, ecosystems and the use of '
                 'biological resources'),
    '4CH1': Copy('Chemistry', '', 'IGCSE Chemistry',
                 'From atomic structure and bonding to quantitative chemistry, energetics, rates, '
                 'equilibria and organic chemistry'),
    '4EB1': Copy('English', 'Language B', 'IGCSE English Language B',
                 'From reading comprehension and summary to directed writing and extended writing'),
    '4HB1': Copy('Human', 'Biology', 'IGCSE Human Biology',
                 'From cells and enzymes to breathing, circulation, the blood, coordination, '
                 'reproduction and disease'),
    '4MB1': Copy('Mathematics', 'B', 'IGCSE Mathematics B',
                 'From number, sets and algebra to functions, matrices, geometry, vectors, '
                 'transformations and statistics', inline=True),
    '4PH1': Copy('Physics', '', 'IGCSE Physics',
                 'From forces and motion to electricity, waves, energy, magnetism, radioactivity and '
                 'astrophysics'),
    '4PM1': Copy('Further Pure', 'Mathematics', 'IGCSE Further Pure Mathematics',
                 'From logarithms, quadratics and series to the binomial expansion, vectors, calculus '
                 'and trigonometry'),
    'WMA11': Copy('Pure', 'Maths P1', 'Pure Mathematics P1',
                  'From quadratics and curve sketching to straight lines, radians, trigonometry, '
                  'differentiation and integration'),
    'WMA12': Copy('Pure', 'Maths P2', 'Pure Mathematics P2',
                  'From algebraic division and the circle to logarithms, series, the binomial '
                  'expansion, trigonometric equations and the trapezium rule'),
    'WMA13': Copy('Pure', 'Maths P3', 'Pure Mathematics P3',
                  'From functions, modulus and exponentials to trigonometric identities, calculus '
                  'techniques and numerical methods'),
    'WMA14': Copy('Pure', 'Maths P4', 'Pure Mathematics P4',
                  'From partial fractions and the binomial series to parametric equations, '
                  'integration, differential equations and vectors'),
    'WME01': Copy('Mechanics', 'M1', 'Mechanics 1',
                  'From kinematics and vectors to Newton’s laws, connected particles, '
                  'friction, momentum and moments'),
    'WST01': Copy('Statistics', 'S1', 'Statistics 1',
                  'From measures of location and spread to probability, correlation and regression, '
                  'discrete random variables and the normal distribution'),
}

SEASON = {
    'IGCSE': {'jan': 'January', 'may-jun': 'June', 'oct-nov': 'November'},
    'IAL': {'jan': 'January', 'may-jun': 'June', 'oct-nov': 'October'},
}
SEASON_SHORT = {'January': 'JAN', 'June': 'JUN', 'October': 'OCT', 'November': 'NOV'}
