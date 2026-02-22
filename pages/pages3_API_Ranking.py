"""
Bangumi API 实时排行 - 先筛选后获取

从 Bangumi API 拉取数据，支持筛选条件在请求前传入。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from bangumi_api import (
    TYPE_ANIME,
    TYPE_GAME,
    fetch_ranking_with_filters,
)

st.set_page_config(
    page_title="Bangumi API 实时排行",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Bangumi API 实时排行")
st.caption("数据来自 Bangumi API，筛选条件在请求前生效，减少数据量。")

# 侧边栏：筛选条件（先筛选后获取）
st.sidebar.header("筛选条件")
limit = st.sidebar.slider("显示条数", 20, 200, 100)

use_filters = st.sidebar.checkbox("启用筛选", value=False, help="启用后使用搜索 API，按条件过滤")

air_date_filters = None
rating_min = rating_max = None
rating_count_min = None
meta_tags_list = None

if use_filters:
    st.sidebar.subheader("日期范围")
    year_from = st.sidebar.number_input("起始年", 1970, 2030, 2000, key="yf")
    year_to = st.sidebar.number_input("结束年", 1970, 2030, 2025, key="yt")
    if year_from <= year_to:
        air_date_filters = [f">={year_from}-01-01", f"<={year_to}-12-31"]

    st.sidebar.subheader("评分")
    use_rating = st.sidebar.checkbox("限制评分范围", False, key="ur")
    if use_rating:
        r1, r2 = st.sidebar.slider("评分范围", 0.0, 10.0, (6.0, 9.0), 0.1, key="rng")
        rating_min, rating_max = r1, r2

    use_rc = st.sidebar.checkbox("限制最少评分人数", False, key="urc")
    if use_rc:
        rating_count_min = st.sidebar.number_input("最少评分人数", 0, 100000, 100, 100, key="rcmin")

    st.sidebar.subheader("标签 (meta_tags)")
    tag_input = st.sidebar.text_input(
        "标签筛选，多个用逗号分隔",
        placeholder="如: 科幻, 原创",
        key="mt",
    )
    if tag_input:
        meta_tags_list = [t.strip() for t in tag_input.split(",") if t.strip()]


@st.cache_data(ttl=1800)
def _cached_fetch(subject_type: int, limit: int, air_date_tuple, rating_min, rating_max, rating_count_min, meta_tags_tuple):
    air_date = list(air_date_tuple) if air_date_tuple else None
    meta_tags = list(meta_tags_tuple) if meta_tags_tuple else None
    return fetch_ranking_with_filters(
        subject_type=subject_type,
        limit=limit,
        air_date=air_date,
        rating_min=rating_min,
        rating_max=rating_max,
        rating_count_min=rating_count_min,
        meta_tags=meta_tags,
    )


def _fetch_and_display(subject_type: int, date_col: str):
    ad = tuple(air_date_filters) if air_date_filters else ()
    mt = tuple(meta_tags_list) if meta_tags_list else ()
    try:
        rows = _cached_fetch(
            subject_type,
            limit,
            ad,
            rating_min,
            rating_max,
            rating_count_min,
            mt,
        )
    except Exception as e:
        st.error(f"API 请求失败: {e}")
        return

    if rows:
        df = pd.DataFrame(rows)
        df = df.sort_values("rank")
        df = df.rename(
            columns={
                "name_cn": "中文名",
                "name": "原名",
                "date": date_col,
                "score": "评分",
                "score_total": "评分人数",
                "rank": "排名",
            }
        )
        df["链接"] = "https://bgm.tv/subject/" + df["id"].astype(str)
        df["排名"] = df["排名"].apply(lambda x: "未上榜" if isinstance(x, (int, float)) and x >= 999999 else x)
        st.dataframe(
            df[["排名", "中文名", "原名", date_col, "评分", "评分人数", "链接"]],
            column_config={
                "链接": st.column_config.LinkColumn("Bangumi", display_text="链接"),
                "评分": st.column_config.NumberColumn("评分", format="%.1f"),
            },
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("暂无符合条件的数据。")

tab_anime, tab_game = st.tabs(["动画排行", "游戏排行"])

with tab_anime:
    with st.spinner("正在获取动画排行..."):
        _fetch_and_display(TYPE_ANIME, "日期")

with tab_game:
    with st.spinner("正在获取游戏排行..."):
        _fetch_and_display(TYPE_GAME, "发行日期")
