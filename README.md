# Bangumi 综合数据分析平台

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://bangumi-anime-dashboard-wvdgaakdmuyfd7s9v4ujj3.streamlit.app/)

基于 Bangumi 数据，使用 Streamlit 构建的交互式分析面板，支持**归档 xlsx** 与 **API 实时排行**两种模式。

---

## 数据模式

| 模式 | 说明 | 数据来源 |
|------|------|----------|
| **归档模式** | 动画/游戏榜单，支持筛选、搜索 | 上传 `anime_cleaned.xlsx` / `game_cleaned.xlsx`（由 `get_source.py` 从归档生成） |
| **API 模式** | 在线排行，类似 Bangumi 主站 | [Bangumi API](https://bangumi.github.io/api/) 实时获取，无需上传文件 |

---

## 功能概览

### 归档模式（Anime / Game 页面）
* 名称搜索（中文 / 原名）
* 日期、评分、评分人数筛选
* 多维度排序
* 需先运行 `get_source.py` 生成 xlsx，或直接在页面中上传

### API 模式（API 实时排行页面）
* 动画 / 游戏排行榜
* 实时从 Bangumi API 拉取
* 无需本地数据文件

---

## 本地运行

```bash
git clone https://github.com/xiaoyang-1607/bangumi-anime-dashboard.git
cd bangumi-anime-dashboard
pip install -r requirements.txt
streamlit run app.py
```

### 归档模式：准备 xlsx

1. 从 [Bangumi Archive](https://github.com/bangumi/Archive) 获取归档数据：
   - 最新归档地址见 [aux/latest.json](https://raw.githubusercontent.com/bangumi/Archive/master/aux/latest.json)
   - 在 [Releases](https://github.com/bangumi/Archive/releases) 下载 `dump-*.zip`，解压得到 `subject.jsonlines`
2. 设置环境变量（可选）：`BANGUMI_DUMP_DIR` 指向归档解压目录
3. 运行：`python get_source.py`
4. 将生成的 `bangumi_anime_data.xlsx`、`bangumi_game_data.xlsx` 清洗后，在应用中上传或放入项目根目录

---

## 项目结构

| 文件 | 说明 |
|------|------|
| `app.py` | 应用入口 |
| `pages/` | 多页模块 |
| ├── `pages1_Anime.py` | 动画榜单（归档 xlsx） |
| ├── `pages2_Game.py` | 游戏榜单（归档 xlsx） |
| └── `pages3_API_Ranking.py` | API 实时排行 |
| `get_source.py` | 从归档 JSONL 导出 xlsx |
| `bangumi_api.py` | Bangumi API 客户端 |
| `config.py` | 配置（环境变量） |
| `best.py` | 月度最佳统计脚本 |

---

## 环境变量

| 变量 | 说明 |
|------|------|
| `BANGUMI_DUMP_DIR` | 归档目录（含 subject.jsonlines），默认 `./data` |
| `BANGUMI_APP_DATA_DIR` | xlsx 数据目录，默认项目根目录 |
| `BANGUMI_ACCESS_TOKEN` | （可选）API Access Token |
| `BANGUMI_USER_AGENT` | （可选）API 请求 User-Agent |
