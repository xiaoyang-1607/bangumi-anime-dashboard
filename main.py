"""从 Bangumi 归档生成动画、游戏榜单数据。

默认只生成本地文件。只有显式传入 ``--publish`` 时才会提交并推送，避免一次
数据处理意外修改远端仓库。
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import Sequence

import pandas as pd

from config import (
    ANIME_CLEANED_FILE,
    BANGUMI_APP_DATA_DIR,
    BANGUMI_DUMP_DIR,
    GAME_CLEANED_FILE,
    JSONL_FILE_NAME,
    PROJECT_ROOT,
)
from get_source import (
    DATE_COLUMN_NAME,
    EXCEL_DATE_FORMAT,
    apply_excel_date_format,
    export_to_excel,
    process_subject_data,
)


REQUIRED_COLUMNS = {"id", "name", "name_cn", "date", "score", "score_total", "rank"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="从 Bangumi Archive 生成榜单 Excel")
    parser.add_argument(
        "--dump-dir",
        type=Path,
        default=BANGUMI_DUMP_DIR,
        help="包含 subject.jsonlines 的归档目录（默认读取 BANGUMI_DUMP_DIR）",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=BANGUMI_APP_DATA_DIR,
        help="榜单输出目录（默认读取 BANGUMI_APP_DATA_DIR）",
    )
    parser.add_argument(
        "--also-save-to-dump",
        action="store_true",
        help="同时把生成文件写入归档目录",
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="生成成功后提交并推送输出文件（默认不执行 Git 写操作）",
    )
    parser.add_argument("--remote", default="origin", help="推送目标 remote")
    parser.add_argument("--branch", help="推送目标分支，默认使用当前分支")
    parser.add_argument(
        "--commit-message",
        default="Update Bangumi ranking data",
        help="自动提交的说明",
    )
    return parser


def validate_workbook(path: Path) -> None:
    """确认生成文件可读、非空且包含页面依赖的所有字段。"""
    data = pd.read_excel(path, engine="openpyxl")
    missing = REQUIRED_COLUMNS - set(data.columns)
    if missing:
        raise ValueError(f"{path.name} 缺少字段：{', '.join(sorted(missing))}")
    if data.empty:
        raise ValueError(f"{path.name} 没有数据行")
    if pd.to_datetime(data[DATE_COLUMN_NAME], errors="coerce").isna().all():
        raise ValueError(f"{path.name} 的日期列全部无效")


def _run_git(arguments: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def publish_files(
    paths: Sequence[Path], *, remote: str, branch: str | None, message: str
) -> bool:
    """只提交指定输出文件；没有内容变化时返回 False。"""
    relative_paths = []
    for path in paths:
        try:
            relative_paths.append(str(path.resolve().relative_to(PROJECT_ROOT.resolve())))
        except ValueError as exc:
            raise ValueError("--publish 仅支持项目目录内的输出文件") from exc

    _run_git(["add", "--", *relative_paths])
    diff = subprocess.run(
        ["git", "diff", "--cached", "--quiet", "--", *relative_paths],
        cwd=PROJECT_ROOT,
        capture_output=True,
    )
    if diff.returncode == 0:
        print("输出数据没有变化，跳过提交和推送。")
        return False
    if diff.returncode != 1:
        raise RuntimeError("无法检查暂存区差异")

    _run_git(["commit", "-m", message, "--", *relative_paths])
    target_branch = branch
    if not target_branch:
        target_branch = _run_git(["branch", "--show-current"]).stdout.strip()
    if not target_branch:
        raise ValueError("当前处于 detached HEAD，请使用 --branch 指定目标分支")
    _run_git(["push", remote, f"HEAD:{target_branch}"])
    print(f"[OK] 已推送到 {remote}/{target_branch}")
    return True


def generate_files(
    dump_dir: Path, output_dir: Path, *, also_save_to_dump: bool = False
) -> list[Path]:
    dump_dir = dump_dir.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    jsonl_path = dump_dir / JSONL_FILE_NAME
    if not jsonl_path.is_file():
        raise FileNotFoundError(f"未找到 {jsonl_path}")

    print(f"读取归档：{jsonl_path}")
    anime_data, game_data = process_subject_data(jsonl_path)
    if anime_data is None or game_data is None:
        raise RuntimeError("归档读取失败")
    if not anime_data or not game_data:
        raise ValueError("动画或游戏数据为空，已停止写入")

    output_directories = [output_dir]
    if also_save_to_dump and dump_dir != output_dir:
        output_directories.append(dump_dir)

    generated: list[Path] = []
    for directory in output_directories:
        targets = (
            (anime_data, directory / ANIME_CLEANED_FILE, "Anime_Subjects"),
            (game_data, directory / GAME_CLEANED_FILE, "Game_Subjects"),
        )
        for records, path, sheet_name in targets:
            if not export_to_excel(records, path, sheet_name):
                raise RuntimeError(f"写入失败：{path}")
            if not apply_excel_date_format(path, DATE_COLUMN_NAME, EXCEL_DATE_FORMAT):
                raise RuntimeError(f"日期格式化失败：{path}")
            validate_workbook(path)
            generated.append(path)
            print(f"[OK] 已验证：{path}")
    return generated


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        generated = generate_files(
            args.dump_dir,
            args.output_dir,
            also_save_to_dump=args.also_save_to_dump,
        )
        if args.publish:
            primary_output = args.output_dir.expanduser().resolve()
            publish_files(
                [path for path in generated if path.parent == primary_output],
                remote=args.remote,
                branch=args.branch,
                message=args.commit_message,
            )
    except (FileNotFoundError, RuntimeError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"[ERROR] {exc}")
        if isinstance(exc, subprocess.CalledProcessError) and exc.stderr:
            print(exc.stderr.strip())
        return 1

    print("生成完成：")
    for path in generated:
        print(f"  - {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
