import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class StreamlitUiSmokeTests(unittest.TestCase):
    def test_router_renders_overview(self):
        app = AppTest.from_file(PROJECT_ROOT / "app.py").run(timeout=60)
        self.assertEqual(list(app.exception), [])
        self.assertEqual(app.metric[0].label, "收录作品")
        self.assertEqual(len(app.get("page_link")), 2)

    def test_ranking_pages_render_filters_tabs_and_table(self):
        for path in (
            PROJECT_ROOT / "pages/pages1_Anime.py",
            PROJECT_ROOT / "pages/pages2_Game.py",
        ):
            with self.subTest(path=path):
                app = AppTest.from_file(path).run(timeout=60)
                self.assertEqual(list(app.exception), [])
                self.assertEqual(len(app.tabs), 2)
                self.assertEqual(len(app.dataframe), 1)
                self.assertEqual(len(app.get("download_button")), 1)
                self.assertEqual(len(app.date_input), 0)
                self.assertIn("起始月份", [widget.label for widget in app.selectbox])
                self.assertIn("结束月份", [widget.label for widget in app.selectbox])
                self.assertIn("找到", app.success[0].value)

    def test_quick_filter_and_reset_update_result_count(self):
        app = AppTest.from_file(PROJECT_ROOT / "pages/pages1_Anime.py").run(timeout=60)
        total = int(app.metric[0].value.replace(",", ""))
        initial_result = int(app.metric[1].value.replace(",", ""))

        app.selectbox[0].select("高分佳作")
        app.run(timeout=60)
        filtered = int(app.metric[1].value.replace(",", ""))
        self.assertGreater(filtered, 0)
        self.assertLess(filtered, initial_result)

        app.button[1].click()
        app.run(timeout=60)
        self.assertEqual(int(app.metric[1].value.replace(",", "")), initial_result)

    def test_full_table_view_is_available(self):
        app = AppTest.from_file(PROJECT_ROOT / "pages/pages1_Anime.py").run(timeout=60)
        table_control = next(item for item in app.radio if item.label == "显示字段")
        table_control.set_value("完整数据")
        app.run(timeout=60)
        self.assertEqual(list(app.exception), [])
        self.assertIn("上期排名", app.dataframe[0].value.columns)


if __name__ == "__main__":
    unittest.main()
