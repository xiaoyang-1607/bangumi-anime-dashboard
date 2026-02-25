import streamlit as st

st.set_page_config(
    page_title="Bangumi 综合数据分析平台",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Bangumi 综合数据分析平台")

st.markdown("""
请从左侧导航选择榜单：

* **Anime（动画榜单）**：动画作品排名与筛选
* **Game（游戏榜单）**：游戏作品排名与筛选

数据需使用 `get_source.py` 从 Bangumi 归档生成 xlsx 后，上传或放入项目目录。
""")
