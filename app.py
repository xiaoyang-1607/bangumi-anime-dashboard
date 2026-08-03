"""Bangumi 综合数据分析平台首页。"""

from __future__ import annotations

import json
import pandas as pd
import streamlit as st

from config import (
    ANIME_CLEANED_FILE,
    BANGUMI_APP_DATA_DIR,
    DATA_METADATA_FILE,
    GAME_CLEANED_FILE,
)
from ranking_ui import LINK, NAME_CN, RANK, SCORE, SCORE_TOTAL, load_from_path


st.set_page_config(
    page_title="Bangumi 综合数据分析平台",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Bangumi 综合数据分析平台")
st.caption("从 Bangumi 归档中发现高口碑动画与游戏，并用统一条件快速比较。")

metadata_path = BANGUMI_APP_DATA_DIR / DATA_METADATA_FILE
if metadata_path.is_file():
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        archive_name = metadata.get("archive_name")
        if archive_name:
            st.caption(f"当前数据源：`{archive_name}`")
    except (OSError, json.JSONDecodeError):
        pass


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

if available:
    total_items = sum(len(data) for data in available.values())
    total_votes = sum(int(data[SCORE_TOTAL].sum()) for data in available.values())
    columns = st.columns(4)
    columns[0].metric("收录作品", f"{total_items:,}")
    columns[1].metric("动画", f"{len(available.get('动画', [])):,}")
    columns[2].metric("游戏", f"{len(available.get('游戏', [])):,}")
    columns[3].metric("累计评分人次", f"{total_votes:,}")

    st.subheader("高口碑作品速览")
    st.caption("至少 1,000 人评分，按评分与评分人数综合排序。")
    candidates = []
    for category, data in available.items():
        qualified = data[data[SCORE_TOTAL] >= 1_000].copy()
        qualified["类型"] = category
        qualified["口碑指数"] = qualified[SCORE] * (
            1 + qualified[SCORE_TOTAL].map(lambda value: min(value, 50_000) / 50_000)
        )
        candidates.append(qualified)
    if candidates:
        highlights = (
            pd.concat(candidates, ignore_index=True)
            .sort_values(["口碑指数", SCORE_TOTAL], ascending=False)
            .head(12)
        )
        st.dataframe(
            highlights[["类型", RANK, NAME_CN, SCORE, SCORE_TOTAL, LINK]],
            column_config={
                LINK: st.column_config.LinkColumn("链接", display_text="打开 Bangumi"),
                SCORE: st.column_config.NumberColumn(SCORE, format="%.1f"),
                SCORE_TOTAL: st.column_config.NumberColumn(SCORE_TOTAL, format="%d"),
            },
            hide_index=True,
            width="stretch",
        )

    st.subheader("开始探索")
    st.markdown(
        "请从左侧导航进入 **Anime（动画榜单）** 或 **Game（游戏榜单）**。"
        "每个榜单都支持日期、评分人数、标签和名称筛选，并可下载当前结果。"
    )
else:
    st.info("尚未找到榜单数据。请运行 `python main.py`，或进入榜单页面上传 xlsx 文件。")

with st.expander("数据说明"):
    st.markdown(
        "数据来自 Bangumi Archive 的 `subject.jsonlines`。评分与排名会随归档更新；"
        "本站只做数据整理和可视化，作品详情以 Bangumi 页面为准。"
    )
