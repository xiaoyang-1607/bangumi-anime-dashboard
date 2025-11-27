# 📺 Bangumi 动画排名数据分析 Dashboard

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://bangumi-anime-dashboard-wvdgaakdmuyfd7s9v4ujj3.streamlit.app/)

本项目是一个基于 Streamlit 框架构建的交互式数据分析面板，用于展示和筛选来自 Bangumi 归档数据库的动画作品排名和评分数据。

## ✨ 主要功能

本 Dashboard 提供灵活的侧边栏控件，帮助用户快速定位和分析感兴趣的动画作品：

* **名称搜索**: 支持按作品的**中文名**或**日文原名**进行模糊搜索。
* **精确日期筛选**: 可按 **年份** 和 **月份** 精确选择作品的开播时间范围。
* **评分范围筛选**: 通过滑块调整作品的 Bangumi 评分范围。
* **热度筛选**: 通过数字输入框设定作品的**最少评分人数**，过滤掉冷门作品。
* **多维度排序**: 支持按开播日期、评分、评分人数和 Bangumi 排名进行升序或降序排列。
* **快速链接**: 表格中的每一项都直接链接到 Bangumi 对应的作品页面。

## 🌐 在线使用

您可以直接通过以下链接访问和使用部署好的 Dashboard：

[**👉 前往 Bangumi 动画排名 Dashboard**](https://bangumi-anime-dashboard-wvdgaakdmuyfd7s9v4ujj3.streamlit.app/)

## 📊 数据信息

* **数据来源**: 原始数据来源于 Bangumi 归档数据库，经过清洗和预处理后用于本应用。
* **数据更新频率**: 一般情况下，数据会**每周更新一次**，以确保排名的时效性。

## 🛠️ 本地运行（针对开发者）

如果您想在本地运行或进一步开发此应用，请遵循以下步骤：

1.  **克隆仓库**:
    ```bash
    git clone [https://github.com/2817199948-byte/bangumi-anime-dashboard.git](https://github.com/2817199948-byte/bangumi-anime-dashboard.git)
    cd bangumi-anime-dashboard
    ```

2.  **安装依赖**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **准备数据**:
    将数据文件 `anime_cleaned.xlsx` (或其他对应格式) 放入项目根目录。

4.  **运行应用**:
    ```bash
    streamlit run app.py
    ```

应用将自动在您的浏览器中打开 (`http://localhost:8501`)。
