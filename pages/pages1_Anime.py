import streamlit as st
import pandas as pd

# --- 配置 ---
st.set_page_config(
    page_title="Bangumi 动画排名数据分析",
    layout="wide",
    initial_sidebar_state="expanded"
)

DATA_FILE_NAME = 'anime_cleaned.xlsx'

# --- 1. 数据加载与清洗 ---
@st.cache_data
def load_and_clean_data(file_path):
    # 此函数返回带有 datetime 对象的 DataFrame，用于准确的筛选和排序
    df = pd.DataFrame()
    csv_path = file_path.replace('.xlsx', '.csv')

    # 尝试加载文件
    try:
        df = pd.read_excel(file_path, engine='openpyxl')
    except FileNotFoundError:
        try:
            df = pd.read_csv(csv_path)
        except FileNotFoundError:
            st.error("找不到数据文件。请确保 'anime_cleaned.xlsx' 或对应的 CSV 文件存在。")
            st.stop()
        except Exception as e:
            st.error(f"加载 CSV 文件时发生错误: {e}")
            st.stop()
    except Exception as e:
        st.error(f"加载 XLSX 文件时发生错误: {e}")
        st.stop()

    if df.empty:
        st.error("数据加载失败，无法继续处理。")
        st.stop()

    # 填充中文名为空的项，确保关键列为正确类型
    df['name_cn'] = df['name_cn'].fillna(df['name'])
    df['date'] = pd.to_datetime(df['date'], errors='coerce')  # 保持为 datetime 类型
    df['score'] = pd.to_numeric(df['score'], errors='coerce')
    df['score_total'] = pd.to_numeric(df['score_total'], errors='coerce')
    df['rank'] = pd.to_numeric(df['rank'], errors='coerce')

    # 移除日期无效的行
    df.dropna(subset=['date'], inplace=True)

    df['Bangumi链接'] = 'https://bgm.tv/subject/' + df['id'].astype(str)

    # 重命名列
    df = df.rename(columns={
        'name_cn': '中文名', 'name': '原名', 'date': '开播日期',
        'score': '评分', 'score_total': '评分人数', 'rank': 'Bangumi排名'
    })

    display_cols = ['中文名', '原名', '开播日期', '评分', '评分人数', 'Bangumi排名', 'Bangumi链接']
    return df[display_cols]


# --- 2. 应用主逻辑 ---
st.title("📺 Bangumi 动画排名数据分析")

# 加载原始数据 (包含 datetime 对象)
df_original = load_and_clean_data(DATA_FILE_NAME)
df_filtered = df_original.copy()  # 用于筛选操作

# --- 3. 侧边栏筛选器 ---
st.sidebar.header("⚙️ 数据筛选与排序")

search_term = st.sidebar.text_input("按名称搜索 (中文/原名)", value="")

if search_term:
    search_term_lower = search_term.lower()
    df_filtered = df_filtered[
        df_filtered['中文名'].str.lower().str.contains(search_term_lower, na=False) |
        df_filtered['原名'].str.lower().str.contains(search_term_lower, na=False)
        ]

st.sidebar.subheader("📅 日期范围筛选")

# 1. 获取所有可选的年份和月份
min_year = int(df_original['开播日期'].min().year)
max_year = int(df_original['开播日期'].max().year)
all_years = list(range(min_year, max_year + 1))
all_months = list(range(1, 13))

# 2. 起始日期选择
st.sidebar.markdown("##### 起始时间")
col1, col2 = st.sidebar.columns(2)
with col1:
    start_year = st.selectbox('年份', all_years, index=0, key='start_year', label_visibility='collapsed')
with col2:
    start_month = st.selectbox('月份', all_months, index=0, key='start_month', label_visibility='collapsed')

# 3. 结束日期选择
st.sidebar.markdown("##### 结束时间")
col3, col4 = st.sidebar.columns(2)
with col3:
    # 默认值设置为最大年份
    end_year = st.selectbox('年份', all_years, index=len(all_years) - 1, key='end_year', label_visibility='collapsed')
with col4:
    # 默认值设置为最大月份 (即 12 月)
    end_month = st.selectbox('月份', all_months, index=11, key='end_month', label_visibility='collapsed')

# 4. 构建日期对象并应用筛选逻辑
try:
    # 构造起始日期 (该月的 1 号)
    start_date = pd.to_datetime(f"{start_year}-{start_month}-01")

    # 构造结束日期 (选择月份的下一月 1 号，作为上界，确保包含选中月份的全部天数)
    if end_month == 12:
        end_month_next = 1
        end_year_next = end_year + 1
    else:
        end_month_next = end_month + 1
        end_year_next = end_year

    end_date = pd.to_datetime(f"{end_year_next}-{end_month_next}-01")

    # 逻辑检查：如果起始日期晚于等于结束日期，显示错误
    if start_date >= end_date:
        st.sidebar.error("起始日期不能晚于或等于结束日期！")
        # 为了防止应用崩溃，我们使用一个空范围
        df_filtered = df_filtered[0:0]
    else:
        # 应用日期筛选 (使用 < 结束日期，因为结束日期是下一月的 1 号)
        df_filtered = df_filtered[
            (df_filtered['开播日期'] >= start_date) &
            (df_filtered['开播日期'] < end_date)
            ]

except ValueError:
    st.sidebar.error("日期选择解析失败，请检查年份和月份是否有效。")

# 评分筛选
min_score = df_original['评分'].min()
max_score = df_original['评分'].max()
score_range = st.sidebar.slider(
    '评分范围', float(min_score), float(max_score),
    (float(min_score), float(max_score)), step=0.1
)
df_filtered = df_filtered[
    (df_filtered['评分'] >= score_range[0]) & (df_filtered['评分'] <= score_range[1])
    ]

# 人数筛选
max_users = df_original['评分人数'].max()
user_threshold = st.sidebar.number_input(
    '最少评分人数 (筛选热度)', min_value=0, max_value=int(max_users), value=0
)
df_filtered = df_filtered[df_filtered['评分人数'] >= user_threshold]

# --- 4. 排序选项 ---
sort_by = st.sidebar.selectbox("排序依据", ('开播日期', '评分', '评分人数', 'Bangumi排名'))
default_ascending = True if sort_by == 'Bangumi排名' else False
sort_order = st.sidebar.radio(
    f"{sort_by} 排序方式", ('降序', '升序'), index=0 if not default_ascending else 1
)
is_ascending = (sort_order == '升序')

df_sorted = df_filtered.sort_values(by=sort_by, ascending=is_ascending)

# --- 5. 结果展示 ---
st.subheader(f"✨ 筛选结果 ({len(df_sorted)} 部动画)")

# 在展示前，创建一个用于显示的副本并格式化日期
df_display = df_sorted.copy()
df_display['开播日期'] = df_display['开播日期'].dt.strftime('%Y-%m-%d')

st.caption(f"数据更新时间: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")

st.dataframe(
    df_display[['Bangumi排名', '中文名', '原名', '开播日期', '评分', '评分人数', 'Bangumi链接']],   # <-- 确保 'Bangumi链接' 在展示列中
    width='stretch',
    column_config={
        "Bangumi链接": st.column_config.LinkColumn(
            "Bangumi 链接",
            help="点击可查看 Bangumi 页面",
            display_text="🔗 链接"
        ),
        'Bangumi排名': "排名",
        '评分': st.column_config.NumberColumn("评分", format="%.1f", width="small"),
        '评分人数': "评分人数",
    },
    hide_index=True
)
