import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pandas as pd

from get_source import (
    apply_excel_date_format,
    export_to_excel,
    process_subject_data,
)


class ArchiveProcessingTests(unittest.TestCase):
    def test_processes_supported_types_and_skips_bad_rows(self):
        rows = [
            {
                "id": 1,
                "type": 2,
                "rank": 10,
                "name": "Anime",
                "name_cn": "",
                "date": "2024-01-01",
                "score": 8.1,
                "score_details": {"8": 2, "9": "3", "bad": None},
                "meta_tags": ["原创", {"name": "科幻"}],
            },
            {"id": 2, "type": 4, "rank": 20, "name": "No date"},
            {"id": 3, "type": 2, "rank": 0, "name": "Unranked", "date": "2020-01-01"},
        ]
        with TemporaryDirectory() as directory:
            path = Path(directory) / "subject.jsonlines"
            content = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows)
            path.write_text(content + "\n{invalid", encoding="utf-8")
            anime, games = process_subject_data(path)

        self.assertEqual(len(anime), 1)
        self.assertEqual(games, [])
        self.assertEqual(anime[0]["name_cn"], "Anime")
        self.assertEqual(anime[0]["score_total"], 5)
        self.assertEqual(anime[0]["meta_tags"], "原创, 科幻")

    def test_excel_export_and_date_format_round_trip(self):
        records = [
            {
                "id": 1,
                "name": "A",
                "name_cn": "A",
                "date": "2024-02-03",
                "meta_tags": "原创",
                "score": 8.0,
                "score_total": 10,
                "rank": 1,
            }
        ]
        with TemporaryDirectory() as directory:
            output = Path(directory) / "data.xlsx"
            self.assertTrue(export_to_excel(records, output, "Subjects"))
            self.assertTrue(apply_excel_date_format(output, "date", "yyyy-mm-dd"))
            loaded = pd.read_excel(output, engine="openpyxl")
        self.assertEqual(loaded.loc[0, "date"].strftime("%Y-%m-%d"), "2024-02-03")


if __name__ == "__main__":
    unittest.main()
