"""Bangumi 游戏榜单页面。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from config import BANGUMI_APP_DATA_DIR, GAME_CLEANED_FILE
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
    page_title="Bangumi 游戏榜单",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATE_COLUMN = "发行日期"
DEFAULT_PATH = BANGUMI_APP_DATA_DIR / GAME_CLEANED_FILE

st.title("Bangumi 游戏榜单")
st.caption("探索游戏作品的口碑、热度、年代与标签分布。")

original = load_data_or_upload(DEFAULT_PATH, "上传 game_cleaned.xlsx", DATE_COLUMN)
filtered = apply_sidebar_filters(
    original,
    DATE_COLUMN,
    (DATE_COLUMN, SCORE, SCORE_TOTAL, RANK),
    key_prefix="game_",
)
render_overview(original, filtered, DATE_COLUMN)
render_insights(filtered, DATE_COLUMN)
render_table(filtered, DATE_COLUMN, unit="款", download_name="bangumi_game_filtered.csv")
