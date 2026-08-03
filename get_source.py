"""Bangumi Archive 的 JSONL 读取与 Excel 导出工具。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


TYPE_ANIME = 2
TYPE_GAME = 4
DATE_COLUMN_NAME = "date"
EXCEL_DATE_FORMAT = "yyyy-mm-dd"


def _tag_name(tag: Any) -> str:
    if isinstance(tag, dict):
        return str(tag.get("name") or tag.get("title") or "").strip()
    return str(tag).strip()


def _score_total(score_details: Any) -> int:
    if not isinstance(score_details, dict):
        return 0
    total = 0
    for value in score_details.values():
        try:
            total += int(value)
        except (TypeError, ValueError):
            continue
    return total


def process_subject_data(jsonl_path: str | Path):
    """流式读取归档，并返回动画与游戏两组清洗记录。"""
    path = Path(jsonl_path)
    anime_records: list[dict[str, Any]] = []
    game_records: list[dict[str, Any]] = []
    skipped_missing_date = 0
    skipped_invalid_json = 0

    print(f"正在读取：{path}")
    try:
        with path.open("r", encoding="utf-8-sig") as source:
            for line_number, line in enumerate(source, 1):
                try:
                    subject = json.loads(line)
                except json.JSONDecodeError as exc:
                    skipped_invalid_json += 1
                    print(f"[WARN] 第 {line_number} 行 JSON 无效：{exc}")
                    continue

                if not isinstance(subject, dict):
                    skipped_invalid_json += 1
                    print(f"[WARN] 第 {line_number} 行不是 JSON 对象，已跳过")
                    continue

                subject_type = subject.get("type")
                if subject_type not in (TYPE_ANIME, TYPE_GAME) or subject.get("rank") == 0:
                    continue
                if not subject.get("date"):
                    skipped_missing_date += 1
                    continue

                original_name = subject.get("name") or ""
                raw_tags = subject.get("meta_tags") or []
                if not isinstance(raw_tags, list):
                    raw_tags = [raw_tags]
                tags = [name for tag in raw_tags if (name := _tag_name(tag))]
                record = {
                    "id": subject.get("id"),
                    "name": original_name,
                    "name_cn": subject.get("name_cn") or original_name,
                    "date": subject.get("date"),
                    "meta_tags": ", ".join(tags),
                    "score": subject.get("score"),
                    "score_total": _score_total(subject.get("score_details")),
                    "rank": subject.get("rank"),
                }
                target = anime_records if subject_type == TYPE_ANIME else game_records
                target.append(record)
    except (OSError, UnicodeError) as exc:
        print(f"[ERROR] 无法读取归档：{exc}")
        return None, None

    print(
        f"处理完成：动画 {len(anime_records):,} 条，游戏 {len(game_records):,} 条；"
        f"跳过无日期 {skipped_missing_date:,} 条、无效 JSON {skipped_invalid_json:,} 条。"
    )
    return anime_records, game_records


def export_to_excel(data_list, output_path: str | Path, sheet_name: str) -> bool:
    """把记录写入 Excel。"""
    path = Path(output_path)
    if not data_list:
        print(f"[WARN] {sheet_name} 没有可导出的数据")
        return False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(data_list).to_excel(
            path, index=False, sheet_name=sheet_name, engine="xlsxwriter"
        )
        return True
    except (OSError, ValueError) as exc:
        print(f"[ERROR] 无法导出 {path}：{exc}")
        return False


def apply_excel_date_format(
    file_path: str | Path, column_name: str, date_format: str
) -> bool:
    """把指定列转换为真正的 Excel 日期，并保留原工作表名称。"""
    path = Path(file_path)
    if not path.is_file():
        print(f"[ERROR] 文件不存在：{path}")
        return False
    try:
        with pd.ExcelFile(path, engine="openpyxl") as workbook:
            sheet_name = workbook.sheet_names[0]
            data = pd.read_excel(workbook, sheet_name=sheet_name)
        if column_name not in data.columns:
            print(f"[ERROR] {path.name} 缺少日期列 {column_name}")
            return False
        data[column_name] = pd.to_datetime(data[column_name], errors="coerce")
        with pd.ExcelWriter(
            path, engine="xlsxwriter", datetime_format=date_format
        ) as writer:
            data.to_excel(writer, index=False, sheet_name=sheet_name)
        return True
    except (OSError, ValueError) as exc:
        print(f"[ERROR] 无法格式化 {path}：{exc}")
        return False
