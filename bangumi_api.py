"""
Bangumi API 客户端

基于 https://bangumi.github.io/api/ 的 REST API 获取实时条目数据。
需设置 User-Agent，可选 Access Token（见 https://next.bgm.tv/demo/access-token）。
"""
import os
import time
from typing import Any, Generator, Optional

import requests

API_BASE = "https://api.bgm.tv"
DEFAULT_LIMIT = 50
DEFAULT_USER_AGENT = "BangumiAnimeDashboard/1.0 (https://github.com/xiaoyang-1607/bangumi-anime-dashboard)"

# Subject type: 1=Book, 2=Anime, 3=Music, 4=Game, 6=Real
TYPE_ANIME = 2
TYPE_GAME = 4


def _get_headers() -> dict:
    headers = {"User-Agent": os.environ.get("BANGUMI_USER_AGENT", DEFAULT_USER_AGENT)}
    token = os.environ.get("BANGUMI_ACCESS_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def get_subjects(
    subject_type: int,
    sort: str = "rank",
    year: Optional[int] = None,
    month: Optional[int] = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> dict[str, Any]:
    """
    浏览条目 GET /v0/subjects
    subject_type: 2=Anime, 4=Game
    sort: 'date' | 'rank'
    """
    params: dict = {"type": subject_type, "sort": sort, "limit": limit, "offset": offset}
    if year is not None:
        params["year"] = year
    if month is not None:
        params["month"] = month

    resp = requests.get(
        f"{API_BASE}/v0/subjects",
        params=params,
        headers=_get_headers(),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def search_subjects(
    keyword: str = "",
    subject_type: Optional[list[int]] = None,
    sort: str = "rank",
    limit: int = 50,
    offset: int = 0,
    air_date: Optional[list[str]] = None,
    rating: Optional[list[str]] = None,
    rating_count: Optional[list[str]] = None,
    meta_tags: Optional[list[str]] = None,
    rank_filter: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    条目搜索 POST /v0/search/subjects，先筛选后获取。
    filter: air_date 如 [">=2020-01-01", "<2024-01-01"], rating 如 [">=7", "<=9"],
    rating_count 如 [">=100"], meta_tags 如 ["科幻", "原创"]。
    """
    body: dict = {"keyword": keyword or " ", "sort": sort}
    flt: dict = {}
    if subject_type:
        flt["type"] = subject_type
    if air_date:
        flt["air_date"] = air_date
    if rating:
        flt["rating"] = rating
    if rating_count:
        flt["rating_count"] = rating_count
    if meta_tags:
        flt["meta_tags"] = meta_tags
    if rank_filter:
        flt["rank"] = rank_filter
    if flt:
        body["filter"] = flt

    resp = requests.post(
        f"{API_BASE}/v0/search/subjects",
        json=body,
        params={"limit": limit, "offset": offset},
        headers={**_get_headers(), "Content-Type": "application/json"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_ranking_with_filters(
    subject_type: int,
    limit: int = 100,
    air_date: Optional[list[str]] = None,
    rating_min: Optional[float] = None,
    rating_max: Optional[float] = None,
    rating_count_min: Optional[int] = None,
    meta_tags: Optional[list[str]] = None,
) -> list[dict]:
    """
    带筛选的排行获取：有筛选时用 search API，无筛选时用 get_subjects。
    先筛选后获取，减少请求量。
    """
    rows = []
    offset = 0
    use_search = air_date or rating_min is not None or rating_max is not None or rating_count_min or meta_tags

    rating_filters = []
    if rating_min is not None:
        rating_filters.append(f">={rating_min}")
    if rating_max is not None:
        rating_filters.append(f"<={rating_max}")
    if not rating_filters:
        rating_filters = None

    rating_count_filters = [f">={rating_count_min}"] if rating_count_min else None

    while len(rows) < limit:
        try:
            if use_search:
                data = search_subjects(
                    keyword=" ",
                    subject_type=[subject_type],
                    sort="rank",
                    limit=min(50, limit - len(rows)),
                    offset=offset,
                    air_date=air_date,
                    rating=rating_filters,
                    rating_count=rating_count_filters,
                    meta_tags=meta_tags,
                )
            else:
                data = get_subjects(
                    subject_type=subject_type,
                    sort="rank",
                    limit=min(50, limit - len(rows)),
                    offset=offset,
                )
        except requests.RequestException as e:
            raise RuntimeError(f"API 请求失败: {e}") from e

        items = data.get("data", [])
        allow_unranked = use_search  # Search API 常返回未上榜条目
        for s in items:
            row = subject_to_row(s, allow_unranked=allow_unranked)
            if row:
                rows.append(row)
                if len(rows) >= limit:
                    break

        if not items or len(items) < 50:
            break
        offset += 50

    return rows


def iter_all_subjects(
    subject_type: int,
    sort: str = "rank",
    delay: float = 0.5,
    max_items: Optional[int] = None,
) -> Generator[dict, None, None]:
    """
    分页遍历指定类型的所有条目，遵守延迟避免触发限流。
    max_items: 最多获取条数，None 表示不限制。
    """
    offset = 0
    yielded = 0
    while True:
        try:
            data = get_subjects(
                subject_type=subject_type, sort=sort, limit=DEFAULT_LIMIT, offset=offset
            )
        except requests.RequestException as e:
            raise RuntimeError(f"API 请求失败: {e}") from e

        items = data.get("data", [])
        total = data.get("total", 0)

        for item in items:
            yield item
            yielded += 1
            if max_items and yielded >= max_items:
                return

        if not items or offset + len(items) >= total:
            break
        offset += len(items)
        time.sleep(delay)


def subject_to_row(subject: dict, allow_unranked: bool = False) -> Optional[dict]:
    """
    将 API Subject 转为与 get_source.py 一致的字段格式。
    API 中 rank 在 rating 内，日期字段为 date 或 air_date。
    allow_unranked: 为 True 时接受 rank=0 的条目（Search API 常返回未上榜条目）。
    """
    rating = subject.get("rating") or {}
    rank = rating.get("rank") or subject.get("rank")
    if not allow_unranked and (rank == 0 or rank is None):
        return None
    if rank is None or rank == 0:
        rank = 999999  # 未上榜，排末尾显示

    air_date = subject.get("date") or subject.get("air_date")
    if not air_date:
        if not allow_unranked:
            return None
        air_date = ""

    score = rating.get("score")
    total = rating.get("total")
    if total is None:
        cnt = rating.get("count")
        total = sum(int(v) for v in (cnt or {}).values()) if isinstance(cnt, dict) else 0

    name_cn = subject.get("name_cn") or subject.get("name") or ""

    return {
        "id": subject.get("id"),
        "name": subject.get("name"),
        "name_cn": name_cn,
        "date": air_date,
        "meta_tags": "",
        "score": score,
        "score_total": total or 0,
        "rank": rank if isinstance(rank, int) else 999999,
    }
