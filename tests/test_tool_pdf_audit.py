"""Regression checks for the missing final assessment pages found in commerce."""
from pathlib import Path
import sys
import tempfile
import unittest

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from lib.tool_pdf_audit import scheme_tail


class SchemeTailTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    def paper(self, name, pages):
        target = self.base / name
        with fitz.open() as doc:
            for text in pages:
                doc.new_page().insert_text((45, 80), text)
            doc.save(target)
        return target

    def test_unlabelled_final_grid_is_content(self):
        answer = '4(c) Answer guidance explains market orientation and customer needs.'
        grid = 'Level 3 9-12 marks. Detailed application and evaluation with a supported judgement.'
        source = self.paper('source.pdf', [answer, grid])
        cut = self.paper('cut.pdf', [answer])
        result = scheme_tail(cut, source)
        self.assertEqual(result['lastSourcePageCovered'], 1)
        self.assertEqual([p['sourcePage'] for p in result['omitted']], [2])

    def test_answer_continuation_is_content(self):
        answer = '4(c) Answers discuss the advantages and disadvantages of this proposal.'
        continuation = 'However this business might instead adopt a different approach to its products.'
        source = self.paper('source.pdf', [answer, continuation])
        cut = self.paper('cut.pdf', [answer])
        self.assertEqual(len(scheme_tail(cut, source)['omitted']), 1)

    def test_complete_answer_excludes_publisher_address(self):
        answer = '4(c) Complete answer with the assessment grid and a supported judgement.'
        publisher = 'Pearson Education Limited. Registered company number 872828 with its registered office at 80 Strand London.'
        source = self.paper('source.pdf', [answer, publisher])
        cut = self.paper('cut.pdf', [answer])
        result = scheme_tail(cut, source)
        self.assertEqual(result['omitted'], [])
        self.assertEqual(result['publisherPagesExcluded'], [2])


if __name__ == '__main__':
    unittest.main()
