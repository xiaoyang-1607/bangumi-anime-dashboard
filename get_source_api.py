"""
从 Bangumi API 获取实时条目数据并导出为 Excel

使用 https://bangumi.github.io/api/ 的 REST API，无需归档数据库。
适用于小规模抓取或实时更新；全量数据建议仍使用归档（请求量大、耗时长）。

环境变量：
- BANGUMI_ACCESS_TOKEN: 可选，Access Token（https://next.bgm.tv/demo/access-token）
- BANGUMI_USER_AGENT: 可选，请求 User-Agent
- BANGUMI_DUMP_DIR: 输出目录，默认 ./data
- BANGUMI_API_MAX_ITEMS: 可选，每类最多获取条数（用于测试），默认不限制
"""
import os
import sys
from pathlib import Path

# 确保可导入项目模块
sys.path.insert(0, str(Path(__file__).resolve().parent))

from bangumi_api import TYPE_ANIME, TYPE_GAME, iter_all_subjects, subject_to_row
from config import BANGUMI_DUMP_DIR
from get_source import (
    DATE_COLUMN_NAME,
    EXCEL_DATE_FORMAT,
    apply_excel_date_format,
    export_to_excel,
)


def fetch_from_api(subject_type: int, type_name: str) -> list[dict]:
    """从 API 分页获取指定类型条目，过滤并转换为统一格式。"""
    max_items_str = os.environ.get("BANGUMI_API_MAX_ITEMS")
    max_items = int(max_items_str) if max_items_str else None

    rows = []
    for i, subject in enumerate(
        iter_all_subjects(subject_type=subject_type, sort="rank", max_items=max_items)
    ):
        row = subject_to_row(subject)
        if row:
            rows.append(row)
        if (i + 1) % 500 == 0:
            print(f"  已获取 {type_name} {len(rows)} 条...")
    return rows


def main():
    print("--- 1. 从 Bangumi API 获取动画数据 ---")
    anime_data = fetch_from_api(TYPE_ANIME, "动画")
    print(f"动画数据: {len(anime_data)} 条")

    print("\n--- 2. 从 Bangumi API 获取游戏数据 ---")
    game_data = fetch_from_api(TYPE_GAME, "游戏")
    print(f"游戏数据: {len(game_data)} 条")

    if not anime_data and not game_data:
        print("\n未获取到任何数据，请检查网络与 API 可用性。")
        return

    print("\n--- 3. 导出 Excel ---")
    anime_path = BANGUMI_DUMP_DIR / "bangumi_anime_data.xlsx"
    game_path = BANGUMI_DUMP_DIR / "bangumi_game_data.xlsx"
    BANGUMI_DUMP_DIR.mkdir(parents=True, exist_ok=True)

    anime_exported = export_to_excel(anime_data, anime_path, "Anime_Subjects")
    game_exported = export_to_excel(game_data, game_path, "Game_Subjects")

    print("\n--- 4. 日期格式修复 ---")
    if anime_exported:
        apply_excel_date_format(anime_path, DATE_COLUMN_NAME, EXCEL_DATE_FORMAT)
    if game_exported:
        apply_excel_date_format(game_path, DATE_COLUMN_NAME, EXCEL_DATE_FORMAT)

    print("\n=====================================")
    print("[OK] API 数据获取与导出已完成。")
    print(f"动画: {anime_path}")
    print(f"游戏: {game_path}")
    print("=====================================")


if __name__ == "__main__":
    main()
