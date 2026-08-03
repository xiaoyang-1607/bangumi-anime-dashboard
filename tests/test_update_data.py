import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from update_data import (
    ArchiveAsset,
    extract_subject_jsonl,
    fetch_latest_asset,
    select_latest_asset,
    update_latest_data,
)


class DataUpdaterTests(unittest.TestCase):
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
            (root / "anime_cleaned.xlsx").touch()
            (root / "game_cleaned.xlsx").touch()
            (root / "data_metadata.json").write_text(
                json.dumps(
                    {"archive_asset_id": asset.asset_id, "archive_name": asset.name}
                ),
                encoding="utf-8",
            )
            changed = update_latest_data(root)
        self.assertFalse(changed)


if __name__ == "__main__":
    unittest.main()
