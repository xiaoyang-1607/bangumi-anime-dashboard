import streamlit as st

st.set_page_config(
    page_title="Bangumi 综合数据分析平台",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Bangumi 综合数据分析平台")

st.markdown("""
本平台支持两种数据来源，请从左侧导航选择：

### 归档模式（需 xlsx 文件）
* **Anime（动画榜单）** / **Game（游戏榜单）**  
  使用 `get_source.py` 从 Bangumi 归档生成 xlsx 后，上传或放入项目目录即可查看。

### API 模式（无需文件）
* **API 实时排行**  
  从 Bangumi API 实时拉取排行榜，类似主站 [bgm.tv](https://bgm.tv) 的排行页，无需上传任何文件。
""")
