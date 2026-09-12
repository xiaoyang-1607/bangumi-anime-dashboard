"""Bangumi Archive 的标准化、榜单准入、质量报告与 Parquet/Excel 导出工具。"""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timezone
import json
import math
from pathlib import Path
import unicodedata
from typing import Any

import pandas as pd


TYPE_ANIME = 2
TYPE_GAME = 4
DATE_COLUMN_NAME = "date"
EXCEL_DATE_FORMAT = "yyyy-mm-dd"
QUALITY_REPORT_SCHEMA_VERSION = 2
PIPELINE_VERSION = 3
MIN_USER_TAG_COUNT = 3
MAX_USER_TAGS = 20

_TAG_ALIASES = {"web": "WEB", "pc": "PC", "windows": "Windows"}


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(unicodedata.normalize("NFKC", str(value)).strip().split())


def _as_int(value: Any, *, minimum: int | None = None) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized or normalized.lstrip("+-").isdigit() is False:
            return None
        value = normalized
    try:
        number = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if isinstance(value, float) and not value.is_integer():
        return None
    if minimum is not None and number < minimum:
        return None
    return number


def _as_bool(value: Any) -> bool | None:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"true", "1"}:
            return True
        if normalized in {"false", "0"}:
            return False
    return None


def _normalize_tag(value: Any) -> str:
    if isinstance(value, dict):
        value = value.get("name") or value.get("title")
    cleaned = _clean_text(value)
    return _TAG_ALIASES.get(cleaned.casefold(), cleaned)


def _unique_tags(values: Any) -> list[str]:
    if not isinstance(values, list):
        values = [] if values is None else [values]
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        tag = _normalize_tag(value)
        key = tag.casefold()
        if tag and key not in seen:
            seen.add(key)
            result.append(tag)
    return result


def _user_tags(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    weighted: dict[str, tuple[str, int]] = {}
    for value in values:
        if not isinstance(value, dict):
            continue
        tag = _normalize_tag(value)
        count = _as_int(value.get("count"), minimum=0)
        if not tag or count is None or count < MIN_USER_TAG_COUNT:
            continue
        key = tag.casefold()
        previous = weighted.get(key)
        if previous is None or count > previous[1]:
            weighted[key] = (tag, count)
    ordered = sorted(weighted.values(), key=lambda item: (-item[1], item[0].casefold()))
    return [tag for tag, _ in ordered[:MAX_USER_TAGS]]


def _score_distribution(value: Any) -> tuple[int, float | None, float | None] | None:
    """返回评分人数、均值和样本方差；结构损坏时返回 None。"""
    if not isinstance(value, dict):
        return None
    total = 0
    weighted = 0
    weighted_square = 0
    for raw_rating, raw_count in value.items():
        rating = _as_int(raw_rating)
        count = _as_int(raw_count, minimum=0)
        if rating is None or not 1 <= rating <= 10 or count is None:
            return None
        total += count
        weighted += rating * count
        weighted_square += rating * rating * count
    if total == 0:
        return 0, None, None
    mean = weighted / total
    variance = max(0.0, (weighted_square - total * mean * mean) / (total - 1)) if total > 1 else None
    return total, mean, variance


def _favorite_counts(value: Any) -> tuple[dict[str, int], bool] | None:
    """标准化收藏状态；返回各状态计数和是否使用了缺失值默认项。"""
    keys = ("wish", "done", "doing", "on_hold", "dropped")
    if value is None:
        return {key: 0 for key in keys}, True
    if not isinstance(value, dict):
        return None
    counts: dict[str, int] = {}
    defaulted = False
    for key in keys:
        if key not in value:
            defaulted = True
        count = _as_int(value.get(key, 0), minimum=0)
        if count is None:
            return None
        counts[key] = count
    return counts, defaulted


def _parse_date(value: Any) -> date | None | bool:
    """缺失返回 None，合法返回 date，格式错误返回 False。"""
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return False


def _normalize_subject(
    subject: dict[str, Any], as_of_date: date
) -> tuple[dict[str, Any] | None, str | None, list[str]]:
    """标准化单条记录，返回记录、硬错误原因和非阻断警告。"""
    warnings: list[str] = []
    subject_id = _as_int(subject.get("id"), minimum=1)
    if subject_id is None:
        return None, "invalid_id", warnings

    original_name = _clean_text(subject.get("name"))
    chinese_name = _clean_text(subject.get("name_cn"))
    if not original_name and not chinese_name:
        return None, "missing_name", warnings
    original_name = original_name or chinese_name
    chinese_name = chinese_name or original_name

    parsed_date = _parse_date(subject.get("date"))
    if parsed_date is False:
        return None, "invalid_date", warnings
    release_status = (
        "unknown_date"
        if parsed_date is None
        else "upcoming"
        if parsed_date > as_of_date
        else "released"
    )

    distribution = _score_distribution(subject.get("score_details"))
    if distribution is None:
        return None, "invalid_score_details", warnings
    score_total, distribution_mean, distribution_variance = distribution
    raw_score = subject.get("score")
    if isinstance(raw_score, bool):
        return None, "invalid_score", warnings
    try:
        score = float(raw_score or 0)
    except (TypeError, ValueError):
        return None, "invalid_score", warnings
    if not math.isfinite(score) or not 0 <= score <= 10:
        return None, "invalid_score", warnings
    if distribution_mean is not None and abs(distribution_mean - score) > 0.11:
        warnings.append("score_distribution_mismatch")

    raw_rank = subject.get("rank")
    rank = 0 if raw_rank in (None, "") else _as_int(raw_rank, minimum=0)
    if rank is None:
        return None, "invalid_rank", warnings

    favorite_result = _favorite_counts(subject.get("favorite"))
    if favorite_result is None:
        return None, "invalid_favorite", warnings
    favorite_counts, favorite_defaulted = favorite_result
    if favorite_defaulted:
        warnings.append("favorite_defaulted")

    nsfw = _as_bool(subject.get("nsfw"))
    if nsfw is None:
        return None, "invalid_nsfw", warnings

    record = {
        "id": subject_id,
        "name": original_name,
        "name_cn": chinese_name,
        "date": parsed_date.isoformat() if isinstance(parsed_date, date) else None,
        "release_status": release_status,
        "meta_tags": ", ".join(_unique_tags(subject.get("meta_tags"))),
        "user_tags": ", ".join(_user_tags(subject.get("tags"))),
        "score": score,
        "score_total": score_total,
        "_rating_variance": distribution_variance,
        "rank": rank,
        "favorite": sum(favorite_counts.values()),
        **{
            f"favorite_{status}": count
            for status, count in favorite_counts.items()
        },
        "nsfw": nsfw,
        "platform": _as_int(subject.get("platform"), minimum=0),
    }
    return record, None, warnings


def _ranking_exclusion(record: dict[str, Any]) -> str | None:
    """榜单准入属于产品规则，不属于数据有效性判断。"""
    if record["score_total"] == 0 or record["score"] == 0:
        return "no_ratings"
    if record["rank"] == 0:
        return "unranked"
    return None


def _add_derived_scores(records: list[dict[str, Any]]) -> dict[str, float | int | None]:
    """用类别内矩估计正态层级模型参数，再计算后验均值。"""
    if not records:
        return {"prior_mean": None, "within_variance": None, "between_variance": None,
                "equivalent_prior_votes": None, "subjects": 0}
    subject_count = len(records)
    global_mean = sum(record["score"] for record in records) / subject_count
    variance_numerator = sum(
        (record["score"] - global_mean) ** 2 for record in records
    )
    observed_variance = variance_numerator / (subject_count - 1) if subject_count > 1 else 0.0
    pooled_variance_numerator = sum(
        (record["score_total"] - 1) * record["_rating_variance"]
        for record in records
        if record["score_total"] > 1 and record["_rating_variance"] is not None
    )
    pooled_degrees = sum(
        record["score_total"] - 1 for record in records if record["score_total"] > 1
    )
    within_variance = pooled_variance_numerator / pooled_degrees if pooled_degrees else 0.0
    average_sampling_variance = within_variance * sum(
        1 / record["score_total"] for record in records
    ) / subject_count
    between_variance = max(0.0, observed_variance - average_sampling_variance)

    for record in records:
        votes = record["score_total"]
        sampling_variance = within_variance / votes
        total_variance = between_variance + sampling_variance
        weight = between_variance / total_variance if total_variance else 0.0
        record["bayesian_score"] = round(
            global_mean + weight * (record["score"] - global_mean),
            3,
        )
        record["score_confidence"] = (
            "high" if votes >= 1_000 else "medium" if votes >= 100 else "low"
        )
        record.pop("_rating_variance")
    return {
        "prior_mean": round(global_mean, 6),
        "within_variance": round(within_variance, 6),
        "between_variance": round(between_variance, 6),
        "equivalent_prior_votes": (
            round(within_variance / between_variance, 3) if between_variance else None
        ),
        "subjects": subject_count,
    }


def _add_rank_movement(
    records: list[dict[str, Any]],
    previous_ranks: dict[int, int] | None,
    previous_movement: dict[int, dict[str, Any]] | None,
) -> Counter[str]:
    movements: Counter[str] = Counter()
    for record in records:
        subject_id = record["id"]
        if previous_movement is not None and subject_id in previous_movement:
            prior = previous_movement[subject_id]
            record["previous_rank"] = prior.get("previous_rank")
            record["rank_change"] = prior.get("rank_change")
            record["rank_change_status"] = prior.get("rank_change_status", "baseline")
        elif previous_ranks is None:
            record.update(previous_rank=None, rank_change=None, rank_change_status="baseline")
        else:
            previous_rank = previous_ranks.get(subject_id)
            if previous_rank is None:
                record.update(previous_rank=None, rank_change=None, rank_change_status="new")
            else:
                change = previous_rank - record["rank"]
                status = "up" if change > 0 else "down" if change < 0 else "same"
                record.update(
                    previous_rank=previous_rank,
                    rank_change=change,
                    rank_change_status=status,
                )
        movements[record["rank_change_status"]] += 1
    return movements


def process_subject_data(
    jsonl_path: str | Path,
    *,
    as_of_date: date | None = None,
    return_report: bool = False,
    previous_rankings: dict[int, dict[int, int]] | None = None,
    previous_movements: dict[int, dict[int, dict[str, Any]]] | None = None,
    comparison_archive: str | None = None,
):
    """流式标准化归档，派生动画/游戏榜单，并可返回质量报告。"""
    path = Path(jsonl_path)
    reference_date = as_of_date or date.today()
    anime_records: list[dict[str, Any]] = []
    game_records: list[dict[str, Any]] = []
    counters: Counter[str] = Counter()
    warning_counts: Counter[str] = Counter()
    seen_ids: set[int] = set()

    print(f"正在读取：{path}")
    try:
        with path.open("r", encoding="utf-8-sig") as source:
            for line_number, line in enumerate(source, 1):
                counters["input_lines"] += 1
                try:
                    subject = json.loads(line)
                except json.JSONDecodeError as exc:
                    counters["invalid_json"] += 1
                    print(f"[WARN] 第 {line_number} 行 JSON 无效：{exc}")
                    continue
                if not isinstance(subject, dict):
                    counters["non_object_json"] += 1
                    continue
                if subject.get("type") not in (TYPE_ANIME, TYPE_GAME):
                    counters["unsupported_type"] += 1
                    continue
                counters["supported_type"] += 1

                record, error, warnings = _normalize_subject(subject, reference_date)
                if error:
                    counters[error] += 1
                    continue
                assert record is not None
                if record["id"] in seen_ids:
                    counters["duplicate_id"] += 1
                    continue
                seen_ids.add(record["id"])
                counters["normalized"] += 1
                warning_counts.update(warnings)

                exclusion = _ranking_exclusion(record)
                if exclusion:
                    counters[exclusion] += 1
                    continue
                if record["release_status"] == "unknown_date":
                    counters["ranked_unknown_date"] += 1
                elif record["release_status"] == "upcoming":
                    counters["ranked_upcoming"] += 1
                if record["nsfw"]:
                    counters["ranked_nsfw"] += 1
                if not record["meta_tags"]:
                    counters["ranked_without_meta_tags"] += 1

                target = anime_records if subject["type"] == TYPE_ANIME else game_records
                target.append(record)
    except (OSError, UnicodeError) as exc:
        print(f"[ERROR] 无法读取归档：{exc}")
        return (None, None, None) if return_report else (None, None)

    score_models = {}
    movement_counts: Counter[str] = Counter()
    for category, records in ((TYPE_ANIME, anime_records), (TYPE_GAME, game_records)):
        score_models["anime" if category == TYPE_ANIME else "game"] = _add_derived_scores(records)
        movement_counts.update(_add_rank_movement(
            records,
            previous_rankings.get(category) if previous_rankings else None,
            previous_movements.get(category) if previous_movements else None,
        ))
        records.sort(key=lambda record: (record["rank"], record["id"]))

    count_keys = (
        "input_lines", "invalid_json", "non_object_json", "unsupported_type",
        "supported_type", "invalid_id", "missing_name", "invalid_date",
        "invalid_score_details", "invalid_score", "invalid_rank",
        "invalid_favorite", "invalid_nsfw", "duplicate_id", "normalized",
        "no_ratings", "unranked",
        "ranked_unknown_date", "ranked_upcoming", "ranked_nsfw",
        "ranked_without_meta_tags",
    )
    hard_error_keys = (
        "invalid_id", "missing_name", "invalid_date", "invalid_score_details",
        "invalid_score", "invalid_rank", "invalid_favorite", "invalid_nsfw",
        "duplicate_id",
    )
    report = {
        "schema_version": QUALITY_REPORT_SCHEMA_VERSION,
        "pipeline_version": PIPELINE_VERSION,
        "source_file": path.name,
        "as_of_date": reference_date.isoformat(),
        "comparison_archive": comparison_archive,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": {key: counters[key] for key in count_keys},
        "warnings": {
            key: warning_counts[key]
            for key in ("score_distribution_mismatch", "favorite_defaulted")
        },
        "score_model": score_models,
        "rank_movement": {
            key: movement_counts[key] for key in ("up", "down", "same", "new", "baseline")
        },
        "output": {
            "anime_records": len(anime_records),
            "game_records": len(game_records),
            "total_records": len(anime_records) + len(game_records),
        },
    }
    print(
        f"处理完成：动画 {len(anime_records):,} 条，游戏 {len(game_records):,} 条；"
        f"未评分 {counters['no_ratings']:,} 条、未上榜 {counters['unranked']:,} 条、"
        f"硬错误 {sum(counters[key] for key in hard_error_keys):,} 条。"
    )
    if return_report:
        return anime_records, game_records, report
    return anime_records, game_records


def export_to_excel(data_list, output_path: str | Path, sheet_name: str) -> bool:
    """标准化日期后一次性写入带日期格式的 Excel。"""
    path = Path(output_path)
    if not data_list:
        print(f"[WARN] {sheet_name} 没有可导出的数据")
        return False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = pd.DataFrame(data_list)
        data[DATE_COLUMN_NAME] = pd.to_datetime(data[DATE_COLUMN_NAME], errors="coerce")
        with pd.ExcelWriter(
            path, engine="xlsxwriter", datetime_format=EXCEL_DATE_FORMAT
        ) as writer:
            data.to_excel(writer, index=False, sheet_name=sheet_name)
        return True
    except (OSError, ValueError) as exc:
        print(f"[ERROR] 无法导出 {path}：{exc}")
        return False


def export_to_parquet(data_list, output_path: str | Path) -> bool:
    """写入供应用直接读取的类型化 Parquet 数据。"""
    path = Path(output_path)
    if not data_list:
        print(f"[WARN] {path.name} 没有可导出的数据")
        return False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = pd.DataFrame(data_list)
        data[DATE_COLUMN_NAME] = pd.to_datetime(data[DATE_COLUMN_NAME], errors="coerce")
        data.to_parquet(path, engine="pyarrow", compression="zstd", index=False)
        return True
    except (OSError, ValueError, ImportError) as exc:
        print(f"[ERROR] 无法导出 {path}：{exc}")
        return False


def write_quality_report(report: dict[str, Any], output_path: str | Path) -> bool:
    path = Path(output_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return True
    except OSError as exc:
        print(f"[ERROR] 无法写入质量报告 {path}：{exc}")
        return False


def apply_excel_date_format(
    file_path: str | Path, column_name: str, date_format: str
) -> bool:
    """兼容旧调用：重写已有 Excel 的日期格式。"""
    path = Path(file_path)
    if not path.is_file():
        return False
    try:
        with pd.ExcelFile(path, engine="openpyxl") as workbook:
            sheet_name = workbook.sheet_names[0]
            data = pd.read_excel(workbook, sheet_name=sheet_name)
        if column_name not in data.columns:
            return False
        data[column_name] = pd.to_datetime(data[column_name], errors="coerce")
        with pd.ExcelWriter(path, engine="xlsxwriter", datetime_format=date_format) as writer:
            data.to_excel(writer, index=False, sheet_name=sheet_name)
        return True
    except (OSError, ValueError):
        return False
