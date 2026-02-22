"""
游戏榜单 - 基于归档导出的 xlsx 数据

使用 get_source.py 从 Bangumi 归档生成 xlsx 后，上传或放入项目根目录。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from config import BANGUMI_APP_DATA_DIR, GAME_CLEANED_FILE

st.set_page_config(
    page_title="Bangumi 游戏榜单",
    layout="wide",
    initial_sidebar_state="expanded",
)

DEFAULT_PATH = BANGUMI_APP_DATA_DIR / GAME_CLEANED_FILE

RENAME = {
    "id": "ID",
    "name": "原名",
    "name_cn": "中文名",
    "date": "发行日期",
    "score": "评分",
    "score_total": "评分人数",
    "rank": "Bangumi排名",
}


def load_from_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """清洗为展示格式。"""
    if df.empty:
        return df
    df = df.rename(columns={c: RENAME.get(c, c) for c in df.columns if c in RENAME})
    df["中文名"] = df.get("中文名", "").fillna("")
    df["发行日期"] = pd.to_datetime(df.get("发行日期"), errors="coerce")
    df = df.dropna(subset=["发行日期"])
    df["评分"] = pd.to_numeric(df.get("评分"), errors="coerce")
    df["评分人数"] = pd.to_numeric(df.get("评分人数"), errors="coerce")
    df["Bangumi排名"] = pd.to_numeric(df.get("Bangumi排名"), errors="coerce")
    id_col = "ID" if "ID" in df.columns else "id"
    df["Bangumi链接"] = "https://bgm.tv/subject/" + df[id_col].astype(str)
    return df[["中文名", "原名", "发行日期", "评分", "评分人数", "Bangumi排名", "Bangumi链接"]]


@st.cache_data
def load_from_path(file_path: str) -> pd.DataFrame:
    df = pd.read_excel(file_path, engine="openpyxl")
    return load_from_dataframe(df)


st.title("Bangumi 游戏榜单")
st.caption("数据来自归档导出的 xlsx。需先运行 get_source.py 生成，或从下方上传。")

df_original = None
if DEFAULT_PATH.exists():
    try:
        df_original = load_from_path(str(DEFAULT_PATH))
    except Exception as e:
        st.warning(f"读取本地文件失败: {e}")

if df_original is None or df_original.empty:
    uploaded = st.file_uploader(
        "上传 game_cleaned.xlsx",
        type=["xlsx", "xls"],
        help="由 get_source.py 从归档生成后导出",
    )
    if uploaded:
        try:
            df_original = load_from_dataframe(pd.read_excel(uploaded, engine="openpyxl"))
        except Exception as e:
            st.error(f"解析失败: {e}")
    else:
        st.info("请上传 xlsx 文件，或使用左侧「API 实时排行」查看在线数据。")
        st.stop()

df_filtered = df_original.copy()

st.sidebar.header("筛选与排序")
search_term = st.sidebar.text_input("按名称搜索 (中文/原名)", value="", key="g_search")
if search_term:
    s = search_term.lower()
    df_filtered = df_filtered[
        df_filtered["中文名"].str.lower().str.contains(s, na=False)
        | df_filtered["原名"].str.lower().str.contains(s, na=False)
    ]

st.sidebar.subheader("日期范围")
years = sorted(df_original["发行日期"].dt.year.dropna().astype(int).unique())
if years:
    all_years = list(range(years[0], years[-1] + 1))
    all_months = list(range(1, 13))
    c1, c2 = st.sidebar.columns(2)
    with c1:
        start_year = st.selectbox("起始年", all_years, index=0, key="gsy")
        start_month = st.selectbox("起始月", all_months, index=0, key="gsm")
    with c2:
        end_year = st.selectbox("结束年", all_years, index=len(all_years) - 1, key="gey")
        end_month = st.selectbox("结束月", all_months, index=11, key="gem")
    try:
        start_date = pd.to_datetime(f"{start_year}-{start_month}-01")
        ny, nm = (end_year + 1, 1) if end_month == 12 else (end_year, end_month + 1)
        end_date = pd.to_datetime(f"{ny}-{nm:02d}-01")
        if start_date < end_date:
            df_filtered = df_filtered[
                (df_filtered["发行日期"] >= start_date)
                & (df_filtered["发行日期"] < end_date)
            ]
        else:
            df_filtered = df_filtered[0:0]
    except ValueError:
        pass

min_s, max_s = float(df_original["评分"].min()), float(df_original["评分"].max())
score_range = st.sidebar.slider("评分范围", min_s, max_s, (min_s, max_s), step=0.1, key="g_score")
df_filtered = df_filtered[
    (df_filtered["评分"] >= score_range[0]) & (df_filtered["评分"] <= score_range[1])
]
user_min = st.sidebar.number_input(
    "最少评分人数", 0, int(df_original["评分人数"].max()), 0, key="g_min"
)
df_filtered = df_filtered[df_filtered["评分人数"] >= user_min]

sort_by = st.sidebar.selectbox(
    "排序", ("发行日期", "评分", "评分人数", "Bangumi排名"), key="g_sort"
)
asc = st.sidebar.radio("排序方向", ("降序", "升序"), index=0, key="g_asc") == "升序"
asc = asc if sort_by != "Bangumi排名" else True
df_sorted = df_filtered.sort_values(sort_by, ascending=asc)

st.subheader(f"筛选结果 ({len(df_sorted)} 个)")
if len(df_sorted) > 0:
    df_display = df_sorted.copy()
    df_display["发行日期"] = df_display["发行日期"].dt.strftime("%Y-%m-%d")
    st.dataframe(
        df_display[["Bangumi排名", "中文名", "原名", "发行日期", "评分", "评分人数", "Bangumi链接"]],
        column_config={
            "Bangumi链接": st.column_config.LinkColumn("链接", display_text="Bangumi"),
            "评分": st.column_config.NumberColumn("评分", format="%.1f"),
        },
        hide_index=True,
        use_container_width=True,
    )
else:
    st.info("无符合条件的结果。")
