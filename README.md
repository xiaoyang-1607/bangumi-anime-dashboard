# Bangumi 综合数据分析平台

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://bangumi-anime-dashboard-wvdgaakdmuyfd7s9v4ujj3.streamlit.app/)

基于 Bangumi 归档数据构建的交互式榜单：**动画榜单**与**游戏榜单**，支持按名称、日期、评分、标签筛选与排序。

---

## 快速开始（仅查看榜单）

若你只想在本地或在线查看榜单、不做数据更新：

1. **克隆并安装**
   ```bash
   git clone https://github.com/xiaoyang-1607/bangumi-anime-dashboard.git
   cd bangumi-anime-dashboard
   pip install -r requirements.txt
   ```

2. **启动应用**
   ```bash
   streamlit run app.py
   ```

3. **使用数据**
   - 若项目根目录已有 `anime_cleaned.xlsx`、`game_cleaned.xlsx`，应用会自动加载。
   - 若无，在左侧进入 **Anime** 或 **Game** 页面后，在页面内**上传**对应的 xlsx 文件即可。

也可直接使用 [Streamlit Cloud 在线应用](https://bangumi-anime-dashboard-wvdgaakdmuyfd7s9v4ujj3.streamlit.app/)（若仓库中已包含上述 xlsx，会直接展示）。

---

## 从归档生成数据并更新到 GitHub

若你需要**自己从 Bangumi 归档生成** `anime_cleaned.xlsx` / `game_cleaned.xlsx`，并**自动提交、推送到本仓库**，按以下步骤操作。

### 1. 获取 Bangumi 归档

- 打开 [Bangumi Archive Releases](https://github.com/bangumi/Archive/releases)，下载最新的 `dump-*.zip`。
- 解压后，确保目录内包含 **`subject.jsonlines`**。

### 2. 在项目中设置解压目录

用编辑器打开项目根目录下的 **`main.py`**，修改顶部的解压目录（使用你的实际路径）：

```python
# ---------- 手动设置：归档解压目录（内含 subject.jsonlines） ----------
DUMP_DIR = Path(r"D:\path\to\your\bangumi-dump-extracted")  # 改为你的解压路径
# --------------------------------------------------------------------
```

例如解压到了 `D:\data\bangumi-dump`，则写：

```python
DUMP_DIR = Path(r"D:\data\bangumi-dump")
```

### 3. 运行生成与上传

在项目根目录执行：

```bash
python main.py
```

脚本会依次：

1. 读取 `DUMP_DIR/subject.jsonlines`，清洗出动画与游戏数据。
2. 生成 **`anime_cleaned.xlsx`**、**`game_cleaned.xlsx`**，并保存到：
   - 解压目录（`DUMP_DIR`）
   - 项目根目录
3. 对项目根目录下的 xlsx 做格式检查。
4. 若检查通过：`git add` → `git commit` → `git push origin main`，用新文件**替换**仓库中已有的同名 xlsx。

若项目目录中原本已有这两个 xlsx，会被新生成的文件覆盖；推送后 GitHub 上的文件也会被更新。

### 4. 查看结果

- 本地：再次运行 `streamlit run app.py`，应用会从项目根目录读取最新的 xlsx。
- 在线：若已配置 Streamlit Cloud 等，推送后会自动使用仓库中的新数据。

---

## 功能说明

| 页面 | 说明 |
|------|------|
| **Anime（动画榜单）** | 按开播日期、评分、评分人数、Bangumi 排名筛选与排序，支持名称搜索与标签筛选 |
| **Game（游戏榜单）** | 按发行日期、评分、评分人数、Bangumi 排名筛选与排序，支持名称搜索与标签筛选 |

数据来源：`anime_cleaned.xlsx` / `game_cleaned.xlsx`，可由 **`main.py`** 从 Bangumi 归档自动生成（见上文）。

---

## 项目结构

| 文件/目录 | 说明 |
|-----------|------|
| `app.py` | Streamlit 应用入口 |
| `pages/pages1_Anime.py` | 动画榜单页 |
| `pages/pages2_Game.py` | 游戏榜单页 |
| `ranking_ui.py` | 榜单页公共逻辑（加载、筛选、展示） |
| `main.py` | **数据流水线**：从归档生成 xlsx，双路保存并推送到 GitHub（解压目录在脚本内设置） |
| `get_source.py` | 归档 JSONL 的读取与导出（被 `main.py` 调用） |
| `config.py` | 应用路径等配置（可配合环境变量） |
| `best.py` | 月度最佳统计脚本（依赖 `BANGUMI_DUMP_DIR` 下的 xlsx） |

---

## 环境变量（可选）

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `BANGUMI_APP_DATA_DIR` | Streamlit 读取 xlsx 的目录 | 项目根目录 |
| `BANGUMI_DUMP_DIR` | 仅被 `best.py`、`test_data.py` 使用 | `./data` |

归档解压路径**不在**环境变量中配置，请在 **`main.py`** 内修改 `DUMP_DIR`。
