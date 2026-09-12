"""全站视觉样式与可复用界面组件。"""

from __future__ import annotations

from datetime import datetime
import html
import json
from pathlib import Path

import streamlit as st

from config import BANGUMI_APP_DATA_DIR, DATA_METADATA_FILE


def configure_app() -> None:
    st.set_page_config(
        page_title="Bangumi 数据探索站",
        page_icon="🌸",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            "Get help": "https://github.com/xiaoyang-1607/bangumi-anime-dashboard",
            "Report a Bug": "https://github.com/xiaoyang-1607/bangumi-anime-dashboard/issues",
            "About": "基于 Bangumi Archive 构建的非官方数据探索工具。",
        },
    )
    st.html(
        """
        <style>
        :root { --bgm-pink:#ef7891; --bgm-ink:#27232b; --bgm-muted:#746c78; }
        .stApp { background:radial-gradient(circle at 90% 0%,#fff0f3 0,transparent 28rem),#fffdfc; }
        [data-testid="stHeader"] { background:rgba(255,253,252,.82); backdrop-filter:blur(12px); }
        [data-testid="stSidebar"] { border-right:1px solid rgba(239,120,145,.14); }
        [data-testid="stMetric"] { background:#fff; border:1px solid #f0e5e8; border-radius:16px; padding:1rem 1.1rem; box-shadow:0 8px 24px rgba(64,38,48,.045); }
        [data-testid="stMetricLabel"] { color:var(--bgm-muted); }
        [data-testid="stDataFrame"] { border:1px solid #efe5e8; border-radius:14px; overflow:hidden; }
        [data-testid="stSegmentedControl"] { margin:.1rem 0 .55rem; }
        [data-testid="stSidebar"] [data-testid="stExpander"] { border-radius:12px; }
        @media (min-width:1200px) { .block-container { max-width:1500px; padding-top:2rem; } }
        .bgm-hero { padding:2rem 2.2rem; border-radius:24px; margin:.4rem 0 1.4rem; color:white; background:linear-gradient(125deg,#3c303a 0%,#8f5365 55%,#ef7891 100%); box-shadow:0 18px 45px rgba(106,54,72,.18); }
        .bgm-eyebrow { font-size:.76rem; letter-spacing:.14em; text-transform:uppercase; opacity:.75; font-weight:700; }
        .bgm-hero h1 { margin:.35rem 0 .45rem; font-size:clamp(1.8rem,4vw,3.1rem); line-height:1.12; color:white; }
        .bgm-hero p { margin:0; max-width:46rem; font-size:1.02rem; opacity:.88; }
        .bgm-chip { display:inline-block; margin:.1rem .3rem .1rem 0; padding:.25rem .62rem; border-radius:999px; background:#f8edf0; color:#774353; font-size:.79rem; border:1px solid #efd9df; }
        .bgm-kicker { color:#ef7891; font-size:.78rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase; }
        .bgm-page-title { margin:.18rem 0 .25rem; font-size:2.15rem; line-height:1.2; color:var(--bgm-ink); }
        .bgm-page-copy { color:var(--bgm-muted); margin:0 0 1.15rem; }
        .bgm-side-brand { padding:.2rem 0 1rem; }
        .bgm-side-brand strong { display:block; font-size:1.05rem; color:var(--bgm-ink); }
        .bgm-side-brand span { color:var(--bgm-muted); font-size:.8rem; }
        @media (max-width:700px) { .bgm-hero { padding:1.45rem; border-radius:18px; } .bgm-page-title { font-size:1.75rem; } .block-container { padding-left:1rem; padding-right:1rem; } }
        </style>
        """
    )


def render_page_header(kicker: str, title: str, description: str) -> None:
    st.html(
        f'<div><div class="bgm-kicker">{html.escape(kicker)}</div>'
        f'<h1 class="bgm-page-title">{html.escape(title)}</h1>'
        f'<p class="bgm-page-copy">{html.escape(description)}</p></div>'
    )


def render_sidebar_brand(section: str) -> None:
    st.sidebar.html(
        f'<div class="bgm-side-brand"><strong>🌸 Bangumi Explorer</strong>'
        f'<span>{html.escape(section)} · 精准发现下一部作品</span></div>'
    )


def load_data_metadata(path: Path | None = None) -> dict:
    metadata_path = path or (BANGUMI_APP_DATA_DIR / DATA_METADATA_FILE)
    try:
        return json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def format_archive_date(metadata: dict) -> str:
    value = metadata.get("archive_created_at") or metadata.get("generated_at")
    if not value:
        return "未知"
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        return str(value)[:10]


def render_filter_chips(labels: list[str]) -> None:
    if not labels:
        st.caption("当前显示完整数据集")
        return
    chips = "".join(f'<span class="bgm-chip">{html.escape(label)}</span>' for label in labels)
    st.html(f'<div aria-label="当前筛选条件">{chips}</div>')
