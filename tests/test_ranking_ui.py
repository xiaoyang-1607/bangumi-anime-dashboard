from datetime import date
import unittest

import pandas as pd

from ranking_ui import (
    NAME_CN,
    RANK,
    SCORE,
    TAGS,
    apply_quick_preset,
    available_tags,
    filter_dataframe,
    load_from_dataframe,
)


class RankingDataTests(unittest.TestCase):
    def setUp(self):
        source = pd.DataFrame(
            [
                {
                    "id": 1,
                    "name": "Alpha [TV]",
                    "name_cn": "阿尔法",
                    "date": "2024-01-15",
                    "meta_tags": "科幻, 原创",
                    "score": 8.4,
                    "score_total": 1200,
                    "rank": 120,
                },
                {
                    "id": 2,
                    "name": "Beta",
                    "name_cn": None,
                    "date": "2023-06-01",
                    "meta_tags": "奇幻, 改编",
                    "score": 7.6,
                    "score_total": 300,
                    "rank": 800,
                },
                {
                    "id": 3,
                    "name": "Hard SF",
                    "name_cn": "硬科幻",
                    "date": "2024-12-31",
                    "meta_tags": "硬科幻, 原创",
                    "score": 9.0,
                    "score_total": 8000,
                    "rank": 20,
                },
            ]
        )
        self.data = load_from_dataframe(source, "开播日期")

    def test_normalizes_names_and_links(self):
        self.assertEqual(self.data.loc[1, NAME_CN], "Beta")
        self.assertEqual(self.data.loc[0, "Bangumi链接"], "https://bgm.tv/subject/1")

    def test_missing_required_column_has_clear_error(self):
        with self.assertRaisesRegex(ValueError, "score_total"):
            load_from_dataframe(
                pd.DataFrame(columns=["id", "name", "name_cn", "date", "score", "rank"]),
                "日期",
            )

    def test_search_is_literal_not_regex(self):
        result = filter_dataframe(
            self.data, date_column="开播日期", search_term="[", sort_by=SCORE
        )
        self.assertEqual(result[NAME_CN].tolist(), ["阿尔法"])

    def test_combined_filters_and_inclusive_end_date(self):
        result = filter_dataframe(
            self.data,
            date_column="开播日期",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            score_range=(8.0, 9.0),
            minimum_votes=1000,
            tags=["原创"],
            sort_by=RANK,
            ascending=True,
        )
        self.assertEqual(result[RANK].tolist(), [20, 120])

    def test_tag_filter_is_exact(self):
        result = filter_dataframe(
            self.data,
            date_column="开播日期",
            tags=["科幻"],
            sort_by=SCORE,
        )
        self.assertEqual(result[NAME_CN].tolist(), ["阿尔法"])
        self.assertIn("原创", available_tags(self.data))
        self.assertIn(TAGS, self.data.columns)

    def test_tag_filter_can_match_any_selected_tag(self):
        result = filter_dataframe(
            self.data,
            date_column="开播日期",
            tags=["科幻", "奇幻"],
            tag_match="any",
            sort_by=RANK,
            ascending=True,
        )
        self.assertEqual(result[NAME_CN].tolist(), ["阿尔法", "Beta"])

    def test_quick_presets_apply_expected_thresholds(self):
        high_score, labels = apply_quick_preset(self.data, "高分佳作", "开播日期")
        self.assertEqual(high_score[NAME_CN].tolist(), ["阿尔法", "硬科幻"])
        self.assertIn("评分 ≥ 8.0", labels)

        hidden_gems, _ = apply_quick_preset(self.data, "冷门佳作", "开播日期")
        self.assertEqual(hidden_gems[NAME_CN].tolist(), ["阿尔法"])


if __name__ == "__main__":
    unittest.main()
