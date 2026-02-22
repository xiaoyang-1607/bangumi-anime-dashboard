"""
项目统一配置模块。

支持通过环境变量覆盖默认路径，便于在不同环境中部署和协作。

环境变量：
- BANGUMI_DUMP_DIR: Bangumi 归档数据目录（包含 subject.jsonlines）
- BANGUMI_APP_DATA_DIR: Streamlit 应用数据目录（包含 anime_cleaned.xlsx, game_cleaned.xlsx）
"""
import os
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent

# Bangumi 归档/工作目录：存放 subject.jsonlines、导出 Excel、清洗后的数据
# 可通过环境变量 BANGUMI_DUMP_DIR 覆盖
_DUMP_DIR = os.environ.get(
    "BANGUMI_DUMP_DIR",
    str(PROJECT_ROOT / "data"),
)
BANGUMI_DUMP_DIR = Path(_DUMP_DIR)

# Streamlit 应用数据目录：存放 anime_cleaned.xlsx, game_cleaned.xlsx
# 可通过环境变量 BANGUMI_APP_DATA_DIR 覆盖，默认为项目根目录
_APP_DATA_DIR = os.environ.get(
    "BANGUMI_APP_DATA_DIR",
    str(PROJECT_ROOT),
)
BANGUMI_APP_DATA_DIR = Path(_APP_DATA_DIR)

# 数据文件名称
JSONL_FILE_NAME = "subject.jsonlines"
ANIME_CLEANED_FILE = "anime_cleaned.xlsx"
GAME_CLEANED_FILE = "game_cleaned.xlsx"
