import streamlit as st
import pandas as pd

# --- 配置 ---
st.set_page_config(
    page_title="Bangumi 游戏榜单分析",
    layout="wide",
)

DATA_FILE_NAME = 'game_cleaned.xlsx'  # <--- 已修改为 XLSX


# --- 1. 数据加载与清洗 (需适应游戏数据) ---
@st.cache_data
def load_and_clean_data(file_path):
    df = pd.DataFrame()

    # 尝试加载 XLSX 文件 (游戏数据)
    try:
        # 使用 pd.read_excel 加载 XLSX 文件
        df = pd.read_excel(file_path, engine='openpyxl')
    except FileNotFoundError:
        st.error(f"找不到数据文件。请确保 '{DATA_FILE_NAME}' 文件存在。")
        st.stop()
    except Exception as e:
        st.error(f"加载 XLSX 文件时发生错误: {e}")
        st.stop()

    if df.empty:
        st.error("数据加载失败，无法继续处理。")
        st.stop()

    # 填充中文名为空字符串
    df['name_cn'] = df['name_cn'].fillna('')

    # 统一列名
    df.columns = ['ID', '原名', '中文名', '发行日期', '评分', '评分人数', 'Bangumi排名']

    # 将日期字符串转换为 datetime 对象
    try:
        df['发行日期'] = pd.to_datetime(df['发行日期'], errors='coerce')
        df = df.dropna(subset=['发行日期'])  # 清除无效日期
    except Exception as e:
        st.error(f"日期转换错误: {e}")
        st.stop()

    # 确保关键列为正确类型
    df['评分'] = pd.to_numeric(df['评分'], errors='coerce')
    df['评分人数'] = pd.to_numeric(df['评分人数'], errors='coerce')
    df['Bangumi排名'] = pd.to_numeric(df['Bangumi排名'], errors='coerce')

    # 创建完整的 Bangumi 链接列
    df['Bangumi链接'] = 'https://bgm.tv/subject/' + df['ID'].astype(str)

    display_cols = ['中文名', '原名', '发行日期', '评分', '评分人数', 'Bangumi排名', 'Bangumi链接']
    return df[display_cols]


# --- 2. 应用主逻辑 ---
st.title("🎮 Bangumi 游戏榜单分析")

# 加载原始数据 (包含 datetime 对象)
df_original = load_and_clean_data(DATA_FILE_NAME)
df_filtered = df_original.copy()

# --- 3. 侧边栏筛选器 ---
st.sidebar.header("⚙️ 数据筛选与排序")

# 名称搜索
search_term = st.sidebar.text_input('按名称搜索 (中文/原名)', value='').strip()
if search_term:
    search_term_lower = search_term.lower()
    df_filtered = df_filtered[
        df_filtered['中文名'].str.lower().str.contains(search_term_lower, na=False) |
        df_filtered['原名'].str.lower().str.contains(search_term_lower, na=False)
        ]

# 日期范围筛选 (使用发行日期)
st.sidebar.subheader("📅 日期范围筛选")
unique_years = sorted(df_original['发行日期'].dt.year.dropna().astype(int).unique())

if unique_years:
    all_years = list(range(unique_years[0], unique_years[-1] + 1))
    all_months = list(range(1, 13))

    st.sidebar.markdown("##### 起始时间")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_year = st.selectbox('年份', all_years, index=0, key='g_start_year', label_visibility='collapsed')
    with col2:
        start_month = st.selectbox('月份', all_months, index=0, key='g_start_month', label_visibility='collapsed')

    st.sidebar.markdown("##### 结束时间")
    col3, col4 = st.sidebar.columns(2)
    with col3:
        end_year = st.selectbox('年份', all_years, index=len(all_years) - 1, key='g_end_year',
                                label_visibility='collapsed')
    with col4:
        end_month = st.selectbox('月份', all_months, index=11, key='g_end_month', label_visibility='collapsed')

    try:
        start_date = pd.to_datetime(f"{start_year}-{start_month}-01")
        if end_month == 12:
            end_month_next = 1
            end_year_next = end_year + 1
        else:
            end_month_next = end_month + 1
            end_year_next = end_year
        end_date = pd.to_datetime(f"{end_year_next}-{end_month_next}-01")

        if start_date >= end_date:
            st.sidebar.error("起始日期不能晚于或等于结束日期！")
            df_filtered = df_filtered[0:0]
        else:
            df_filtered = df_filtered[
                (df_filtered['发行日期'] >= start_date) &
                (df_filtered['发行日期'] < end_date)
                ]
    except ValueError:
        st.sidebar.error("日期选择解析失败，请检查年份和月份是否有效。")

# 评分筛选
min_score = df_original['评分'].min()
max_score = df_original['评分'].max()
score_range = st.sidebar.slider(
    '评分范围', float(min_score), float(max_score),
    (float(min_score), float(max_score)), step=0.1, key='g_score_range'
)
df_filtered = df_filtered[
    (df_filtered['评分'] >= score_range[0]) & (df_filtered['评分'] <= score_range[1])
    ]

# 人数筛选
max_users = df_original['评分人数'].max()
user_threshold = st.sidebar.number_input(
    '最少评分人数 (筛选热度)', min_value=0, max_value=int(max_users), value=0, key='g_user_threshold'
)
df_filtered = df_filtered[df_filtered['评分人数'] >= user_threshold]

# --- 4. 排序选项 ---
sort_by = st.sidebar.selectbox("排序依据", ('发行日期', '评分', '评分人数', 'Bangumi排名'), key='g_sort_by')
default_ascending = True if sort_by == 'Bangumi排名' else False
sort_order = st.sidebar.radio(
    f"{sort_by} 排序方式", ('降序', '升序'), index=0 if not default_ascending else 1, key='g_sort_order'
)
is_ascending = (sort_order == '升序')

df_sorted = df_filtered.sort_values(by=sort_by, ascending=is_ascending)

# --- 5. 结果展示 ---
st.subheader(f"✨ 筛选结果 ({len(df_sorted)} 个游戏)")

if len(df_sorted) > 0:
    df_display = df_sorted.copy()
    df_display['发行日期'] = df_display['发行日期'].dt.strftime('%Y-%m-%d')

    st.dataframe(
        df_display[['Bangumi排名', '中文名', '原名', '发行日期', '评分', '评分人数', 'Bangumi链接']],
        column_config={
            # 使用 LinkColumn 来显示可点击的链接
            "Bangumi链接": st.column_config.LinkColumn(
                "Bangumi 链接",
                help="点击可查看 Bangumi 页面",
                display_text="🔗 链接"  # 显示为简短的图标或文字
            ),
            'Bangumi排名': "排名",  # 恢复为普通列名
            '评分': st.column_config.NumberColumn("评分", format="%.1f", width="small"),
            '评分人数': "评分人数",
        },
        hide_index=True,
        width='stretch'
    )
else:
    st.info("没有找到符合筛选条件的结果。")

st.caption("数据来源：Bangumi 归档数据库")
