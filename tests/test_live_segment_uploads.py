import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from lib import live_segments_publish as publisher


class UploadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.pdf = Path(self.temp.name) / "question.pdf"
        self.pdf.write_bytes(b"example PDF bytes")

    def test_duplicate_and_existing_objects_are_not_uploaded(self):
        put = Mock()
        with patch.object(publisher, "_put_with_retry", put), redirect_stdout(StringIO()):
            count = publisher.upload_objects(Mock(), "bucket", [
                (self.pdf, "q1"), (self.pdf, "q1"), (self.pdf, "q2")], {"q2": 17}, 2)
        self.assertEqual(count, 2)
        self.assertEqual(put.call_count, 1)
        self.assertEqual(put.call_args.args[2:], ("q1", b"example PDF bytes"))

    def test_failed_upload_does_not_report_completion(self):
        with patch.object(publisher, "_put_with_retry", side_effect=RuntimeError("upload failed")), \
                redirect_stdout(StringIO()):
            with self.assertRaisesRegex(RuntimeError, "upload failed"):
                publisher.upload_objects(Mock(), "bucket", [(self.pdf, "q1")], {}, 2)

    def test_invalid_worker_count_cannot_start_uploads(self):
        with patch.object(publisher, "_put_with_retry") as put:
            with self.assertRaises(ValueError):
                publisher.upload_objects(Mock(), "bucket", [(self.pdf, "q1")], {}, 0)
            put.assert_not_called()


if __name__ == "__main__":
    unittest.main()
