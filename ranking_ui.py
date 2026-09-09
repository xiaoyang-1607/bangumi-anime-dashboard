"""动画与游戏榜单共用的数据处理和 Streamlit 界面组件。"""

from __future__ import annotations

from collections import Counter
from datetime import date
from pathlib import Path
from typing import Iterable

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


def _format_count(value: object) -> str:
    """格式化人数；兼容 Streamlit 测试框架回传的已格式化字符串。"""
    return f"{int(str(value).replace(',', '')):,}"


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
    maximum_votes: int | None = None,
    tags: Iterable[str] = (),
    tag_match: str = "all",
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
    if maximum_votes is not None:
        result = result[result[SCORE_TOTAL] <= maximum_votes]

    selected_tags = {tag.strip() for tag in tags if tag.strip()}
    if selected_tags and TAGS in result.columns:
        if tag_match not in {"all", "any"}:
            raise ValueError("tag_match 只支持 all 或 any")
        result = result[result[TAGS].map(
            lambda value: (
                selected_tags.issubset(set(_tag_tokens(value)))
                if tag_match == "all"
                else bool(selected_tags.intersection(_tag_tokens(value)))
            )
        )]

    if sort_by not in result.columns:
        raise ValueError(f"无法按不存在的列排序：{sort_by}")
    return result.sort_values(sort_by, ascending=ascending, kind="stable").reset_index(drop=True)


def apply_quick_preset(
    df: pd.DataFrame, preset: str, date_column: str
) -> tuple[pd.DataFrame, list[str]]:
    """应用常用发现情景，返回结果和面向用户的条件说明。"""
    if preset == "全部作品":
        return df, []
    if preset == "高分佳作":
        return df[(df[SCORE] >= 8.0) & (df[SCORE_TOTAL] >= 1_000)], ["评分 ≥ 8.0", "评分人数 ≥ 1,000"]
    if preset == "大众热门":
        return df[df[SCORE_TOTAL] >= 10_000], ["评分人数 ≥ 10,000"]
    if preset == "冷门佳作":
        return df[(df[SCORE] >= 8.0) & df[SCORE_TOTAL].between(100, 2_000)], ["评分 ≥ 8.0", "100–2,000 人评分"]
    if preset == "近三年":
        cutoff = df[date_column].max() - pd.DateOffset(years=3)
        return df[df[date_column] >= cutoff], [f"{cutoff.year} 年至今"]
    raise ValueError(f"未知快捷筛选：{preset}")


_FILTER_WIDGETS = (
    "preset", "search", "dates", "score", "minimum_votes", "tags",
    "tag_match", "sort",
)


def _reset_filter_widgets(prefix: str) -> None:
    for suffix in _FILTER_WIDGETS:
        st.session_state.pop(f"{prefix}{suffix}", None)


def apply_sidebar_filters(
    df_original: pd.DataFrame,
    date_column: str,
    key_prefix: str = "",
) -> pd.DataFrame:
    """渲染分组筛选器并返回结果；活跃条件写入 DataFrame.attrs。"""
    k = key_prefix
    st.sidebar.subheader("发现方式")
    preset_options = {
        "全部作品": "全部作品",
        "高分佳作": "✨ 高分佳作",
        "大众热门": "🔥 大众热门",
        "冷门佳作": "💎 冷门佳作",
        "近三年": "🆕 近三年",
    }
    preset = st.sidebar.selectbox(
        "快捷筛选",
        tuple(preset_options),
        format_func=preset_options.get,
        key=f"{k}preset",
        width="stretch",
    )
    minimum_date = df_original[date_column].min().date()
    maximum_date = df_original[date_column].max().date()
    minimum_score = float(df_original[SCORE].min())
    maximum_score = float(df_original[SCORE].max())

    with st.sidebar.form(f"{k}filter_form", border=False):
        search_term = st.text_input(
            "搜索作品", value="", placeholder="输入中文名或原名", key=f"{k}search",
            icon=":material/search:",
        )
        with st.expander("时间与评分", expanded=True, icon=":material/tune:"):
            selected_dates = st.date_input(
                "日期范围", value=(minimum_date, maximum_date),
                min_value=minimum_date, max_value=maximum_date, key=f"{k}dates",
            )
            score_range = st.slider(
                "评分范围", minimum_score, maximum_score,
                (minimum_score, maximum_score), step=0.1, key=f"{k}score",
            )
            vote_options = sorted(set(
                [0, 100, 500, 1_000, 3_000, 5_000, 10_000]
                + [int(df_original[SCORE_TOTAL].max())]
            ))
            minimum_votes = st.select_slider(
                "最低评分人数", options=vote_options, value=0,
                format_func=_format_count, key=f"{k}minimum_votes",
            )

        with st.expander("标签", expanded=False, icon=":material/label:"):
            selected_tags = st.multiselect(
                "作品标签", options=available_tags(df_original),
                placeholder="选择热门标签", key=f"{k}tags",
            )
            tag_match_label = st.radio(
                "多个标签", ("同时满足", "满足任一"), horizontal=True,
                key=f"{k}tag_match",
            )

        with st.expander("排序", expanded=False, icon=":material/swap_vert:"):
            sort_choices = {
                f"{date_column} · 新作优先": (date_column, False),
                "评分 · 高分优先": (SCORE, False),
                "评分人数 · 热门优先": (SCORE_TOTAL, False),
                "Bangumi 排名 · 前列优先": (RANK, True),
                f"{date_column} · 经典优先": (date_column, True),
            }
            sort_label = st.selectbox(
                "排序方式", tuple(sort_choices), key=f"{k}sort",
            )
        st.form_submit_button(
            "应用高级筛选", type="primary", icon=":material/check:", width="stretch"
        )

    if isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 2:
        start_date, end_date = selected_dates
    else:
        start_date = end_date = selected_dates
    sort_by, ascending = sort_choices[sort_label]
    result = filter_dataframe(
        df_original,
        date_column=date_column,
        search_term=search_term,
        start_date=start_date,
        end_date=end_date,
        score_range=score_range,
        minimum_votes=int(minimum_votes),
        tags=selected_tags,
        tag_match="all" if tag_match_label == "同时满足" else "any",
        sort_by=sort_by,
        ascending=ascending,
    )
    result, preset_labels = apply_quick_preset(result, preset or "全部作品", date_column)
    result = result.sort_values(sort_by, ascending=ascending, kind="stable").reset_index(drop=True)

    labels = list(preset_labels)
    if search_term.strip():
        labels.append(f"名称：{search_term.strip()}")
    if start_date != minimum_date or end_date != maximum_date:
        labels.append(f"{start_date:%Y-%m-%d} 至 {end_date:%Y-%m-%d}")
    if score_range != (minimum_score, maximum_score):
        labels.append(f"评分 {score_range[0]:.1f}–{score_range[1]:.1f}")
    if minimum_votes:
        labels.append(f"至少 {minimum_votes:,} 人评分")
    if selected_tags:
        joiner = " 且 " if tag_match_label == "同时满足" else " 或 "
        labels.append("标签：" + joiner.join(selected_tags))
    result.attrs["active_filters"] = labels

    st.sidebar.success(f"找到 {len(result):,} / {len(df_original):,} 条", icon=":material/filter_alt:")
    st.sidebar.button(
        "重置全部条件", icon=":material/restart_alt:", width="stretch",
        on_click=_reset_filter_widgets, args=(k,),
    )
    return result


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
        st.info("暂无可分析的数据，请调整筛选条件。")
        return

    left, right = st.columns(2)
    yearly = (
        df_filtered.assign(年份=df_filtered[date_column].dt.year)
        .groupby("年份", as_index=False)
        .size()
        .rename(columns={"size": "作品数"})
        .tail(50)
    )
    left.subheader("年代分布")
    left.caption("最近 50 个有数据年份的作品数量")
    left.bar_chart(yearly, x="年份", y="作品数", width="stretch", height=340)

    tag_counter = Counter(
        tag for value in df_filtered.get(TAGS, pd.Series(dtype=str)) for tag in _tag_tokens(value)
    )
    tag_data = pd.DataFrame(tag_counter.most_common(12), columns=["标签", "作品数"])
    right.subheader("标签热度")
    right.caption("当前结果中出现最多的 12 个标签")
    if tag_data.empty:
        right.info("当前数据没有标签信息。")
    else:
        right.bar_chart(tag_data, x="标签", y="作品数", width="stretch", height=340)


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
