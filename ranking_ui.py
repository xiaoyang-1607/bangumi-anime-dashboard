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
USER_TAGS = "用户标签"
NSFW = "NSFW"
RELEASE_STATUS = "发行状态"
FAVORITE = "收藏人数"
BAYESIAN_SCORE = "综合评分"
SCORE_CONFIDENCE = "评分样本量"
RANK_CHANGE = "名次变动"
RANK_CHANGE_STATUS = "名次状态"
PREVIOUS_RANK = "上期排名"

_BASE_RENAME = {
    "name": NAME,
    "name_cn": NAME_CN,
    "score": SCORE,
    "score_total": SCORE_TOTAL,
    "rank": RANK,
    "meta_tags": TAGS,
    "user_tags": USER_TAGS,
    "nsfw": NSFW,
    "release_status": RELEASE_STATUS,
    "favorite": FAVORITE,
    "bayesian_score": BAYESIAN_SCORE,
    "score_confidence": SCORE_CONFIDENCE,
    "rank_change": RANK_CHANGE,
    "rank_change_status": RANK_CHANGE_STATUS,
    "previous_rank": PREVIOUS_RANK,
}


def _tag_tokens(value: object) -> list[str]:
    if pd.isna(value):
        return []
    return [tag.strip() for tag in str(value).split(",") if tag.strip()]


def _format_count(value: object) -> str:
    """格式化人数；兼容 Streamlit 测试框架回传的已格式化字符串。"""
    return f"{int(str(value).replace(',', '')):,}"


def _coerce_boolean(value: object) -> bool:
    """兼容 Excel 中的布尔值、0/1 和常见文本写法。"""
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().casefold() in {"true", "1", "yes", "y"}


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
    data = data.dropna(subset=["score", "score_total", "rank", "id"])

    data["score_total"] = data["score_total"].clip(lower=0).astype("int64")
    data["rank"] = data["rank"].astype("int64")
    if "favorite" in data.columns:
        data["favorite"] = pd.to_numeric(data["favorite"], errors="coerce").fillna(0).astype("int64")
    if "bayesian_score" in data.columns:
        data["bayesian_score"] = pd.to_numeric(data["bayesian_score"], errors="coerce")
    for column in ("rank_change", "previous_rank"):
        if column in data.columns:
            data[column] = pd.to_numeric(data[column], errors="coerce")
    if "nsfw" in data.columns:
        data["nsfw"] = data["nsfw"].map(_coerce_boolean)
    if "release_status" in data.columns:
        data["release_status"] = data["release_status"].map(
            {"released": "已发行", "upcoming": "即将发行", "unknown_date": "日期未知"}
        ).fillna("日期未知")
    if "score_confidence" in data.columns:
        data["score_confidence"] = data["score_confidence"].map(
            {"high": "高", "medium": "中", "low": "低"}
        ).fillna("低")
    data[LINK] = data["id"].map(lambda item: f"https://bgm.tv/subject/{int(item)}")

    if "meta_tags" in data.columns:
        data["meta_tags"] = data["meta_tags"].map(lambda value: ", ".join(_tag_tokens(value)))

    rename = {**_BASE_RENAME, "date": date_display_name}
    data = data.rename(columns=rename)
    columns = [NAME_CN, NAME, date_display_name, SCORE, SCORE_TOTAL, RANK, LINK]
    for optional_column in (
        RANK_CHANGE, RANK_CHANGE_STATUS, PREVIOUS_RANK,
        BAYESIAN_SCORE, SCORE_CONFIDENCE, FAVORITE, RELEASE_STATUS,
        NSFW, TAGS, USER_TAGS,
    ):
        if optional_column in data.columns:
            columns.append(optional_column)
    return data[columns].reset_index(drop=True)


def _read_tabular(source) -> pd.DataFrame:
    name = getattr(source, "name", source)
    suffix = Path(str(name)).suffix.casefold()
    if suffix == ".parquet":
        return pd.read_parquet(source, engine="pyarrow")
    if suffix == ".xlsx":
        return pd.read_excel(source, engine="openpyxl")
    raise ValueError("仅支持 .parquet 或 .xlsx 数据文件")


@st.cache_data(show_spinner="正在读取榜单数据…")
def load_from_path(file_path: str, date_display_name: str) -> pd.DataFrame:
    """从 Parquet 或 Excel 文件加载并规范化榜单数据。"""
    source = _read_tabular(file_path)
    return load_from_dataframe(source, date_display_name)


def month_range_bounds(start_month: str, end_month: str) -> tuple[date, date]:
    """把包含首尾的 YYYY-MM 月份范围转换为日级过滤边界。"""
    try:
        start_period = pd.Period(start_month, freq="M")
        end_period = pd.Period(end_month, freq="M")
    except ValueError as exc:
        raise ValueError("月份必须使用 YYYY-MM 格式") from exc
    if start_period > end_period:
        raise ValueError("起始月份不能晚于结束月份")
    return start_period.start_time.date(), end_period.end_time.date()


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
    include_unknown_dates: bool = False,
    nsfw_mode: str = "all",
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

    date_mask = result[date_column].notna()
    if start_date is not None:
        date_mask &= result[date_column] >= pd.Timestamp(start_date)
    if end_date is not None:
        inclusive_end = pd.Timestamp(end_date).normalize() + pd.Timedelta(days=1)
        date_mask &= result[date_column] < inclusive_end
    if include_unknown_dates:
        date_mask |= result[date_column].isna()
    result = result[date_mask]

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

    if NSFW in result.columns:
        if nsfw_mode == "hide":
            result = result[~result[NSFW]]
        elif nsfw_mode == "only":
            result = result[result[NSFW]]
        elif nsfw_mode != "all":
            raise ValueError("nsfw_mode 只支持 hide、all 或 only")

    if sort_by not in result.columns:
        raise ValueError(f"无法按不存在的列排序：{sort_by}")
    return result.sort_values(
        sort_by, ascending=ascending, kind="stable", na_position="last"
    ).reset_index(drop=True)


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
        latest_date = df[date_column].max()
        if pd.isna(latest_date):
            return df.iloc[0:0], ["近三年"]
        latest_month = latest_date.to_period("M")
        cutoff = (latest_month - 35).start_time
        return df[df[date_column] >= cutoff], [f"{cutoff:%Y-%m} 至今"]
    raise ValueError(f"未知快捷筛选：{preset}")


_FILTER_WIDGETS = (
    "preset", "search", "start_month", "end_month", "score", "minimum_votes", "tags",
    "tag_match", "sort", "include_unknown_dates", "nsfw_mode",
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
    valid_dates = df_original[date_column].dropna()
    if valid_dates.empty:
        current_month = pd.Period(date.today(), freq="M")
        minimum_month = maximum_month = str(current_month)
    else:
        minimum_period = valid_dates.min().to_period("M")
        maximum_period = valid_dates.max().to_period("M")
        minimum_month = str(minimum_period)
        maximum_month = str(maximum_period)
    month_options = pd.period_range(
        minimum_month, maximum_month, freq="M"
    ).strftime("%Y-%m").tolist()
    minimum_score = float(df_original[SCORE].min())
    maximum_score = float(df_original[SCORE].max())

    with st.sidebar.form(f"{k}filter_form", border=False):
        search_term = st.text_input(
            "搜索作品", value="", placeholder="输入中文名或原名", key=f"{k}search",
            icon=":material/search:",
        )
        with st.expander("时间与评分", expanded=True, icon=":material/tune:"):
            month_columns = st.columns(2)
            selected_start_month = month_columns[0].selectbox(
                "起始月份", month_options, index=0, key=f"{k}start_month"
            )
            selected_end_month = month_columns[1].selectbox(
                "结束月份",
                month_options,
                index=len(month_options) - 1,
                key=f"{k}end_month",
            )
            include_unknown_dates = st.checkbox(
                "包含日期未知作品", value=False, key=f"{k}include_unknown_dates"
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

        if NSFW in df_original.columns:
            with st.expander("内容分级", expanded=False, icon=":material/shield:"):
                nsfw_label = st.radio(
                    "NSFW 内容", ("隐藏", "显示全部", "仅 NSFW"),
                    key=f"{k}nsfw_mode",
                )
        else:
            nsfw_label = "显示全部"

        with st.expander("排序", expanded=False, icon=":material/swap_vert:"):
            sort_choices = {
                f"{date_column} · 新作优先": (date_column, False),
                "评分 · 高分优先": (SCORE, False),
                "评分人数 · 热门优先": (SCORE_TOTAL, False),
                "Bangumi 排名 · 前列优先": (RANK, True),
                f"{date_column} · 经典优先": (date_column, True),
            }
            if BAYESIAN_SCORE in df_original.columns:
                sort_choices = {
                    "经验贝叶斯分 · 高分优先": (BAYESIAN_SCORE, False),
                    **sort_choices,
                }
            if RANK_CHANGE in df_original.columns and df_original[RANK_CHANGE].notna().any():
                sort_choices["名次上升 · 最多优先"] = (RANK_CHANGE, False)
            if FAVORITE in df_original.columns:
                sort_choices["收藏人数 · 人气优先"] = (FAVORITE, False)
            sort_label = st.selectbox(
                "排序方式", tuple(sort_choices), key=f"{k}sort",
            )
        st.form_submit_button(
            "应用高级筛选", type="primary", icon=":material/check:", width="stretch"
        )

    invalid_month_range = False
    try:
        start_date, end_date = month_range_bounds(
            selected_start_month, selected_end_month
        )
    except ValueError as exc:
        invalid_month_range = True
        st.sidebar.error(str(exc), icon=":material/calendar_month:")
        start_date = pd.Period(selected_start_month, freq="M").start_time.date()
        end_date = pd.Period(selected_end_month, freq="M").end_time.date()
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
        include_unknown_dates=include_unknown_dates,
        nsfw_mode={"隐藏": "hide", "显示全部": "all", "仅 NSFW": "only"}[nsfw_label],
        sort_by=sort_by,
        ascending=ascending,
    )
    result, preset_labels = apply_quick_preset(result, preset or "全部作品", date_column)
    if invalid_month_range:
        result = result.iloc[0:0]
    result = result.sort_values(
        sort_by, ascending=ascending, kind="stable", na_position="last"
    ).reset_index(drop=True)

    labels = list(preset_labels)
    if search_term.strip():
        labels.append(f"名称：{search_term.strip()}")
    if selected_start_month != minimum_month or selected_end_month != maximum_month:
        labels.append(f"{selected_start_month} 至 {selected_end_month}")
    if score_range != (minimum_score, maximum_score):
        labels.append(f"评分 {score_range[0]:.1f}–{score_range[1]:.1f}")
    if minimum_votes:
        labels.append(f"至少 {minimum_votes:,} 人评分")
    if include_unknown_dates:
        labels.append("包含日期未知")
    if nsfw_label != "显示全部":
        labels.append(f"NSFW：{nsfw_label}")
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
            f"{df_filtered[date_column].dropna().min().year}–"
            f"{df_filtered[date_column].dropna().max().year}"
            if not df_filtered[date_column].dropna().empty
            else "—"
        ),
    )
    if RANK_CHANGE_STATUS in df_original.columns:
        comparable = df_original[RANK_CHANGE_STATUS].isin(["up", "down", "same"])
        if comparable.any():
            up = int((df_filtered[RANK_CHANGE_STATUS] == "up").sum())
            down = int((df_filtered[RANK_CHANGE_STATUS] == "down").sum())
            st.caption(f"当前结果中：↑ {up:,} 条上升 · ↓ {down:,} 条下降 · 名次变动以 Bangumi 原始排名为准")


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


def format_rank_change(value: object, status: object) -> str:
    """排名数字越小越靠前，因此正差值代表上升。"""
    if status == "new":
        return "本期新增"
    if status == "baseline":
        return "暂无对比"
    if status == "same":
        return "— 0"
    if pd.isna(value):
        return "暂无对比"
    change = int(value)
    return f"↑ +{change:,}" if change > 0 else f"↓ {change:,}"


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

    compact_columns = [
        RANK, RANK_CHANGE, NAME_CN, date_column, SCORE, BAYESIAN_SCORE,
        SCORE_TOTAL, LINK,
    ]
    detail_columns = [
        RANK, RANK_CHANGE, PREVIOUS_RANK, NAME_CN, NAME, date_column,
        RELEASE_STATUS, SCORE, BAYESIAN_SCORE, SCORE_CONFIDENCE,
        SCORE_TOTAL, FAVORITE, TAGS, USER_TAGS, LINK,
    ]
    display = df_sorted.copy()
    display[date_column] = display[date_column].dt.strftime("%Y-%m-%d").fillna("未知")
    table_display = display.copy()
    if RANK_CHANGE in display.columns and RANK_CHANGE_STATUS in display.columns:
        table_display[RANK_CHANGE] = [
            format_rank_change(change, status)
            for change, status in zip(display[RANK_CHANGE], display[RANK_CHANGE_STATUS])
        ]

    st.subheader(f"筛选结果（{len(display):,} {unit}）")
    controls = st.columns([2, 1], vertical_alignment="bottom")
    with controls[0]:
        table_mode = st.radio(
            "显示字段", ("精简榜单", "完整数据"), horizontal=True,
            key=f"{download_name}_table_mode",
        )
    with controls[1]:
        st.caption("↑ 名次上升 · ↓ 名次下降 · 修正分不额外奖励热度")
    visible_columns = compact_columns if table_mode != "完整数据" else detail_columns
    st.dataframe(
        table_display[[column for column in visible_columns if column in table_display.columns]],
        column_config={
            LINK: st.column_config.LinkColumn("链接", display_text="打开 Bangumi"),
            SCORE: st.column_config.NumberColumn(SCORE, format="%.1f"),
            BAYESIAN_SCORE: st.column_config.NumberColumn("经验贝叶斯分", format="%.2f"),
            SCORE_TOTAL: st.column_config.NumberColumn(SCORE_TOTAL, format="%d"),
            FAVORITE: st.column_config.NumberColumn(FAVORITE, format="%d"),
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
    """优先加载默认 Parquet，兼容本地或上传的 Excel。"""
    data = None
    local_path = default_path
    if not local_path.is_file() and local_path.suffix.casefold() == ".parquet":
        excel_fallback = local_path.with_suffix(".xlsx")
        if excel_fallback.is_file():
            local_path = excel_fallback
    if local_path.is_file():
        try:
            data = load_from_path(str(local_path), date_display_name)
        except Exception as exc:  # Streamlit 需要把可操作错误展示给用户
            st.warning(f"读取本地数据失败：{exc}")

    if data is None or data.empty:
        uploaded = st.file_uploader(
            upload_label,
            type=["parquet", "xlsx"],
            help="可使用 main.py 从 Bangumi 归档生成",
        )
        if uploaded is None:
            st.info("请上传对应的 Parquet 或 XLSX 数据文件。")
            st.stop()
        try:
            data = load_from_dataframe(_read_tabular(uploaded), date_display_name)
        except Exception as exc:
            st.error(f"解析上传文件失败：{exc}")
            st.stop()

    return data
