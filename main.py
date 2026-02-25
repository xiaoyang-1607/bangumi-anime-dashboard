"""
从 Bangumi 归档解压目录读取 subject.jsonlines，清洗并导出 anime_cleaned.xlsx、game_cleaned.xlsx，
同时保存到解压目录与项目根目录，格式检查通过后自动提交并推送到 GitHub。
"""
import subprocess
import sys
from pathlib import Path

import pandas as pd

from get_source import (
    DATE_COLUMN_NAME,
    EXCEL_DATE_FORMAT,
    apply_excel_date_format,
    export_to_excel,
    process_subject_data,
)

# ---------- 手动设置：归档解压目录（内含 subject.jsonlines） ----------
DUMP_DIR = Path(r"D:\桌面\others\dump-2026-02-24.210320Z")
# --------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent
JSONL_FILE = "subject.jsonlines"
ANIME_FILE = "anime_cleaned.xlsx"
GAME_FILE = "game_cleaned.xlsx"

REQUIRED_COLUMNS = {"id", "name", "name_cn", "date", "score", "score_total", "rank"}


def run():
    jsonl_path = DUMP_DIR / JSONL_FILE
    if not jsonl_path.exists():
        print(f"错误: 未找到 {jsonl_path}，请检查 DUMP_DIR 并确保已解压归档。")
        sys.exit(1)

    print("--- 1. 读取并处理 JSONL ---")
    anime_data, game_data = process_subject_data(jsonl_path)
    if anime_data is None and game_data is None:
        print("数据处理失败，已退出。")
        sys.exit(1)

    out_dirs = [DUMP_DIR, PROJECT_ROOT]
    anime_paths = [d / ANIME_FILE for d in out_dirs]
    game_paths = [d / GAME_FILE for d in out_dirs]

    print("\n--- 2. 导出 Excel（解压目录 + 项目目录，若已有同名文件则覆盖）---")
    for path in anime_paths:
        export_to_excel(anime_data, path, "Anime_Subjects")
    for path in game_paths:
        export_to_excel(game_data, path, "Game_Subjects")

    print("\n--- 3. 日期格式修复 ---")
    for path in anime_paths + game_paths:
        if path.exists():
            apply_excel_date_format(path, DATE_COLUMN_NAME, EXCEL_DATE_FORMAT)

    # 只对项目目录下实际存在的文件做格式检查与 Git 操作
    anime_project = PROJECT_ROOT / ANIME_FILE
    game_project = PROJECT_ROOT / GAME_FILE
    project_files = [(ANIME_FILE, anime_project), (GAME_FILE, game_project)]
    existing_project_files = [(name, path) for name, path in project_files if path.exists()]

    if not existing_project_files:
        print("错误: 项目目录下未生成任何 xlsx 文件（动画与游戏数据均为空时不会生成文件）。")
        sys.exit(1)

    print("\n--- 4. 格式检查（项目目录下的文件）---")
    for name, path in existing_project_files:
        try:
            df = pd.read_excel(path, engine="openpyxl")
        except Exception as e:
            print(f"格式检查失败 [{name}]: 无法读取文件 - {e}")
            sys.exit(1)
        missing = REQUIRED_COLUMNS - set(df.columns)
        if missing:
            print(f"格式检查失败 [{name}]: 缺少列 {missing}")
            sys.exit(1)
        if df.empty:
            print(f"格式检查警告 [{name}]: 无数据行，仍将上传。")
    print("[OK] 格式检查通过。")

    print("\n--- 5. 提交并推送到 GitHub（用新生成的文件替换仓库中已有的 xlsx）---")
    try:
        to_add = [name for name, _ in existing_project_files]
        subprocess.run(
            ["git", "add"] + to_add,
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        r = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            subprocess.run(
                ["git", "commit", "-m", "Update anime_cleaned.xlsx and game_cleaned.xlsx"],
                cwd=PROJECT_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["git", "push", "origin", "main"],
                cwd=PROJECT_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            print("[OK] 已推送到 GitHub。")
        else:
            print("文件无变化，未执行提交与推送。")
    except subprocess.CalledProcessError as e:
        print(f"Git 操作失败: {e}")
        if e.stderr:
            print(e.stderr)
        sys.exit(1)

    print("\n=====================================")
    print("完成。已保存的文件:")
    for d in out_dirs:
        for name in (ANIME_FILE, GAME_FILE):
            p = d / name
            if p.exists():
                print(f"  - {p}")
    print("=====================================")


if __name__ == "__main__":
    run()
