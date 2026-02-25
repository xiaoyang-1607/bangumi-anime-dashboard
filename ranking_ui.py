"""
榜单页公共逻辑：数据加载、侧边栏筛选与排序、表格展示。
供 pages1_Anime 与 pages2_Game 复用。
"""
from __future__ import annotations

import pandas as pd
import streamlit as st


# 原始 xlsx 列名到展示列名的映射（date 列名由调用方指定）
_BASE_RENAME = {
    "name": "原名",
    "score": "评分",
    "score_total": "评分人数",
    "rank": "Bangumi排名",
}


def load_from_dataframe(
    df: pd.DataFrame,
    date_display_name: str,
) -> pd.DataFrame:
    """将原始 DataFrame 统一清洗为展示格式。date 列重命名为 date_display_name（开播日期/发行日期）。"""
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
    rename = {**_BASE_RENAME, "name_cn": "中文名", "date": date_display_name}
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    out_cols = ["中文名", "原名", date_display_name, "评分", "评分人数", "Bangumi排名", "Bangumi链接"]
    if "meta_tags" in df.columns:
        out_cols.append("meta_tags")
    return df[[c for c in out_cols if c in df.columns]]


@st.cache_data
def load_from_path(file_path: str, date_display_name: str) -> pd.DataFrame:
    """从文件路径加载并清洗。"""
    df = pd.read_excel(file_path, engine="openpyxl")
    return load_from_dataframe(df, date_display_name)


def apply_sidebar_filters(
    df_original: pd.DataFrame,
    date_column: str,
    sort_options: tuple,
    key_prefix: str = "",
) -> pd.DataFrame:
    """侧边栏：搜索、日期范围、评分、最少评分人数、标签、排序。返回排序后的 DataFrame。"""
    df = df_original.copy()
    k = key_prefix

    st.sidebar.header("筛选与排序")
    search_term = st.sidebar.text_input("按名称搜索 (中文/原名)", value="", key=f"{k}search")
    if search_term:
        s = search_term.lower()
        df = df[
            df["中文名"].str.lower().str.contains(s, na=False)
            | df["原名"].str.lower().str.contains(s, na=False)
        ]

    st.sidebar.subheader("日期范围")
    min_year = int(df_original[date_column].min().year)
    max_year = int(df_original[date_column].max().year)
    all_years = list(range(min_year, max_year + 1))
    all_months = list(range(1, 13))
    c1, c2 = st.sidebar.columns(2)
    with c1:
        start_year = st.selectbox("起始年", all_years, index=0, key=f"{k}sy")
        start_month = st.selectbox("起始月", all_months, index=0, key=f"{k}sm")
    with c2:
        end_year = st.selectbox("结束年", all_years, index=len(all_years) - 1, key=f"{k}ey")
        end_month = st.selectbox("结束月", all_months, index=11, key=f"{k}em")

    try:
        start_date = pd.to_datetime(f"{start_year}-{start_month}-01")
        ny, nm = (end_year + 1, 1) if end_month == 12 else (end_year, end_month + 1)
        end_date = pd.to_datetime(f"{ny}-{nm:02d}-01")
        if start_date < end_date:
            df = df[(df[date_column] >= start_date) & (df[date_column] < end_date)]
        else:
            st.sidebar.error("起始日期须早于结束日期")
            df = df[0:0]
    except ValueError:
        st.sidebar.error("日期无效")

    min_s, max_s = float(df_original["评分"].min()), float(df_original["评分"].max())
    score_range = st.sidebar.slider("评分范围", min_s, max_s, (min_s, max_s), step=0.1, key=f"{k}score")
    df = df[(df["评分"] >= score_range[0]) & (df["评分"] <= score_range[1])]
    user_min = st.sidebar.number_input(
        "最少评分人数", 0, int(df_original["评分人数"].max()), 0, key=f"{k}min"
    )
    df = df[df["评分人数"] >= user_min]

    if "meta_tags" in df.columns:
        tag_input = st.sidebar.text_input(
            "标签筛选 (多个用逗号分隔)",
            placeholder="如: 科幻, 原创",
            key=f"{k}tag",
        )
        if tag_input:
            tags = [t.strip() for t in tag_input.split(",") if t.strip()]
            for t in tags:
                df = df[df["meta_tags"].astype(str).str.contains(t, na=False)]

    sort_by = st.sidebar.selectbox("排序", sort_options, key=f"{k}sort")
    asc = st.sidebar.radio("排序方向", ("降序", "升序"), index=0, key=f"{k}asc") == "升序"
    asc = asc if sort_by != "Bangumi排名" else True
    return df.sort_values(sort_by, ascending=asc)


def render_table(
    df_sorted: pd.DataFrame,
    date_column: str,
    unit: str = "部",
) -> None:
    """展示筛选结果表格。"""
    display_cols = ["Bangumi排名", "中文名", "原名", date_column, "评分", "评分人数", "Bangumi链接"]
    if df_sorted.empty:
        st.info("无符合条件的结果。")
        return
    df_display = df_sorted.copy()
    df_display[date_column] = df_display[date_column].dt.strftime("%Y-%m-%d")
    st.subheader(f"筛选结果 ({len(df_sorted)} {unit})")
    st.dataframe(
        df_display[[c for c in display_cols if c in df_display.columns]],
        column_config={
            "Bangumi链接": st.column_config.LinkColumn("链接", display_text="Bangumi"),
            "评分": st.column_config.NumberColumn("评分", format="%.1f"),
        },
        hide_index=True,
        use_container_width=True,
    )


def load_data_or_upload(
    default_path,
    upload_label: str,
    date_display_name: str,
) -> pd.DataFrame | None:
    """
    优先从 default_path 加载，不存在或为空时显示上传组件。
    返回清洗后的 DataFrame，无数据时返回 None 并已 st.stop()。
    """
    df_original = None
    if default_path.exists():
        try:
            df_original = load_from_path(str(default_path), date_display_name)
        except Exception as e:
            st.warning(f"读取本地文件失败: {e}")

    if df_original is None or df_original.empty:
        uploaded = st.file_uploader(
            upload_label,
            type=["xlsx", "xls"],
            help="由 main.py 从归档生成后导出",
        )
        if uploaded:
            try:
                df_original = load_from_dataframe(
                    pd.read_excel(uploaded, engine="openpyxl"), date_display_name
                )
            except Exception as e:
                st.error(f"解析失败: {e}")
        else:
            st.info("请上传 xlsx 文件。")
            st.stop()

    return df_original
