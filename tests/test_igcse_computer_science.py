"""Guard publication against stale reviews and unusable practical tasks."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from onboard_igcse_computer_science import DEPENDENCIES, fingerprint, validate_read


class ComputerScienceTests(unittest.TestCase):
    def test_practical_dependencies_without_file_extensions_are_detected(self):
        for prompt in ('Open Q01b in the code editor.', 'Open the file Q06 in the code editor.',
                       'Amend the program files provided.', 'Open answers.csv'):
            self.assertIsNotNone(DEPENDENCIES.search(prompt), prompt)
        self.assertIsNone(DEPENDENCIES.search('Explain why a computer uses binary.'))

    def test_chapter_read_is_bound_to_both_pdfs(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = [Path(folder) / f'{kind}.pdf' for kind in ('qp', 'ms')]
            for path in paths:
                with fitz.open() as doc:
                    doc.new_page().insert_text((40, 80), 'Reviewed question')
                    doc.save(path)
            row = dict(zip(('qp', 'ms'), map(str, paths)))
            read = {'topics': ['1', '2'], 'difficulty': 'hard', 'reason': 'Trace and correct an array algorithm.',
                    'qp_sha256': fingerprint(paths[0]), 'ms_sha256': fingerprint(paths[1])}
            self.assertEqual(validate_read(row, read), ['1', '2'])
            for field, value in [('topics', ['7']), ('topics', ['1', '1']), ('topics', []),
                                 ('reason', ''), ('difficulty', 'invented'), ('ms_sha256', 'stale')]:
                invalid = copy.deepcopy(read)
                invalid[field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    validate_read(row, invalid)
            paths[0].write_bytes(b'changed source')
            with self.assertRaisesRegex(ValueError, 'Stale qp'):
                validate_read(row, read)


if __name__ == '__main__':
    unittest.main()
