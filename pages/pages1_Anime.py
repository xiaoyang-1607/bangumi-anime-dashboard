"""
动画榜单 - 基于归档导出的 xlsx 数据

使用 get_source.py 从 Bangumi 归档生成 xlsx 后，上传或放入项目根目录。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import io
import pandas as pd
import streamlit as st

from config import BANGUMI_APP_DATA_DIR, ANIME_CLEANED_FILE

st.set_page_config(
    page_title="Bangumi 动画榜单",
    layout="wide",
    initial_sidebar_state="expanded",
)

DEFAULT_PATH = BANGUMI_APP_DATA_DIR / ANIME_CLEANED_FILE


def load_from_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """将原始 DataFrame 清洗为展示格式。"""
    if df.empty:
        return df
    df = df.copy()
    df["name_cn"] = df.get("name_cn", df.get("name", "")).fillna(df.get("name", ""))
    df["date"] = pd.to_datetime(df.get("date"), errors="coerce")
    df["score"] = pd.to_numeric(df.get("score"), errors="coerce")
    df["score_total"] = pd.to_numeric(df.get("score_total"), errors="coerce")
    df["rank"] = pd.to_numeric(df.get("rank"), errors="coerce")
    df.dropna(subset=["date"], inplace=True)
    id_col = "id" if "id" in df.columns else "ID"
    df["Bangumi链接"] = "https://bgm.tv/subject/" + df[id_col].astype(str)
    df = df.rename(
        columns={
            "name_cn": "中文名",
            "name": "原名",
            "date": "开播日期",
            "score": "评分",
            "score_total": "评分人数",
            "rank": "Bangumi排名",
        }
    )
    return df[["中文名", "原名", "开播日期", "评分", "评分人数", "Bangumi排名", "Bangumi链接"]]


@st.cache_data
def load_from_path(file_path: str) -> pd.DataFrame:
    """从文件路径加载。"""
    df = pd.read_excel(file_path, engine="openpyxl")
    return load_from_dataframe(df)


st.title("Bangumi 动画榜单")
st.caption("数据来自归档导出的 xlsx。需先运行 get_source.py 生成，或从下方上传。")

# 数据源：本地文件 / 上传
df_original = None
if DEFAULT_PATH.exists():
    try:
        df_original = load_from_path(str(DEFAULT_PATH))
    except Exception as e:
        st.warning(f"读取本地文件失败: {e}")

if df_original is None or df_original.empty:
    uploaded = st.file_uploader(
        "上传 anime_cleaned.xlsx",
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

# 侧边栏
st.sidebar.header("筛选与排序")
search_term = st.sidebar.text_input("按名称搜索 (中文/原名)", value="")
if search_term:
    s = search_term.lower()
    df_filtered = df_filtered[
        df_filtered["中文名"].str.lower().str.contains(s, na=False)
        | df_filtered["原名"].str.lower().str.contains(s, na=False)
    ]

st.sidebar.subheader("日期范围")
min_year = int(df_original["开播日期"].min().year)
max_year = int(df_original["开播日期"].max().year)
all_years = list(range(min_year, max_year + 1))
all_months = list(range(1, 13))
c1, c2 = st.sidebar.columns(2)
with c1:
    start_year = st.selectbox("起始年", all_years, index=0, key="sy")
    start_month = st.selectbox("起始月", all_months, index=0, key="sm")
with c2:
    end_year = st.selectbox("结束年", all_years, index=len(all_years) - 1, key="ey")
    end_month = st.selectbox("结束月", all_months, index=11, key="em")

try:
    start_date = pd.to_datetime(f"{start_year}-{start_month}-01")
    ny, nm = (end_year + 1, 1) if end_month == 12 else (end_year, end_month + 1)
    end_date = pd.to_datetime(f"{ny}-{nm:02d}-01")
    if start_date < end_date:
        df_filtered = df_filtered[
            (df_filtered["开播日期"] >= start_date)
            & (df_filtered["开播日期"] < end_date)
        ]
    else:
        st.sidebar.error("起始日期须早于结束日期")
        df_filtered = df_filtered[0:0]
except ValueError:
    st.sidebar.error("日期无效")

min_s, max_s = float(df_original["评分"].min()), float(df_original["评分"].max())
score_range = st.sidebar.slider("评分范围", min_s, max_s, (min_s, max_s), step=0.1)
df_filtered = df_filtered[
    (df_filtered["评分"] >= score_range[0]) & (df_filtered["评分"] <= score_range[1])
]
user_min = st.sidebar.number_input(
    "最少评分人数", 0, int(df_original["评分人数"].max()), 0
)
df_filtered = df_filtered[df_filtered["评分人数"] >= user_min]

sort_by = st.sidebar.selectbox(
    "排序", ("开播日期", "评分", "评分人数", "Bangumi排名")
)
asc = st.sidebar.radio("排序方向", ("降序", "升序"), index=0) == "升序"
asc = asc if sort_by != "Bangumi排名" else True
df_sorted = df_filtered.sort_values(sort_by, ascending=asc)

# 展示
st.subheader(f"筛选结果 ({len(df_sorted)} 部)")
df_display = df_sorted.copy()
df_display["开播日期"] = df_display["开播日期"].dt.strftime("%Y-%m-%d")

st.dataframe(
    df_display[["Bangumi排名", "中文名", "原名", "开播日期", "评分", "评分人数", "Bangumi链接"]],
    column_config={
        "Bangumi链接": st.column_config.LinkColumn("链接", display_text="Bangumi"),
        "评分": st.column_config.NumberColumn("评分", format="%.1f"),
    },
    hide_index=True,
    use_container_width=True,
)
