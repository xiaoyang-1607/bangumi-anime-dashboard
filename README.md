# Bangumi 综合数据分析平台

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://bangumi-anime-dashboard-wvdgaakdmuyfd7s9v4ujj3.streamlit.app/)

基于 Bangumi 归档数据，使用 Streamlit 构建的交互式分析面板。

---

## 功能

* **动画榜单**：名称搜索，日期、评分、评分人数筛选，多维度排序
* **游戏榜单**：同上，按发行日期与评分筛选

数据来源：上传 `anime_cleaned.xlsx` / `game_cleaned.xlsx`（由 `get_source.py` 从归档生成）。

---

## 本地运行

```bash
git clone https://github.com/xiaoyang-1607/bangumi-anime-dashboard.git
cd bangumi-anime-dashboard
pip install -r requirements.txt
streamlit run app.py
```

### 准备 xlsx

1. 从 [Bangumi Archive](https://github.com/bangumi/Archive) 获取归档：
   - 最新地址见 [aux/latest.json](https://raw.githubusercontent.com/bangumi/Archive/master/aux/latest.json)
   - 在 [Releases](https://github.com/bangumi/Archive/releases) 下载 `dump-*.zip`，解压得到 `subject.jsonlines`
2. 设置环境变量（可选）：`BANGUMI_DUMP_DIR` 指向归档解压目录
3. 运行：`python get_source.py`
4. 将生成的 xlsx 清洗后，在应用中上传或放入项目根目录

---

## 项目结构

| 文件 | 说明 |
|------|------|
| `app.py` | 应用入口 |
| `pages/pages1_Anime.py` | 动画榜单 |
| `pages/pages2_Game.py` | 游戏榜单 |
| `get_source.py` | 从归档 JSONL 导出 xlsx |
| `config.py` | 配置（环境变量） |
| `best.py` | 月度最佳统计脚本 |

---

## 环境变量

| 变量 | 说明 |
|------|------|
| `BANGUMI_DUMP_DIR` | 归档目录（含 subject.jsonlines），默认 `./data` |
| `BANGUMI_APP_DATA_DIR` | xlsx 数据目录，默认项目根目录 |
