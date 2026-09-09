"""Bangumi 游戏榜单页面。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from config import BANGUMI_APP_DATA_DIR, GAME_PARQUET_FILE
from ranking_ui import (
    apply_sidebar_filters,
    load_data_or_upload,
    render_insights,
    render_overview,
    render_table,
)
from ui import render_filter_chips, render_page_header, render_sidebar_brand

DATE_COLUMN = "发行日期"
DEFAULT_PATH = BANGUMI_APP_DATA_DIR / GAME_PARQUET_FILE

render_sidebar_brand("游戏筛选")
render_page_header(
    "Game ranking",
    "游戏作品探索",
    "在不同年代与类型中比较口碑和热度，发现被错过的佳作与长青经典。",
)

original = load_data_or_upload(DEFAULT_PATH, "上传游戏榜单", DATE_COLUMN)
filtered = apply_sidebar_filters(
    original,
    DATE_COLUMN,
    key_prefix="game_",
)
render_overview(original, filtered, DATE_COLUMN)
render_filter_chips(filtered.attrs.get("active_filters", []))

ranking_tab, insight_tab = st.tabs(["榜单结果", "数据洞察"])
with ranking_tab:
    render_table(filtered, DATE_COLUMN, unit="款", download_name="bangumi_game_filtered.csv")
with insight_tab:
    render_insights(filtered, DATE_COLUMN)
