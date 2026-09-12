import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pandas as pd

from get_source import (
    TYPE_ANIME,
    _add_derived_scores,
    apply_excel_date_format,
    export_to_excel,
    export_to_parquet,
    process_subject_data,
)


class ArchiveProcessingTests(unittest.TestCase):
    def test_empirical_bayes_strength_is_estimated_from_data(self):
        base = [
            {"score": 6.0, "score_total": 10, "_rating_variance": 4.0},
            {"score": 9.0, "score_total": 1000, "_rating_variance": 4.0},
            {"score": 8.0, "score_total": 100, "_rating_variance": 4.0},
        ]
        records = [item.copy() for item in base]
        model = _add_derived_scores(records)
        self.assertGreater(model["between_variance"], 0)
        self.assertNotEqual(model["equivalent_prior_votes"], 250)
        self.assertGreater(records[0]["bayesian_score"], records[0]["score"])
        self.assertLess(records[1]["bayesian_score"], records[1]["score"])

        more_diverse = [
            {**item, "score": score}
            for item, score in zip(base, (3.0, 9.0, 8.0))
        ]
        other_model = _add_derived_scores(more_diverse)
        self.assertNotEqual(model["equivalent_prior_votes"], other_model["equivalent_prior_votes"])

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
                "score_details": {"8": 2, "9": "3"},
                "meta_tags": ["原创", {"name": "科幻"}],
                "tags": [
                    {"name": "经典", "count": 8},
                    {"name": "个人标签", "count": 1},
                ],
                "favorite": {
                    "wish": 2, "done": 10, "doing": 3, "on_hold": 1, "dropped": 4,
                },
            },
            {
                "id": 2,
                "type": 4,
                "rank": 20,
                "name": "No date",
                "score": 7.0,
                "score_details": {"7": 10},
            },
            {
                "id": 3,
                "type": 2,
                "rank": 0,
                "name": "Unranked",
                "date": "2020-01-01",
                "score": 7.0,
                "score_details": {"7": 10},
            },
            {
                "id": 4,
                "type": 2,
                "rank": 5,
                "name": "Broken ratings",
                "date": "2020-01-01",
                "score": 8.0,
                "score_details": {"bad": 2},
            },
            {
                "id": 5,
                "type": 2,
                "rank": 6,
                "name": "Invalid classification",
                "date": "2020-01-01",
                "score": 8.0,
                "score_details": {"8": 2},
                "nsfw": "not-a-boolean",
            },
        ]
        with TemporaryDirectory() as directory:
            path = Path(directory) / "subject.jsonlines"
            content = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows)
            path.write_text(content + "\n{invalid", encoding="utf-8")
            anime, games = process_subject_data(path)

        self.assertEqual(len(anime), 1)
        self.assertEqual(len(games), 1)
        self.assertEqual(anime[0]["name_cn"], "Anime")
        self.assertEqual(anime[0]["score_total"], 5)
        self.assertEqual(anime[0]["meta_tags"], "原创, 科幻")
        self.assertEqual(anime[0]["user_tags"], "经典")
        self.assertEqual(anime[0]["favorite"], 20)
        self.assertEqual(anime[0]["favorite_done"], 10)
        self.assertEqual(games[0]["release_status"], "unknown_date")
        self.assertIsNone(games[0]["date"])
        self.assertIn("bayesian_score", anime[0])

    def test_quality_report_distinguishes_cleaning_from_ranking_rules(self):
        rows = [
            {
                "id": 1, "type": 2, "rank": 0, "name": "Valid unranked",
                "date": "2024-01-01", "score": 7, "score_details": {"7": 3},
            },
            {
                "id": 2, "type": 2, "rank": 1, "name": "Invalid date",
                "date": "2024-99-01", "score": 8, "score_details": {"8": 3},
            },
        ]
        with TemporaryDirectory() as directory:
            path = Path(directory) / "subject.jsonlines"
            path.write_text(
                "\n".join(json.dumps(row, ensure_ascii=False) for row in rows),
                encoding="utf-8",
            )
            anime, games, report = process_subject_data(path, return_report=True)

        self.assertEqual(anime, [])
        self.assertEqual(games, [])
        self.assertEqual(report["counts"]["unranked"], 1)
        self.assertEqual(report["counts"]["invalid_date"], 1)
        self.assertEqual(report["counts"]["invalid_json"], 0)

    def test_rank_change_uses_previous_source_rank(self):
        rows = [
            {"id": subject_id, "type": 2, "rank": rank, "name": str(subject_id),
             "score": score, "score_details": {"8": 5}, "date": "2024-01-01"}
            for subject_id, rank, score in ((1, 10, 8), (2, 20, 8), (3, 30, 8))
        ]
        with TemporaryDirectory() as directory:
            path = Path(directory) / "subject.jsonlines"
            path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
            anime, _, report = process_subject_data(
                path, return_report=True,
                previous_rankings={TYPE_ANIME: {1: 18, 2: 15}},
                comparison_archive="previous.zip",
            )
        by_id = {record["id"]: record for record in anime}
        self.assertEqual((by_id[1]["rank_change"], by_id[1]["rank_change_status"]), (8, "up"))
        self.assertEqual((by_id[2]["rank_change"], by_id[2]["rank_change_status"]), (-5, "down"))
        self.assertEqual(by_id[3]["rank_change_status"], "new")
        self.assertEqual(report["rank_movement"]["new"], 1)

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
            loaded = pd.read_excel(output, engine="openpyxl")
        self.assertEqual(loaded.loc[0, "date"].strftime("%Y-%m-%d"), "2024-02-03")

    def test_legacy_date_formatter_remains_compatible(self):
        records = [{"id": 1, "date": "2024-02-03"}]
        with TemporaryDirectory() as directory:
            output = Path(directory) / "legacy.xlsx"
            self.assertTrue(export_to_excel(records, output, "Subjects"))
            self.assertTrue(apply_excel_date_format(output, "date", "yyyy-mm-dd"))

    def test_parquet_export_preserves_types_and_missing_dates(self):
        records = [
            {"id": 1, "date": "2024-02-03", "nsfw": False},
            {"id": 2, "date": None, "nsfw": True},
        ]
        with TemporaryDirectory() as directory:
            output = Path(directory) / "data.parquet"
            self.assertTrue(export_to_parquet(records, output))
            loaded = pd.read_parquet(output, engine="pyarrow")

        self.assertTrue(pd.api.types.is_datetime64_any_dtype(loaded["date"]))
        self.assertTrue(pd.api.types.is_bool_dtype(loaded["nsfw"]))
        self.assertTrue(pd.isna(loaded.loc[1, "date"]))


if __name__ == "__main__":
    unittest.main()
