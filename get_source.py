import json
import pandas as pd
from pathlib import Path

from config import BANGUMI_DUMP_DIR, JSONL_FILE_NAME

# --- 配置：可通过环境变量 BANGUMI_DUMP_DIR 覆盖 ---
JSONL_PATH = BANGUMI_DUMP_DIR / JSONL_FILE_NAME

# Define the numerical IDs for Anime and Game (based on the provided document)
TYPE_ANIME = 2
TYPE_GAME = 4

# Target output Excel files (used in both export and formatting steps)
ANIME_OUTPUT_FILE = BANGUMI_DUMP_DIR / 'bangumi_anime_data.xlsx'
GAME_OUTPUT_FILE = BANGUMI_DUMP_DIR / 'bangumi_game_data.xlsx'

# Date column to format
DATE_COLUMN_NAME = 'date'

# Explicit Excel date format (only date, no time)
EXCEL_DATE_FORMAT = 'yyyy-mm-dd'

# --- End Configuration ---

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
        with open(jsonl_path, 'r', encoding='utf-8') as f:
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
        print(f"✓ 成功导出文件: {output_path.name}")
        return True
    except Exception as e:
        print(f"✗ 导出数据到 Excel 错误: {e}")
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
        # 1. 读取 Excel 文件
        df = pd.read_excel(file_path, engine='openpyxl')

        if column_name not in df.columns:
            print(f"警告: 文件中未找到列名 '{column_name}'，跳过日期格式修复。")
            return

        # 2. 将字符串转换为 Pandas datetime 对象 (时间部分默认为 00:00:00)
        # errors='coerce' 会将无法转换的值设为 NaT (Not a Time)
        df[column_name] = pd.to_datetime(df[column_name], errors='coerce')

        # 3. 使用 ExcelWriter (xlsxwriter engine) 来设置日期格式并保存
        # 'openpyxl' engine does not support formatting, so we re-write the file with 'xlsxwriter'
        writer = pd.ExcelWriter(file_path, engine='xlsxwriter', datetime_format=date_format)

        # 将 DataFrame 写入工作表
        # We use a default sheet name 'Sheet1' since 'to_excel' was used in the previous step
        df.to_excel(writer, index=False, sheet_name='Sheet1')

        # 保存并关闭文件
        # This operation overwrites the original file
        writer.close()

        print(f"✓ 文件 {file_base_name} 中的 '{column_name}' 列已成功转换为日期格式 ({date_format}) 并保存。")

    except Exception as e:
        print(f"✗ 修复文件 {file_base_name} 的日期格式时发生错误: {e}")


def main():
    """
    Main execution function: Process data, export to Excel, and apply date formatting.
    """
    # 1. Process the JSONL data
    anime_data, game_data = process_subject_data(JSONL_PATH)

    if anime_data is None and game_data is None:
        print("\nProcess halted due to critical data processing error(s).")
        return

    # 2. Export Data to Excel
    print("\n--- 阶段 2: 导出 Excel 文件 ---")
    anime_exported = export_to_excel(anime_data, ANIME_OUTPUT_FILE, 'Anime_Subjects')
    game_exported = export_to_excel(game_data, GAME_OUTPUT_FILE, 'Game_Subjects')

    # 3. Apply Date Formatting to the exported files
    print("\n--- 阶段 3: 修复 Excel 日期格式 ---")
    if anime_exported:
        apply_excel_date_format(ANIME_OUTPUT_FILE, DATE_COLUMN_NAME, EXCEL_DATE_FORMAT)

    if game_exported:
        apply_excel_date_format(GAME_OUTPUT_FILE, DATE_COLUMN_NAME, EXCEL_DATE_FORMAT)

    print("\n=====================================")
    print("✅ 所有提取、导出和格式化操作已完成。")
    print(f"动画数据文件: {ANIME_OUTPUT_FILE}")
    print(f"游戏数据文件: {GAME_OUTPUT_FILE}")
    print("=====================================")


if __name__ == '__main__':
    main()
