"""
游戏榜单 - 基于归档导出的 xlsx 数据

使用 main.py 从 Bangumi 归档生成 xlsx 后，上传或放入项目根目录。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from config import BANGUMI_APP_DATA_DIR, GAME_CLEANED_FILE
from ranking_ui import (
    apply_sidebar_filters,
    load_data_or_upload,
    render_table,
)

st.set_page_config(
    page_title="Bangumi 游戏榜单",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATE_COL = "发行日期"
DEFAULT_PATH = BANGUMI_APP_DATA_DIR / GAME_CLEANED_FILE

st.title("Bangumi 游戏榜单")
st.caption("数据来自归档导出的 xlsx。需先运行 main.py 生成，或从下方上传。")

df_original = load_data_or_upload(
    DEFAULT_PATH,
    "上传 game_cleaned.xlsx",
    DATE_COL,
)
df_sorted = apply_sidebar_filters(
    df_original,
    DATE_COL,
    ("发行日期", "评分", "评分人数", "Bangumi排名"),
    key_prefix="g_",
)
render_table(df_sorted, DATE_COL, unit="个")
