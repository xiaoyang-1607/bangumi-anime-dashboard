from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from main import build_parser, run


class PipelineCliTests(unittest.TestCase):
    def test_publish_is_opt_in(self):
        args = build_parser().parse_args([])
        self.assertFalse(args.publish)

    def test_missing_archive_returns_failure(self):
        with TemporaryDirectory() as directory:
            result = run(["--dump-dir", str(Path(directory))])
        self.assertEqual(result, 1)


if __name__ == "__main__":
    unittest.main()
