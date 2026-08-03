"""Bangumi 动画榜单页面。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from config import ANIME_CLEANED_FILE, BANGUMI_APP_DATA_DIR
from ranking_ui import (
    RANK,
    SCORE,
    SCORE_TOTAL,
    apply_sidebar_filters,
    load_data_or_upload,
    render_insights,
    render_overview,
    render_table,
)

st.set_page_config(
    page_title="Bangumi 动画榜单",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATE_COLUMN = "开播日期"
DEFAULT_PATH = BANGUMI_APP_DATA_DIR / ANIME_CLEANED_FILE

st.title("Bangumi 动画榜单")
st.caption("探索动画作品的口碑、热度、年代与标签分布。")

original = load_data_or_upload(DEFAULT_PATH, "上传 anime_cleaned.xlsx", DATE_COLUMN)
filtered = apply_sidebar_filters(
    original,
    DATE_COLUMN,
    (DATE_COLUMN, SCORE, SCORE_TOTAL, RANK),
    key_prefix="anime_",
)
render_overview(original, filtered, DATE_COLUMN)
render_insights(filtered, DATE_COLUMN)
render_table(filtered, DATE_COLUMN, unit="部", download_name="bangumi_anime_filtered.csv")
