"""项目路径与文件名配置。

环境变量优先级高于项目根目录下的 ``.env``，便于在本地、CI 和
Streamlit Cloud 使用同一套代码。
"""

from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent


def _load_local_env(path: Path) -> None:
    """加载简单的 KEY=VALUE 配置，不覆盖系统中已存在的环境变量。"""
    if not path.is_file():
        return

    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key:
            os.environ.setdefault(key, value)


_load_local_env(PROJECT_ROOT / ".env")


def _configured_path(variable: str, default: Path) -> Path:
    value = Path(os.environ.get(variable, default)).expanduser()
    if not value.is_absolute():
        value = PROJECT_ROOT / value
    return value.resolve()


BANGUMI_DUMP_DIR = _configured_path("BANGUMI_DUMP_DIR", PROJECT_ROOT / "data")
BANGUMI_APP_DATA_DIR = _configured_path("BANGUMI_APP_DATA_DIR", PROJECT_ROOT)

JSONL_FILE_NAME = "subject.jsonlines"
ANIME_CLEANED_FILE = "anime_cleaned.xlsx"
GAME_CLEANED_FILE = "game_cleaned.xlsx"
DATA_METADATA_FILE = "data_metadata.json"

DATA_FILES = {
    "动画": ANIME_CLEANED_FILE,
    "游戏": GAME_CLEANED_FILE,
}
