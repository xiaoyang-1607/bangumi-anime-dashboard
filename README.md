# 📺🎮 Bangumi 综合数据分析平台

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://bangumi-anime-dashboard-wvdgaakdmuyfd7s9v4ujj3.streamlit.app/)

> 基于 Bangumi 归档数据，使用 Streamlit 构建的交互式分析面板，用于展示和筛选动画和游戏作品排名及评分数据。

---

## ✨ 核心特性

本项目已升级为**多页应用 (Multi-page App)** 架构，包含两个完全独立的分析模块，并通过左侧导航栏进行切换。

### 1. 📺 Anime (动画榜单)
专注于日本动画作品，提供按季度、年份、评分和评分人数的精细化筛选。

### 2. 🎮 Game (游戏榜单)
专注于游戏作品，提供按**发行日期**、评分和评分人数的筛选与排名查询。

### 通用功能

* **名称搜索**: 支持按作品的**中文名**或**日文原名**进行模糊搜索。
* **精确日期筛选**: 可按 **年份** 和 **月份** 精确选择作品的开播/发行时间范围。
* **热度筛选**: 通过数字输入框设定作品的**最少评分人数**，过滤掉冷门作品。
* **统一链接**: 表格中的每一项都包含一个独立的 **Bangumi 链接**，方便用户快速查看作品详情。

---

## 🌐 在线使用

您可以直接通过以下链接访问和使用部署好的综合分析平台：

[**👉 前往 Bangumi 综合数据分析平台**](https://bangumi-anime-dashboard-wvdgaakdmuyfd7s9v4ujj3.streamlit.app/)

### 使用说明

1. 访问应用后，首先看到的是**欢迎页**。
2. 使用左侧的 **导航栏** 选择您想要查看的榜单（`Anime` 或 `Game`）。
3. 在左侧的 **筛选器 (Sidebar)** 中调整参数。

---

## ⚙️ 项目架构与文件

本项目采用 Streamlit 的多页应用结构，核心功能代码都位于 `pages/` 文件夹内。

| 文件/目录 | 作用描述 |
| :--- | :--- |
| **`app.py`** | **应用入口**：轻量级导航页，引导用户选择榜单。 |
| **`pages/`** | **多页代码目录**：核心功能页面存储地。 |
| ├── `pages1_Anime.py` | 动画榜单模块的代码和筛选逻辑。 |
| └── `pages2_Game.py` | 游戏榜单模块的代码和筛选逻辑。 |
| **`config.py`** | 统一配置模块，支持环境变量覆盖数据路径。 |
| **`get_source.py`** | 从 Bangumi 归档 JSONL 提取并导出 Excel。 |
| **`best.py`** | 月度最佳作品统计脚本。 |
| **`anime_cleaned.xlsx`** | 动画数据源（清洗后的 Excel 文件）。 |
| **`game_cleaned.xlsx`** | 游戏数据源（清洗后的 Excel 文件）。 |

## 📊 数据信息

* **数据来源**: 原始数据来源于 Bangumi 归档数据库。
* **数据格式**: 应用使用 `.xlsx` 文件格式进行数据加载和处理。
* **数据更新频率**: 一般情况下，数据会**每周更新一次**，以确保排名的时效性。

---

## 🛠️ 本地运行（针对开发者）

如果您想在本地运行或进一步开发此应用，请遵循以下步骤：

1. **克隆仓库**:
    ```bash
    git clone https://github.com/xiaoyang-1607/bangumi-anime-dashboard.git
    cd bangumi-anime-dashboard
    ```

2. **安装依赖**:
    ```bash
    pip install -r requirements.txt
    ```

3. **准备数据**:
    将数据文件 `anime_cleaned.xlsx` 和 `game_cleaned.xlsx` 放入项目根目录。

4. **（可选）配置数据路径**:
    数据脚本 (`get_source.py`、`best.py`、`test_data.py`) 支持环境变量：
    - `BANGUMI_DUMP_DIR`: Bangumi 归档目录（含 `subject.jsonlines`），默认为 `./data`
    - `BANGUMI_APP_DATA_DIR`: Streamlit 数据目录，默认为项目根目录

5. **运行应用**:
    ```bash
    streamlit run app.py
    ```

应用将自动在您的浏览器中打开 (`http://localhost:8501`)。
