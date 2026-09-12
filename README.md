# Bangumi 综合数据分析平台

[![CI](https://github.com/xiaoyang-1607/bangumi-anime-dashboard/actions/workflows/ci.yml/badge.svg)](https://github.com/xiaoyang-1607/bangumi-anime-dashboard/actions/workflows/ci.yml)
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://bangumi-anime-dashboard-wvdgaakdmuyfd7s9v4ujj3.streamlit.app/)

一个基于 [Bangumi Archive](https://github.com/bangumi/Archive) 的 Streamlit 数据分析应用。它把归档中的动画和游戏条目清洗为可追溯的统一数据集，并提供名称、日期、评分、评分人数、标签、内容分级与排名筛选。

## 主要功能

- 顶部分区导航与榜单内页签，桌面端和移动端保持清晰的信息层级
- 首页收录量、评分人次和高口碑作品概览
- 当前筛选结果的指标、年份分布和热门标签分析
- 高分、热门、冷门佳作、近三年等快捷场景筛选
- 月份范围筛选、高级筛选表单、标签“全部/任一”匹配、条件反馈与一键重置
- 日期未知作品可选择纳入筛选；NSFW 内容默认隐藏并可显式切换
- 原始评分与动态经验贝叶斯修正分并列展示，同时标注评分样本量等级
- 对比上一期归档的 Bangumi 名次变化；首次基线明确显示“暂无对比”
- Bangumi 详情链接与当前结果 CSV 下载
- Parquet 快速读取优先，也可上传 Parquet 或 XLSX
- 数据生成、严格校验、质量报告与发布分离；默认不会自动提交或推送
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

仓库根目录包含应用直接读取的 `anime_cleaned.parquet`、`game_cleaned.parquet`，并保留相应 XLSX 供人工查看和兼容使用，因此启动后可以直接浏览。

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

运行 `python main.py --help` 可查看全部参数。可使用 `--as-of-date YYYY-MM-DD` 固定发行状态判断的基准日期。发布模式只会暂存本次生成的数据文件，不会把其他工作区改动带入提交。

### 一键获取最新归档

不需要手动下载和解压完整归档，下面的命令会查询 Bangumi Archive、选择时间戳最新的 zip、只提取 `subject.jsonlines`，然后生成并校验两个榜单和一份质量报告：

```bash
python update_data.py
```

更新器会在 `data_metadata.json` 记录已经处理的归档及清洗流程版本；只有归档和流程版本都未变化时才会跳过。若新榜单的数据量较上次异常下降超过 10%，自动任务会停止覆盖并要求人工核查。需要确认上游变更后强制重建时使用：

```bash
python update_data.py --force
```

归档目前超过 400 MiB，首次执行耗时取决于网络速度，但不会把下载文件保留在仓库中。

### GitHub 定时更新

`.github/workflows/update-data.yml` 每周三 00:30 UTC（北京时间 08:30）自动执行，也可以在 GitHub Actions 页面手动运行。流程会：

1. 获取最新 `dump-*.zip`；
2. 生成并校验动画、游戏 Parquet、兼容 XLSX 和 `data_quality_report.json`；
3. 运行全部回归测试；
4. 只有数据发生变化时才提交并推送 `main`。

工作流使用仓库自带的 `GITHUB_TOKEN`，无需额外配置密钥。如果仓库启用了禁止 Actions 写入或严格分支保护，需要在仓库设置中允许 GitHub Actions 写入内容，或改成 Pull Request 工作流。

## 数据格式

项目生成的 Parquet 和 XLSX 包含以下核心字段：

| 字段 | 含义 |
| --- | --- |
| `id` | Bangumi 条目 ID |
| `name` / `name_cn` | 原名 / 中文名 |
| `date` / `release_status` | 开播或发行日期 / 已发行、即将发行、日期未知 |
| `meta_tags` / `user_tags` | 元标签 / 经过最低使用次数过滤的用户标签 |
| `score` | Bangumi 评分 |
| `score_total` | 评分人数 |
| `rank` | 本期 Bangumi 原始排名 |
| `previous_rank` / `rank_change` / `rank_change_status` | 上期排名 / 名次增减数 / 上升、下降、持平、本期新增或暂无对比 |
| `favorite` / `favorite_*` | 各收藏状态计数及其总人数 |
| `nsfw` | 内容分级标记 |
| `bayesian_score` | 根据当前类别评分分布动态估计参数的经验贝叶斯修正分 |
| `score_confidence` | 按评分人数划分的低、中、高样本量等级 |

页面仍兼容只含基础字段的旧版上传文件；缺少必要列时会直接显示可操作的错误提示。

应用运行时以 Parquet 为主数据源，以保留日期、布尔值和数值类型并减少冷启动解析开销；XLSX 不再承担应用数据库职责，只用于人工查看、上传兼容和外部交换。日期原值仍精确到日，但界面筛选采用 `YYYY-MM` 月份范围，并完整包含结束月份。

### 动态经验贝叶斯评分

动画和游戏分别估计模型参数，不使用固定的先验票数。对同一类别的已上榜作品，先从 `score_details` 估计用户评分的合并组内方差 `σ²`，从作品原始评分估计总体观测方差 `s²`，再用矩估计得到作品之间的方差 `τ² = max(0, s² − 平均(σ²/nᵢ))`。类别均值 `μ` 为该类别作品原始评分的平均值。作品 `i` 的修正分为：

```text
wᵢ = τ² / (τ² + σ²/nᵢ)
bayesian_scoreᵢ = μ + wᵢ × (scoreᵢ − μ)
```

`nᵢ` 是作品评分人数。样本越多，修正分越接近原始评分；样本越少，越接近类别均值。`data_quality_report.json` 的 `score_model` 记录本期实际估计出的均值、组内方差、组间方差和仅供解释的“等效先验票数”，它不是写死的配置值。分数仅用于相对比较，不是概率或真实质量保证。

2026-09-08 归档估计出的等效先验票数约为动画 `1.59`、游戏 `1.82`。因此当前上榜数据的修正较轻；这套算法只修正评分抽样不稳定性，**不会额外奖励热门作品**。需要口碑与热度混合排名时，应另设独立指标，避免与修正评分混用。

### 名次变动

只比较同一作品在相邻两期不同归档中的 Bangumi 原始 `rank`，与筛选结果中的行序无关。定义 `rank_change = previous_rank − rank`：正数表示上升（如 `↑ +12`），负数表示下降（如 `↓ -5`），0 表示持平。上期榜单中没有的作品显示“本期新增”（并不保证 Bangumi 条目是本周新建的）；首次建立历史基线或无可信上期数据时显示“暂无对比”。同一归档因清洗流程升级而重新生成时，不会伪造名次变化。

本次代码升级使用仓库中 2026-09-01 归档的数据提交 `a1b5736`，为 2026-09-08 归档回填历史名次。需要对尚无名次对比的现有数据执行同类回填时，可以运行 `python update_data.py --backfill-ranks-from-git <上一期数据提交哈希>`；它只读取本地 Git 历史，不重复下载归档。后续每周自动更新会直接与更新前的数据文件比较。

榜单页默认使用“精简榜单”布局，突出名次变化、作品、日期、原始评分和修正评分；切换“完整数据”可查看上期排名、样本量等级、标签等字段。筛选栏保持快捷筛选与高级条件分层，手机端仍可收起侧栏。
表格用箭头展示变动方向，下载的 CSV 保留可计算的有符号 `rank_change` 数值。

### 清洗与榜单准入

清洗阶段会统一 Unicode、空白、名称回退和标签写法，并严格检查 ID、日期、评分分布、评分范围及重复条目。合法但未上榜、尚无评分的记录不会与坏数据混为一类，而是在质量报告中单独计数。已上榜但日期缺失的作品会保留为“日期未知”，未来日期会标记为“即将发行”。

`data_quality_report.json` 记录输入量、各类拒绝原因、非阻断警告、未知日期/未来作品/NSFW 数量、评分模型参数、名次变动汇总和最终榜单规模，便于追踪每次自动更新为何发生变化。

## 项目结构

| 路径 | 用途 |
| --- | --- |
| `app.py` | Streamlit 首页与跨类别概览 |
| `views/home.py` | 首页内容与探索入口 |
| `pages/` | 动画、游戏榜单页面 |
| `ranking_ui.py` | 数据校验、纯筛选函数与通用 UI |
| `ui.py` | 统一视觉主题、页头、侧边栏品牌与筛选条件标签 |
| `main.py` | 可配置的数据生成、校验与可选发布 CLI |
| `update_data.py` | 最新归档发现、流式下载、选择性解压与幂等更新 |
| `get_source.py` | JSONL 流式标准化、榜单准入、质量报告及 Parquet/XLSX 导出 |
| `config.py` | `.env` / 系统环境变量配置 |
| `tests/` | 数据处理与筛选回归测试 |

## 测试

```bash
python -m unittest discover -s tests -v
python -m compileall -q app.py best.py config.py get_source.py main.py ranking_ui.py ui.py update_data.py pages views tests
```

GitHub Actions 会在 Python 3.10 与 3.12 上执行相同检查。

## 环境变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `BANGUMI_DUMP_DIR` | `./data` | 包含 `subject.jsonlines` 的归档目录 |
| `BANGUMI_APP_DATA_DIR` | 项目根目录 | 页面读取和 CLI 输出榜单数据的目录 |

系统环境变量优先于 `.env`；`.env` 已加入 `.gitignore`，适合存放本机路径。
