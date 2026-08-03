"""动画与游戏榜单共用的数据处理和 Streamlit 界面组件。"""

from __future__ import annotations

from collections import Counter
from datetime import date
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd
import streamlit as st


REQUIRED_SOURCE_COLUMNS = {
    "id",
    "name",
    "name_cn",
    "date",
    "score",
    "score_total",
    "rank",
}

NAME_CN = "中文名"
NAME = "原名"
SCORE = "评分"
SCORE_TOTAL = "评分人数"
RANK = "Bangumi排名"
LINK = "Bangumi链接"
TAGS = "标签"

_BASE_RENAME = {
    "name": NAME,
    "name_cn": NAME_CN,
    "score": SCORE,
    "score_total": SCORE_TOTAL,
    "rank": RANK,
    "meta_tags": TAGS,
}


def _tag_tokens(value: object) -> list[str]:
    if pd.isna(value):
        return []
    return [tag.strip() for tag in str(value).split(",") if tag.strip()]


def load_from_dataframe(df: pd.DataFrame, date_display_name: str) -> pd.DataFrame:
    """校验并将归档 DataFrame 转换为榜单展示结构。"""
    missing = REQUIRED_SOURCE_COLUMNS - set(df.columns)
    if missing:
        missing_text = "、".join(sorted(missing))
        raise ValueError(f"数据缺少必要列：{missing_text}")

    data = df.copy()
    data["name_cn"] = data["name_cn"].fillna(data["name"])
    data["name_cn"] = data["name_cn"].replace(r"^\s*$", pd.NA, regex=True).fillna(data["name"])
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data["id"] = pd.to_numeric(data["id"], errors="coerce")
    data["score"] = pd.to_numeric(data["score"], errors="coerce")
    data["score_total"] = pd.to_numeric(data["score_total"], errors="coerce")
    data["rank"] = pd.to_numeric(data["rank"], errors="coerce")
    data = data.dropna(subset=["date", "score", "score_total", "rank", "id"])

    data["score_total"] = data["score_total"].clip(lower=0).astype("int64")
    data["rank"] = data["rank"].astype("int64")
    data[LINK] = data["id"].map(lambda item: f"https://bgm.tv/subject/{int(item)}")

    if "meta_tags" in data.columns:
        data["meta_tags"] = data["meta_tags"].map(lambda value: ", ".join(_tag_tokens(value)))

    rename = {**_BASE_RENAME, "date": date_display_name}
    data = data.rename(columns=rename)
    columns = [NAME_CN, NAME, date_display_name, SCORE, SCORE_TOTAL, RANK, LINK]
    if TAGS in data.columns:
        columns.append(TAGS)
    return data[columns].reset_index(drop=True)


@st.cache_data(show_spinner="正在读取榜单数据…")
def load_from_path(file_path: str, date_display_name: str) -> pd.DataFrame:
    """从 Excel 文件加载并规范化榜单数据。"""
    source = pd.read_excel(file_path, engine="openpyxl")
    return load_from_dataframe(source, date_display_name)


def available_tags(df: pd.DataFrame, limit: int = 80) -> list[str]:
    """按出现频率返回可用于快捷筛选的标签。"""
    if TAGS not in df.columns:
        return []
    counter = Counter(tag for value in df[TAGS] for tag in _tag_tokens(value))
    return [tag for tag, _ in counter.most_common(limit)]


def filter_dataframe(
    df: pd.DataFrame,
    *,
    date_column: str,
    search_term: str = "",
    start_date: date | pd.Timestamp | None = None,
    end_date: date | pd.Timestamp | None = None,
    score_range: tuple[float, float] | None = None,
    minimum_votes: int = 0,
    tags: Iterable[str] = (),
    sort_by: str = SCORE,
    ascending: bool = False,
) -> pd.DataFrame:
    """执行与 UI 无关的筛选，便于单元测试和后续 API 复用。"""
    result = df.copy()

    query = search_term.strip()
    if query:
        name_mask = result[NAME_CN].astype(str).str.contains(
            query, case=False, na=False, regex=False
        )
        original_name_mask = result[NAME].astype(str).str.contains(
            query, case=False, na=False, regex=False
        )
        result = result[name_mask | original_name_mask]

    if start_date is not None:
        result = result[result[date_column] >= pd.Timestamp(start_date)]
    if end_date is not None:
        inclusive_end = pd.Timestamp(end_date).normalize() + pd.Timedelta(days=1)
        result = result[result[date_column] < inclusive_end]

    if score_range is not None:
        result = result[result[SCORE].between(*score_range, inclusive="both")]
    result = result[result[SCORE_TOTAL] >= minimum_votes]

    selected_tags = {tag.strip() for tag in tags if tag.strip()}
    if selected_tags and TAGS in result.columns:
        result = result[
            result[TAGS].map(lambda value: selected_tags.issubset(set(_tag_tokens(value))))
        ]

    if sort_by not in result.columns:
        raise ValueError(f"无法按不存在的列排序：{sort_by}")
    return result.sort_values(sort_by, ascending=ascending, kind="stable").reset_index(drop=True)


def apply_sidebar_filters(
    df_original: pd.DataFrame,
    date_column: str,
    sort_options: Sequence[str],
    key_prefix: str = "",
) -> pd.DataFrame:
    """渲染侧边栏控件并返回筛选结果。"""
    k = key_prefix
    st.sidebar.header("筛选与排序")

    search_term = st.sidebar.text_input(
        "按名称搜索（中文 / 原名）", value="", key=f"{k}search"
    )

    minimum_date = df_original[date_column].min().date()
    maximum_date = df_original[date_column].max().date()
    selected_dates = st.sidebar.date_input(
        "日期范围",
        value=(minimum_date, maximum_date),
        min_value=minimum_date,
        max_value=maximum_date,
        key=f"{k}dates",
    )
    if isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 2:
        start_date, end_date = selected_dates
    else:
        start_date = end_date = selected_dates

    minimum_score = float(df_original[SCORE].min())
    maximum_score = float(df_original[SCORE].max())
    score_range = st.sidebar.slider(
        "评分范围",
        minimum_score,
        maximum_score,
        (minimum_score, maximum_score),
        step=0.1,
        key=f"{k}score",
    )
    minimum_votes = st.sidebar.number_input(
        "最少评分人数",
        min_value=0,
        max_value=int(df_original[SCORE_TOTAL].max()),
        value=0,
        step=100,
        key=f"{k}minimum_votes",
    )

    tag_options = available_tags(df_original)
    selected_tags = st.sidebar.multiselect(
        "标签（同时满足）",
        options=tag_options,
        placeholder="选择一个或多个热门标签",
        key=f"{k}tags",
    )

    sort_by = st.sidebar.selectbox("排序字段", sort_options, key=f"{k}sort")
    default_direction = 1 if sort_by == RANK else 0
    ascending = (
        st.sidebar.radio(
            "排序方向",
            ("降序", "升序"),
            index=default_direction,
            horizontal=True,
            key=f"{k}direction",
        )
        == "升序"
    )

    return filter_dataframe(
        df_original,
        date_column=date_column,
        search_term=search_term,
        start_date=start_date,
        end_date=end_date,
        score_range=score_range,
        minimum_votes=int(minimum_votes),
        tags=selected_tags,
        sort_by=sort_by,
        ascending=ascending,
    )


def render_overview(
    df_original: pd.DataFrame, df_filtered: pd.DataFrame, date_column: str
) -> None:
    """显示榜单核心指标。"""
    columns = st.columns(4)
    columns[0].metric("收录作品", f"{len(df_original):,}")
    columns[1].metric(
        "当前结果",
        f"{len(df_filtered):,}",
        delta=f"{len(df_filtered) - len(df_original):,}",
        delta_color="off",
    )
    columns[2].metric(
        "结果平均分",
        f"{df_filtered[SCORE].mean():.2f}" if not df_filtered.empty else "—",
    )
    columns[3].metric(
        "时间跨度",
        (
            f"{df_filtered[date_column].min().year}–{df_filtered[date_column].max().year}"
            if not df_filtered.empty
            else "—"
        ),
    )


def render_insights(df_filtered: pd.DataFrame, date_column: str) -> None:
    """展示年份分布和热门标签两个轻量分析图。"""
    if df_filtered.empty:
        return

    with st.expander("数据洞察", expanded=False):
        left, right = st.columns(2)
        yearly = (
            df_filtered.assign(年份=df_filtered[date_column].dt.year)
            .groupby("年份", as_index=False)
            .size()
            .rename(columns={"size": "作品数"})
            .tail(50)
        )
        left.caption("近 50 个有数据年份的作品数量")
        left.bar_chart(yearly, x="年份", y="作品数", width="stretch", height=300)

        tag_counter = Counter(
            tag for value in df_filtered.get(TAGS, pd.Series(dtype=str)) for tag in _tag_tokens(value)
        )
        tag_data = pd.DataFrame(tag_counter.most_common(12), columns=["标签", "作品数"])
        right.caption("当前结果中的热门标签")
        if tag_data.empty:
            right.info("当前数据没有标签信息。")
        else:
            right.bar_chart(tag_data, x="标签", y="作品数", width="stretch", height=300)


def render_table(
    df_sorted: pd.DataFrame,
    date_column: str,
    unit: str = "部",
    download_name: str = "bangumi_ranking.csv",
) -> None:
    """展示筛选结果，并提供 CSV 下载。"""
    if df_sorted.empty:
        st.info("没有符合当前条件的作品，请放宽筛选条件。")
        return

    display_columns = [RANK, NAME_CN, NAME, date_column, SCORE, SCORE_TOTAL, TAGS, LINK]
    display = df_sorted.copy()
    display[date_column] = display[date_column].dt.strftime("%Y-%m-%d")

    st.subheader(f"筛选结果（{len(display):,} {unit}）")
    st.dataframe(
        display[[column for column in display_columns if column in display.columns]],
        column_config={
            LINK: st.column_config.LinkColumn("链接", display_text="打开 Bangumi"),
            SCORE: st.column_config.NumberColumn(SCORE, format="%.1f"),
            SCORE_TOTAL: st.column_config.NumberColumn(SCORE_TOTAL, format="%d"),
        },
        hide_index=True,
        width="stretch",
        height=620,
    )
    st.download_button(
        "下载当前结果（CSV）",
        data=display.to_csv(index=False).encode("utf-8-sig"),
        file_name=download_name,
        mime="text/csv",
    )


def load_data_or_upload(
    default_path: Path,
    upload_label: str,
    date_display_name: str,
) -> pd.DataFrame:
    """优先加载默认文件，失败时允许用户上传 Excel。"""
    data = None
    if default_path.is_file():
        try:
            data = load_from_path(str(default_path), date_display_name)
        except Exception as exc:  # Streamlit 需要把可操作错误展示给用户
            st.warning(f"读取本地数据失败：{exc}")

    if data is None or data.empty:
        uploaded = st.file_uploader(
            upload_label,
            type=["xlsx"],
            help="可使用 main.py 从 Bangumi 归档生成",
        )
        if uploaded is None:
            st.info("请上传对应的 xlsx 数据文件。")
            st.stop()
        try:
            data = load_from_dataframe(
                pd.read_excel(uploaded, engine="openpyxl"), date_display_name
            )
        except Exception as exc:
            st.error(f"解析上传文件失败：{exc}")
            st.stop()

    return data
