"""Bangumi 动画榜单页面。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from config import ANIME_CLEANED_FILE, BANGUMI_APP_DATA_DIR
from ranking_ui import (
    apply_sidebar_filters,
    load_data_or_upload,
    render_insights,
    render_overview,
    render_table,
)
from ui import render_filter_chips, render_page_header, render_sidebar_brand

DATE_COLUMN = "开播日期"
DEFAULT_PATH = BANGUMI_APP_DATA_DIR / ANIME_CLEANED_FILE

render_sidebar_brand("动画筛选")
render_page_header(
    "Anime ranking",
    "动画作品探索",
    "从年代、口碑、热度与标签切入，快速收敛到你真正感兴趣的作品。",
)

original = load_data_or_upload(DEFAULT_PATH, "上传 anime_cleaned.xlsx", DATE_COLUMN)
filtered = apply_sidebar_filters(
    original,
    DATE_COLUMN,
    key_prefix="anime_",
)
render_overview(original, filtered, DATE_COLUMN)
render_filter_chips(filtered.attrs.get("active_filters", []))

ranking_tab, insight_tab = st.tabs(["榜单结果", "数据洞察"])
with ranking_tab:
    render_table(filtered, DATE_COLUMN, unit="部", download_name="bangumi_anime_filtered.csv")
with insight_tab:
    render_insights(filtered, DATE_COLUMN)
