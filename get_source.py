import json
import pandas as pd
from pathlib import Path

# 类型 ID（Bangumi 归档）
TYPE_ANIME = 2
TYPE_GAME = 4

# 日期列与 Excel 日期格式
DATE_COLUMN_NAME = 'date'
EXCEL_DATE_FORMAT = 'yyyy-mm-dd'

def process_subject_data(jsonl_path):
    """
    Reads the subject.jsonlines file, processes each entry, and filters them
    into separate lists for anime and game, excluding rank 0 entries.
    """
    anime_data_list = []
    game_data_list = []

    print(f"--- 1. 数据处理: 正在读取文件: {jsonl_path} ---")

    # 用于统计跳过的条目数量
    skipped_count = 0

    try:
        with open(jsonl_path, 'r', encoding='utf-8-sig') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    subject = json.loads(line)

                    # 1. 排除标准: 跳过 rank 0 的条目
                    if subject.get('rank') == 0:
                        continue

                    # 2. 如果 date 为空，跳过该条目
                    subject_date = subject.get('date')
                    if not subject_date:
                        skipped_count += 1
                        continue

                    # 3. 如果 name_cn 为空，使用 name 填充
                    subject_name_cn = subject.get('name_cn')
                    subject_name = subject.get('name')
                    if not subject_name_cn and subject_name:
                        subject_name_cn = subject_name

                    # 计算 score_total
                    score_details = subject.get('score_details', {})
                    score_total = sum(score_details.values()) if score_details else 0

                    # 处理 'tags' 字段 (list of dictionaries -> comma-separated string)
                    raw_tags = subject.get('meta_tags', [])
                    tag_names = [str(tag) for tag in raw_tags]

                    # 4. 提取和处理数据:
                    processed_subject = {
                        'id': subject.get('id'),
                        'name': subject_name,
                        'name_cn': subject_name_cn,
                        'date': subject_date,
                        'meta_tags': ', '.join(tag_names),
                        'score': subject.get('score'),
                        'score_total': score_total,
                        'rank': subject.get('rank'),
                    }

                    # 5. 分类: 检查 'type' 字段
                    subject_type = subject.get('type')

                    if subject_type == TYPE_ANIME:
                        anime_data_list.append(processed_subject)
                    elif subject_type == TYPE_GAME:
                        game_data_list.append(processed_subject)

                except json.JSONDecodeError as e:
                    print(f"警告: Line {line_num} JSON 解码错误: {e}. 跳过该行。")
                except Exception as e:
                    print(f"警告: Line {line_num} 发生意外错误: {e}. 跳过该行。")

    except FileNotFoundError:
        print(f"严重错误: 文件未找到在 {jsonl_path}")
        return None, None
    except Exception as e:
        print(f"读取文件时发生错误: {e}")
        return None, None

    print(f"数据处理完成。已跳过 {skipped_count} 条 date 为空的条目。")
    print(f"找到 {len(anime_data_list)} 条动画数据和 {len(game_data_list)} 条游戏数据。")
    return anime_data_list, game_data_list


def export_to_excel(data_list, output_path, sheet_name):
    """
    Converts a list of dictionaries into a pandas DataFrame and exports it to an Excel file.
    """
    if not data_list:
        print(f"--- 2. 数据导出: 没有 '{sheet_name}' 数据可供导出。跳过。")
        return False

    print(f"--- 2. 数据导出: 正在导出 {len(data_list)} 条记录到 {output_path.name} ---")
    try:
        df = pd.DataFrame(data_list)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Export as is for now; date formatting will happen in the next step
        df.to_excel(output_path, index=False, sheet_name=sheet_name, engine='xlsxwriter')
        print(f"[OK] 成功导出文件: {output_path.name}")
        return True
    except Exception as e:
        print(f"[ERROR] 导出数据到 Excel 错误: {e}")
        return False


def apply_excel_date_format(file_path: Path, column_name: str, date_format: str):
    """
    Reads an Excel file, converts the specified column to datetime objects, and
    saves the file with a specific Excel date format applied to that column.
    Uses 'openpyxl' for reading and 'xlsxwriter' for writing/formatting.
    """
    file_base_name = file_path.name
    print(f"--- 3. 格式修复: 正在处理文件: {file_base_name} ---")

    if not file_path.exists():
        print(f"警告: 文件未找到，无法进行日期格式修复: {file_base_name}")
        return

    try:
        # 1. 读取 Excel 文件（保留首 sheet 名称以便写回时一致）
        with pd.ExcelFile(file_path, engine='openpyxl') as xl:
            sheet_name = xl.sheet_names[0]
            df = pd.read_excel(xl, sheet_name=sheet_name)

        if column_name not in df.columns:
            print(f"警告: 文件中未找到列名 '{column_name}'，跳过日期格式修复。")
            return

        # 2. 将字符串转换为 Pandas datetime 对象 (时间部分默认为 00:00:00)
        # errors='coerce' 会将无法转换的值设为 NaT (Not a Time)
        df[column_name] = pd.to_datetime(df[column_name], errors='coerce')

        # 3. 使用 ExcelWriter (xlsxwriter engine) 来设置日期格式并保存
        # 'openpyxl' engine does not support formatting, so we re-write the file with 'xlsxwriter'
        writer = pd.ExcelWriter(file_path, engine='xlsxwriter', datetime_format=date_format)

        # 写回时使用原 sheet 名称，与 export_to_excel 的 Anime_Subjects / Game_Subjects 一致
        df.to_excel(writer, index=False, sheet_name=sheet_name)

        # 保存并关闭文件
        # This operation overwrites the original file
        writer.close()

        print(f"[OK] 文件 {file_base_name} 中的 '{column_name}' 列已成功转换为日期格式 ({date_format}) 并保存。")

    except Exception as e:
        print(f"[ERROR] 修复文件 {file_base_name} 的日期格式时发生错误: {e}")


