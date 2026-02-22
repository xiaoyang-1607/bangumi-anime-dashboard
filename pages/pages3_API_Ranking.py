"""
Bangumi API 实时排行 - 类似主站排行榜的在线展示

从 Bangumi API 实时拉取数据，无需 xlsx 文件。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from bangumi_api import TYPE_ANIME, TYPE_GAME, get_subjects, subject_to_row

st.set_page_config(
    page_title="Bangumi API 实时排行",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Bangumi API 实时排行")
st.caption("数据来自 Bangumi API，与主站排行榜同步，无需上传文件。")


@st.cache_data(ttl=3600)
def fetch_ranking(subject_type: int, limit: int = 100) -> list[dict]:
    """从 API 获取排行数据，缓存 1 小时。"""
    rows = []
    offset = 0
    while len(rows) < limit:
        try:
            data = get_subjects(
                subject_type=subject_type,
                sort="rank",
                limit=min(50, limit - len(rows)),
                offset=offset,
            )
        except Exception as e:
            st.error(f"API 请求失败: {e}")
            return rows
        items = data.get("data", [])
        for s in items:
            row = subject_to_row(s)
            if row:
                rows.append(row)
                if len(rows) >= limit:
                    break
        if not items or len(items) < 50:
            break
        offset += 50
    return rows


limit = st.sidebar.slider("显示条数", min_value=20, max_value=200, value=100)

tab_anime, tab_game = st.tabs(["动画排行", "游戏排行"])

with tab_anime:
    with st.spinner("正在从 Bangumi API 获取动画排行..."):
        anime_rows = fetch_ranking(TYPE_ANIME, limit)
    if anime_rows:
        df = pd.DataFrame(anime_rows)
        df = df.rename(
            columns={
                "name_cn": "中文名",
                "name": "原名",
                "date": "日期",
                "score": "评分",
                "score_total": "评分人数",
                "rank": "排名",
            }
        )
        df["链接"] = "https://bgm.tv/subject/" + df["id"].astype(str)
        st.dataframe(
            df[["排名", "中文名", "原名", "日期", "评分", "评分人数", "链接"]],
            column_config={
                "链接": st.column_config.LinkColumn("Bangumi", display_text="链接"),
                "评分": st.column_config.NumberColumn("评分", format="%.1f"),
            },
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("暂无法获取数据，请检查网络或稍后重试。")

with tab_game:
    with st.spinner("正在从 Bangumi API 获取游戏排行..."):
        game_rows = fetch_ranking(TYPE_GAME, limit)
    if game_rows:
        df = pd.DataFrame(game_rows)
        df = df.rename(
            columns={
                "name_cn": "中文名",
                "name": "原名",
                "date": "发行日期",
                "score": "评分",
                "score_total": "评分人数",
                "rank": "排名",
            }
        )
        df["链接"] = "https://bgm.tv/subject/" + df["id"].astype(str)
        st.dataframe(
            df[["排名", "中文名", "原名", "发行日期", "评分", "评分人数", "链接"]],
            column_config={
                "链接": st.column_config.LinkColumn("Bangumi", display_text="链接"),
                "评分": st.column_config.NumberColumn("评分", format="%.1f"),
            },
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("暂无法获取数据，请检查网络或稍后重试。")
