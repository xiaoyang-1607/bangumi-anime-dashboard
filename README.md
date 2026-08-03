# Bangumi 综合数据分析平台

[![CI](https://github.com/xiaoyang-1607/bangumi-anime-dashboard/actions/workflows/ci.yml/badge.svg)](https://github.com/xiaoyang-1607/bangumi-anime-dashboard/actions/workflows/ci.yml)
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://bangumi-anime-dashboard-wvdgaakdmuyfd7s9v4ujj3.streamlit.app/)

一个基于 [Bangumi Archive](https://github.com/bangumi/Archive) 的 Streamlit 数据分析应用。它把归档中的动画和游戏条目清洗为统一数据集，并提供名称、日期、评分、评分人数、标签与排名筛选。

## 主要功能

- 动画榜单与游戏榜单，共用一致的筛选和排序体验
- 首页收录量、评分人次和高口碑作品概览
- 当前筛选结果的指标、年份分布和热门标签分析
- 精确标签组合筛选、Bangumi 详情链接、CSV 结果下载
- 本地文件优先，也可在页面上传标准 xlsx
- 数据生成、校验与发布分离；默认不会自动提交或推送
- 每周自动检查最新 Bangumi Archive，仅在数据变化时提交新榜单

## 快速开始

推荐 Python 3.10 或更高版本。

```bash
git clone https://github.com/xiaoyang-1607/bangumi-anime-dashboard.git
cd bangumi-anime-dashboard
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

macOS / Linux 激活虚拟环境时使用 `source .venv/bin/activate`。

仓库根目录已经包含 `anime_cleaned.xlsx` 与 `game_cleaned.xlsx`，因此启动后可以直接浏览。

## 更新数据

1. 从 [Bangumi Archive Releases](https://github.com/bangumi/Archive/releases) 下载并解压最新归档。
2. 复制 `.env.example` 为 `.env`，配置归档路径：

```dotenv
BANGUMI_DUMP_DIR=D:\data\dump-2026-08-01
BANGUMI_APP_DATA_DIR=.
```

3. 生成并校验数据：

```bash
python main.py
```

常用参数：

```bash
# 不使用 .env，临时指定输入输出目录
python main.py --dump-dir D:\data\bangumi-dump --output-dir .

# 同时在归档目录保存一份结果
python main.py --also-save-to-dump

# 生成成功后才提交并推送当前分支（这是显式操作）
python main.py --publish

# 指定推送目标
python main.py --publish --remote origin --branch main
```

运行 `python main.py --help` 可查看全部参数。发布模式只会暂存两个生成的数据文件，不会把其他工作区改动带入提交。

### 一键获取最新归档

不需要手动下载和解压完整归档，下面的命令会查询 Bangumi Archive、选择时间戳最新的 zip、只提取 `subject.jsonlines`，然后生成并校验两个榜单：

```bash
python update_data.py
```

更新器会在 `data_metadata.json` 记录已经处理的归档；再次运行时如果远端资源未变化，会直接跳过。需要强制重建时使用：

```bash
python update_data.py --force
```

归档目前超过 400 MiB，首次执行耗时取决于网络速度，但不会把下载文件保留在仓库中。

### GitHub 定时更新

`.github/workflows/update-data.yml` 每周三 00:30 UTC（北京时间 08:30）自动执行，也可以在 GitHub Actions 页面手动运行。流程会：

1. 获取最新 `dump-*.zip`；
2. 生成并校验动画、游戏 Excel；
3. 运行全部回归测试；
4. 只有数据发生变化时才提交并推送 `main`。

工作流使用仓库自带的 `GITHUB_TOKEN`，无需额外配置密钥。如果仓库启用了禁止 Actions 写入或严格分支保护，需要在仓库设置中允许 GitHub Actions 写入内容，或改成 Pull Request 工作流。

## 数据格式

页面要求 Excel 至少包含以下字段：

| 字段 | 含义 |
| --- | --- |
| `id` | Bangumi 条目 ID |
| `name` / `name_cn` | 原名 / 中文名 |
| `date` | 开播或发行日期 |
| `meta_tags` | 逗号分隔标签 |
| `score` | Bangumi 评分 |
| `score_total` | 评分人数 |
| `rank` | Bangumi 排名 |

上传文件缺少必要列时，页面会直接显示可操作的错误提示。

## 项目结构

| 路径 | 用途 |
| --- | --- |
| `app.py` | Streamlit 首页与跨类别概览 |
| `pages/` | 动画、游戏榜单页面 |
| `ranking_ui.py` | 数据校验、纯筛选函数与通用 UI |
| `main.py` | 可配置的数据生成、校验与可选发布 CLI |
| `update_data.py` | 最新归档发现、流式下载、选择性解压与幂等更新 |
| `get_source.py` | JSONL 流式清洗与 Excel 导出 |
| `config.py` | `.env` / 系统环境变量配置 |
| `tests/` | 数据处理与筛选回归测试 |

## 测试

```bash
python -m unittest discover -s tests -v
python -m compileall -q app.py config.py get_source.py main.py ranking_ui.py update_data.py pages tests
```

GitHub Actions 会在 Python 3.10 与 3.12 上执行相同检查。

## 环境变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `BANGUMI_DUMP_DIR` | `./data` | 包含 `subject.jsonlines` 的归档目录 |
| `BANGUMI_APP_DATA_DIR` | 项目根目录 | 页面读取和 CLI 输出榜单数据的目录 |

系统环境变量优先于 `.env`；`.env` 已加入 `.gitignore`，适合存放本机路径。
