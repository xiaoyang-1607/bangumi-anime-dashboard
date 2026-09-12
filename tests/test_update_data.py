import json
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from update_data import (
    ArchiveAsset,
    add_rank_comparison_columns,
    backfill_rank_changes_from_git,
    extract_subject_jsonl,
    fetch_latest_asset,
    load_rank_comparison,
    select_latest_asset,
    update_latest_data,
    validate_record_count_change,
)
from get_source import PIPELINE_VERSION
from main import generate_files


class DataUpdaterTests(unittest.TestCase):
    def test_rank_columns_mark_up_down_same_and_new(self):
        import pandas as pd
        current = pd.DataFrame({"id": [1, 2, 3, 4], "rank": [10, 20, 30, 40]})
        result = add_rank_comparison_columns(current, {1: 15, 2: 12, 3: 30})
        self.assertEqual(result["rank_change_status"].tolist(), ["up", "down", "same", "new"])
        self.assertEqual(result["rank_change"].tolist()[:3], [5, -8, 0])
        self.assertTrue(pd.isna(result.loc[3, "rank_change"]))

    @patch("update_data.fetch_latest_asset")
    @patch("update_data.download_asset")
    @patch("update_data.extract_subject_jsonl")
    def test_new_archive_uses_existing_rank_as_baseline(
        self, extract_subject_jsonl, download_asset, fetch_latest_asset
    ):
        import pandas as pd
        fetch_latest_asset.return_value = ArchiveAsset(
            asset_id=101,
            name="dump-2026-09-08.210336Z.zip",
            url="https://example.test/archive.zip",
            size=100,
        )
        rows = [
            {"id": 1, "type": 2, "rank": 10, "name": "A", "date": "2024-01-01",
             "score": 8, "score_details": {"8": 3}},
            {"id": 2, "type": 4, "rank": 10, "name": "B", "date": "2024-01-01",
             "score": 7, "score_details": {"7": 3}},
        ]

        def write_fake_archive(_archive_path, output_path):
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                "\n".join(json.dumps(row) for row in rows), encoding="utf-8"
            )

        extract_subject_jsonl.side_effect = write_fake_archive
        with TemporaryDirectory() as directory:
            root = Path(directory)
            pd.DataFrame({"id": [1], "rank": [20]}).to_parquet(root / "anime_cleaned.parquet")
            pd.DataFrame({"id": [2], "rank": [5]}).to_parquet(root / "game_cleaned.parquet")
            (root / "data_metadata.json").write_text(
                json.dumps({
                    "archive_name": "dump-2026-09-01.210329Z.zip",
                    "anime_records": 1, "game_records": 1,
                }),
                encoding="utf-8",
            )
            self.assertTrue(update_latest_data(root))
            anime = pd.read_parquet(root / "anime_cleaned.parquet")
            game = pd.read_parquet(root / "game_cleaned.parquet")
            metadata = json.loads((root / "data_metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(anime.loc[0, "rank_change"], 10)
        self.assertEqual(game.loc[0, "rank_change"], -5)
        self.assertEqual(metadata["comparison_archive"], "dump-2026-09-01.210329Z.zip")

    def test_rank_comparison_distinguishes_new_archive_and_same_archive(self):
        import pandas as pd
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("anime_cleaned.parquet", "game_cleaned.parquet"):
                pd.DataFrame({
                    "id": [1], "rank": [10], "previous_rank": [12],
                    "rank_change": [2], "rank_change_status": ["up"],
                }).to_parquet(root / name, index=False)
            rankings, movements, comparison = load_rank_comparison(root, "old.zip", "new.zip")
            self.assertEqual(rankings[2][1], 10)
            self.assertIsNone(movements)
            self.assertEqual(comparison, "old.zip")
            rankings, movements, comparison = load_rank_comparison(
                root, "old.zip", "old.zip", "older.zip"
            )
            self.assertIsNone(rankings)
            self.assertEqual(movements[2][1]["rank_change"], 2)
            self.assertEqual(comparison, "older.zip")

    @patch("update_data.load_git_rankings")
    def test_backfill_updates_both_formats_and_report(self, load_git_rankings):
        import pandas as pd
        load_git_rankings.return_value = ({2: {1: 20}, 4: {2: 5}}, "old.zip")
        rows = [
            {"id": 1, "type": 2, "rank": 10, "name": "A", "date": "2024-01-01",
             "score": 8, "score_details": {"8": 3}},
            {"id": 2, "type": 4, "rank": 10, "name": "B", "date": "2024-01-01",
             "score": 7, "score_details": {"7": 3}},
        ]
        with TemporaryDirectory() as directory:
            root = Path(directory)
            dump = root / "dump"
            output = root / "output"
            dump.mkdir()
            (dump / "subject.jsonlines").write_text(
                "\n".join(json.dumps(row) for row in rows), encoding="utf-8"
            )
            generate_files(dump, output, as_of_date=date(2024, 1, 2))
            (output / "data_metadata.json").write_text(
                json.dumps({"pipeline_version": PIPELINE_VERSION, "archive_name": "new.zip"}),
                encoding="utf-8",
            )
            backfill_rank_changes_from_git(output, "abc1234")
            anime_parquet = pd.read_parquet(output / "anime_cleaned.parquet")
            game_excel = pd.read_excel(output / "game_cleaned.xlsx")
            report = json.loads((output / "data_quality_report.json").read_text(encoding="utf-8"))
        self.assertEqual(anime_parquet.loc[0, "rank_change"], 10)
        self.assertEqual(game_excel.loc[0, "rank_change"], -5)
        self.assertEqual(report["comparison_archive"], "old.zip")
        self.assertEqual(report["rank_movement"]["up"], 1)

    def test_selects_latest_timestamped_zip(self):
        assets = [
            {
                "id": 1,
                "name": "dump-2026-07-28.210449Z.zip",
                "browser_download_url": "https://example.test/latest.zip",
                "size": 200,
            },
            {
                "id": 2,
                "name": "dump-2026-08-01.000000Z.7z",
                "browser_download_url": "https://example.test/ignored.7z",
                "size": 100,
            },
            {
                "id": 3,
                "name": "dump-2026-07-21.210441Z.zip",
                "browser_download_url": "https://example.test/older.zip",
                "size": 100,
            },
        ]
        selected = select_latest_asset(assets)
        self.assertEqual(selected.asset_id, 1)

    @patch("update_data.request_json")
    def test_fetches_paginated_release_assets(self, request_json):
        request_json.side_effect = [
            {"assets_url": "https://api.example.test/assets"},
            [
                {
                    "id": 9,
                    "name": "dump-2026-07-28.210449Z.zip",
                    "browser_download_url": "https://example.test/archive.zip",
                    "size": 123,
                }
            ],
        ]
        selected = fetch_latest_asset("https://api.example.test/latest")
        self.assertEqual(selected.asset_id, 9)
        self.assertEqual(request_json.call_count, 2)

    def test_extracts_nested_subject_file_only(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "archive.zip"
            output = root / "dump" / "subject.jsonlines"
            with ZipFile(archive, "w") as target:
                target.writestr("dump/subject.jsonlines", '{"id": 1}\n')
                target.writestr("dump/large-unused.txt", "ignored")
            extract_subject_jsonl(archive, output)
            self.assertEqual(output.read_text(encoding="utf-8"), '{"id": 1}\n')

    @patch("update_data.fetch_latest_asset")
    def test_skips_already_processed_asset(self, fetch_latest_asset):
        asset = ArchiveAsset(
            asset_id=99,
            name="dump-2026-07-28.210449Z.zip",
            url="https://example.test/archive.zip",
            size=123,
        )
        fetch_latest_asset.return_value = asset
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "anime_cleaned.parquet").touch()
            (root / "game_cleaned.parquet").touch()
            (root / "anime_cleaned.xlsx").touch()
            (root / "game_cleaned.xlsx").touch()
            (root / "data_quality_report.json").touch()
            (root / "data_metadata.json").write_text(
                json.dumps(
                    {
                        "archive_asset_id": asset.asset_id,
                        "archive_name": asset.name,
                        "pipeline_version": PIPELINE_VERSION,
                    }
                ),
                encoding="utf-8",
            )
            changed = update_latest_data(root)
        self.assertFalse(changed)

    def test_rejects_anomalous_record_count_drop(self):
        with self.assertRaisesRegex(RuntimeError, "超过允许"):
            validate_record_count_change(
                {"anime_records": 10_000}, {"anime_records": 8_000}
            )


if __name__ == "__main__":
    unittest.main()
