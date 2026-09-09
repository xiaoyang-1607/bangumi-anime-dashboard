"""从 Bangumi 归档生成动画、游戏榜单数据。

默认只生成本地文件。只有显式传入 ``--publish`` 时才会提交并推送，避免一次
数据处理意外修改远端仓库。
"""

from __future__ import annotations

import argparse
from datetime import date
import subprocess
from pathlib import Path
from typing import Sequence

import pandas as pd

from config import (
    ANIME_CLEANED_FILE,
    ANIME_PARQUET_FILE,
    BANGUMI_APP_DATA_DIR,
    BANGUMI_DUMP_DIR,
    DATA_QUALITY_REPORT_FILE,
    GAME_CLEANED_FILE,
    GAME_PARQUET_FILE,
    JSONL_FILE_NAME,
    PROJECT_ROOT,
)
from get_source import (
    DATE_COLUMN_NAME,
    export_to_excel,
    export_to_parquet,
    process_subject_data,
    write_quality_report,
)


REQUIRED_COLUMNS = {
    "id", "name", "name_cn", "date", "release_status", "meta_tags",
    "user_tags", "score", "score_total", "rank", "favorite",
    "favorite_wish", "favorite_done", "favorite_doing", "favorite_on_hold",
    "favorite_dropped", "nsfw",
    "bayesian_score", "score_confidence",
}
VALID_RELEASE_STATUSES = {"released", "upcoming", "unknown_date"}
VALID_SCORE_CONFIDENCE = {"low", "medium", "high"}


def _parse_cli_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("日期必须使用 YYYY-MM-DD 格式") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="从 Bangumi Archive 生成 Parquet 与 XLSX 榜单"
    )
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
        "--as-of-date",
        type=_parse_cli_date,
        default=date.today(),
        help="用于区分已发行和未来作品的基准日期（YYYY-MM-DD）",
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


def validate_dataframe(data: pd.DataFrame, source_name: str) -> None:
    """验证数据结构、唯一性、取值范围和跨字段一致性。"""
    missing = REQUIRED_COLUMNS - set(data.columns)
    if missing:
        raise ValueError(f"{source_name} 缺少字段：{', '.join(sorted(missing))}")
    if data.empty:
        raise ValueError(f"{source_name} 没有数据行")
    if data["id"].isna().any() or (data["id"] <= 0).any():
        raise ValueError(f"{source_name} 存在无效 ID")
    if data["id"].duplicated().any():
        raise ValueError(f"{source_name} 存在重复 ID")
    if (data["name"].fillna("").astype(str).str.strip() == "").any():
        raise ValueError(f"{source_name} 存在空名称")
    if data["rank"].isna().any() or (data["rank"] <= 0).any():
        raise ValueError(f"{source_name} 存在无效榜单排名")
    if data["score"].isna().any() or not data["score"].between(0.01, 10).all():
        raise ValueError(f"{source_name} 存在无效评分")
    if data["score_total"].isna().any() or (data["score_total"] <= 0).any():
        raise ValueError(f"{source_name} 存在无效评分人数")
    if data["bayesian_score"].isna().any() or not data["bayesian_score"].between(0, 10).all():
        raise ValueError(f"{source_name} 存在无效综合评分")
    if data["favorite"].isna().any() or (data["favorite"] < 0).any():
        raise ValueError(f"{source_name} 存在无效收藏人数")
    favorite_columns = [
        "favorite_wish", "favorite_done", "favorite_doing",
        "favorite_on_hold", "favorite_dropped",
    ]
    if data[favorite_columns].isna().any().any() or (data[favorite_columns] < 0).any().any():
        raise ValueError(f"{source_name} 存在无效收藏状态计数")
    if not data[favorite_columns].sum(axis=1).eq(data["favorite"]).all():
        raise ValueError(f"{source_name} 的收藏总数与状态计数不一致")
    if data["score_confidence"].isna().any() or not set(
        data["score_confidence"]
    ).issubset(VALID_SCORE_CONFIDENCE):
        raise ValueError(f"{source_name} 存在无效评分可信度")
    if data["release_status"].isna().any() or not set(
        data["release_status"]
    ).issubset(VALID_RELEASE_STATUSES):
        raise ValueError(f"{source_name} 存在无效发行状态")
    if data["nsfw"].isna().any() or not data["nsfw"].isin([True, False, 0, 1]).all():
        raise ValueError(f"{source_name} 存在无效内容分级")

    parsed_dates = pd.to_datetime(data[DATE_COLUMN_NAME], errors="coerce")
    unknown_dates = data["release_status"] == "unknown_date"
    if parsed_dates[~unknown_dates].isna().any() or parsed_dates[unknown_dates].notna().any():
        raise ValueError(f"{source_name} 的日期与发行状态不一致")


def validate_data_file(path: Path) -> None:
    """读取并验证受支持的生成数据文件。"""
    if path.suffix.casefold() == ".parquet":
        data = pd.read_parquet(path, engine="pyarrow")
    elif path.suffix.casefold() == ".xlsx":
        data = pd.read_excel(path, engine="openpyxl")
    else:
        raise ValueError(f"不支持验证 {path.name}")
    validate_dataframe(data, path.name)


def validate_workbook(path: Path) -> None:
    """兼容旧调用的 Excel 校验入口。"""
    validate_data_file(path)


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
    dump_dir: Path,
    output_dir: Path,
    *,
    also_save_to_dump: bool = False,
    as_of_date: date | None = None,
) -> list[Path]:
    dump_dir = dump_dir.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    jsonl_path = dump_dir / JSONL_FILE_NAME
    if not jsonl_path.is_file():
        raise FileNotFoundError(f"未找到 {jsonl_path}")

    print(f"读取归档：{jsonl_path}")
    anime_data, game_data, quality_report = process_subject_data(
        jsonl_path, as_of_date=as_of_date, return_report=True
    )
    if anime_data is None or game_data is None or quality_report is None:
        raise RuntimeError("归档读取失败")
    if not anime_data or not game_data:
        raise ValueError("动画或游戏数据为空，已停止写入")

    output_directories = [output_dir]
    if also_save_to_dump and dump_dir != output_dir:
        output_directories.append(dump_dir)

    generated: list[Path] = []
    for directory in output_directories:
        targets = (
            (
                anime_data,
                directory / ANIME_PARQUET_FILE,
                directory / ANIME_CLEANED_FILE,
                "Anime_Subjects",
            ),
            (
                game_data,
                directory / GAME_PARQUET_FILE,
                directory / GAME_CLEANED_FILE,
                "Game_Subjects",
            ),
        )
        for records, parquet_path, excel_path, sheet_name in targets:
            if not export_to_parquet(records, parquet_path):
                raise RuntimeError(f"写入失败：{parquet_path}")
            if not export_to_excel(records, excel_path, sheet_name):
                raise RuntimeError(f"写入失败：{excel_path}")
            for path in (parquet_path, excel_path):
                validate_data_file(path)
                generated.append(path)
                print(f"[OK] 已验证：{path}")
        report_path = directory / DATA_QUALITY_REPORT_FILE
        if not write_quality_report(quality_report, report_path):
            raise RuntimeError(f"质量报告写入失败：{report_path}")
        generated.append(report_path)
    return generated


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        generated = generate_files(
            args.dump_dir,
            args.output_dir,
            also_save_to_dump=args.also_save_to_dump,
            as_of_date=args.as_of_date,
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
