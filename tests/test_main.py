from datetime import date
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pandas as pd

from main import build_parser, generate_files, run


class PipelineCliTests(unittest.TestCase):
    def test_publish_is_opt_in(self):
        args = build_parser().parse_args([])
        self.assertFalse(args.publish)

    def test_missing_archive_returns_failure(self):
        with TemporaryDirectory() as directory:
            result = run(["--dump-dir", str(Path(directory))])
        self.assertEqual(result, 1)

    def test_generate_files_writes_valid_workbooks_and_quality_report(self):
        rows = [
            {
                "id": 1, "type": 2, "rank": 1, "name": "Anime",
                "date": "2024-01-01", "score": 8, "score_details": {"8": 3},
                "favorite": {
                    "wish": 1, "done": 3, "doing": 0, "on_hold": 0, "dropped": 0,
                },
                "nsfw": False,
            },
            {
                "id": 2, "type": 4, "rank": 1, "name": "Game",
                "date": None, "score": 7, "score_details": {"7": 3},
                "favorite": {
                    "wish": 2, "done": 3, "doing": 0, "on_hold": 0, "dropped": 0,
                },
                "nsfw": False,
            },
        ]
        with TemporaryDirectory() as directory:
            root = Path(directory)
            dump_dir = root / "dump"
            output_dir = root / "output"
            dump_dir.mkdir()
            (dump_dir / "subject.jsonlines").write_text(
                "\n".join(json.dumps(row) for row in rows), encoding="utf-8"
            )
            generated = generate_files(
                dump_dir, output_dir, as_of_date=date(2024, 6, 1)
            )
            names = {path.name for path in generated}
            report = json.loads(
                (output_dir / "data_quality_report.json").read_text(encoding="utf-8")
            )
            game = pd.read_parquet(output_dir / "game_cleaned.parquet", engine="pyarrow")

        self.assertEqual(
            names,
            {
                "anime_cleaned.parquet", "game_cleaned.parquet",
                "anime_cleaned.xlsx", "game_cleaned.xlsx",
                "data_quality_report.json",
            },
        )
        self.assertEqual(report["output"]["total_records"], 2)
        self.assertEqual(game.loc[0, "release_status"], "unknown_date")


if __name__ == "__main__":
    unittest.main()
