"""Bangumi 数据探索站统一入口与顶部导航。"""

import streamlit as st

from ui import configure_app


configure_app()

pages = {
    "探索": [
        st.Page("views/home.py", title="概览", icon=":material/home:", default=True),
        st.Page("pages/pages1_Anime.py", title="动画", icon=":material/movie:"),
        st.Page("pages/pages2_Game.py", title="游戏", icon=":material/sports_esports:"),
    ]
}

navigation = st.navigation(pages, position="top")
navigation.run()
