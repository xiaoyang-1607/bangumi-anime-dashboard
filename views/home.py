"""平台概览页。"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from config import ANIME_CLEANED_FILE, BANGUMI_APP_DATA_DIR, GAME_CLEANED_FILE
from ranking_ui import LINK, NAME_CN, RANK, SCORE, SCORE_TOTAL, load_from_path
from ui import format_archive_date, load_data_metadata, render_sidebar_brand


render_sidebar_brand("数据概览")
st.html(
    """
    <section class="bgm-hero">
      <div class="bgm-eyebrow">Bangumi data explorer</div>
      <h1>从两万部作品里，找到真正值得的下一部</h1>
      <p>把排名、评分热度、年代与标签放在同一套探索体验中。少一点翻页，多一点发现。</p>
    </section>
    """
)


def _try_load(file_name: str, date_name: str) -> pd.DataFrame | None:
    path = BANGUMI_APP_DATA_DIR / file_name
    if not path.is_file():
        return None
    try:
        return load_from_path(str(path), date_name)
    except Exception as exc:
        st.warning(f"{file_name} 加载失败：{exc}")
        return None


datasets = {
    "动画": _try_load(ANIME_CLEANED_FILE, "开播日期"),
    "游戏": _try_load(GAME_CLEANED_FILE, "发行日期"),
}
available = {name: data for name, data in datasets.items() if data is not None}
metadata = load_data_metadata()

if available:
    total_items = sum(len(data) for data in available.values())
    total_votes = sum(int(data[SCORE_TOTAL].sum()) for data in available.values())
    columns = st.columns(4)
    columns[0].metric("收录作品", f"{total_items:,}")
    columns[1].metric("动画", f"{len(available.get('动画', [])):,}")
    columns[2].metric("游戏", f"{len(available.get('游戏', [])):,}")
    columns[3].metric("数据归档", format_archive_date(metadata))

    st.space("small")
    intro, actions = st.columns([1.65, 1], vertical_alignment="center")
    with intro:
        st.subheader("开始探索")
        st.write("进入专属榜单，用快捷场景或高级条件缩小范围。筛选结果可以直接导出。")
    with actions:
        anime_button, game_button = st.columns(2)
        anime_button.page_link(
            "pages/pages1_Anime.py", label="探索动画", icon=":material/movie:", width="stretch"
        )
        game_button.page_link(
            "pages/pages2_Game.py", label="探索游戏", icon=":material/sports_esports:", width="stretch"
        )

    st.divider()
    st.subheader("口碑与热度兼具")
    st.caption(f"至少 1,000 人评分 · 累计 {total_votes:,} 次评分参与计算")
    candidates = []
    for category, data in available.items():
        qualified = data[data[SCORE_TOTAL] >= 1_000].copy()
        qualified["类型"] = category
        qualified["口碑指数"] = qualified[SCORE] * (
            1 + qualified[SCORE_TOTAL].map(lambda value: min(value, 50_000) / 50_000)
        )
        candidates.append(qualified)
    highlights = (
        pd.concat(candidates, ignore_index=True)
        .sort_values(["口碑指数", SCORE_TOTAL], ascending=False)
        .head(12)
    )
    st.dataframe(
        highlights[["类型", RANK, NAME_CN, SCORE, SCORE_TOTAL, LINK]],
        column_config={
            LINK: st.column_config.LinkColumn("详情", display_text="打开 ↗"),
            SCORE: st.column_config.NumberColumn(SCORE, format="%.1f"),
            SCORE_TOTAL: st.column_config.NumberColumn(SCORE_TOTAL, format="%d"),
        },
        hide_index=True,
        width="stretch",
    )
else:
    st.info("尚未找到榜单数据。请运行 `python update_data.py`，或进入榜单页面上传 xlsx。")

with st.sidebar.expander("关于数据", expanded=False):
    st.caption(
        f"归档：{metadata.get('archive_name', '未知')}\n\n"
        "数据来自 Bangumi Archive；本站为非官方数据探索工具。"
    )
