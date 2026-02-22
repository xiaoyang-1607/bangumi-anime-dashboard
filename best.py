import pandas as pd

from config import BANGUMI_DUMP_DIR

# 数据目录：可通过环境变量 BANGUMI_DUMP_DIR 覆盖
folder_path = BANGUMI_DUMP_DIR
file_names = ['game_cleaned.xlsx', 'anime_cleaned.xlsx']

for file_name in file_names:
    file_path = folder_path / file_name

    if file_path.exists():
        df = pd.read_excel(file_path)

        # 1. 转换日期并提取年月 (不再进行 score_total >= 100 的筛选)
        df['date_dt'] = pd.to_datetime(df['date'], errors='coerce')
        # 过滤掉日期无效的行
        df = df[df['date_dt'].notna()].copy()
        df['year_month'] = df['date_dt'].dt.to_period('M')

        # 2. 预排序：按月份倒序，同月按分数倒序
        df_sorted = df.sort_values(
            by=['year_month', 'score_total'],
            ascending=[False, False]
        )

        # 3. 核心逻辑：找出所有存在的月份并检查断层
        # 这里的 all_months 是按时间从新到旧排列的唯一月份序列
        all_months = df_sorted['year_month'].unique()

        continuous_months = []
        if len(all_months) > 0:
            current_m = all_months[0]
            continuous_months.append(current_m)

            # 检查后续月份是否连续
            for i in range(1, len(all_months)):
                next_m = all_months[i]
                # 如果当前月份减去1个月不等于下一个月份，说明中间有断层
                if (current_m - 1) == next_m:
                    continuous_months.append(next_m)
                    current_m = next_m
                else:
                    # 发现断层，立即停止
                    break

        # 4. 只保留连续月份内的数据
        df_continuous = df_sorted[df_sorted['year_month'].isin(continuous_months)]

        # 5. 每个月只保留分数最高的一部作品
        result = df_continuous.drop_duplicates(subset=['year_month'], keep='first').copy()

        # 6. 格式化日期并清理辅助列
        result['date'] = result['date_dt'].dt.strftime('%Y-%m-%d')
        result = result.drop(columns=['date_dt', 'year_month'])

        # 7. 保存文件
        output_path = folder_path / f'monthly_best_{file_name}'
        result.to_excel(output_path, index=False)

        print(f"处理完成: {file_name}，共保留了 {len(result)} 个连续月份。")
    else:
        print(f"未找到文件: {file_path}")