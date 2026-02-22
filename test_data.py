import json

from config import BANGUMI_DUMP_DIR, JSONL_FILE_NAME

# 数据目录：可通过环境变量 BANGUMI_DUMP_DIR 覆盖
JSONL_PATH = BANGUMI_DUMP_DIR / JSONL_FILE_NAME

# 待测试的条目 ID
TARGET_SUBJECT_ID = 326


def find_subject_data(jsonl_path, subject_id):
    """
    在 JSON Lines 文件中查找并打印指定 ID 的条目的完整原始 JSON 内容。
    """
    print(f"--- 1. 正在尝试从文件 {jsonl_path.name} 中查找条目 ID: {subject_id} ---")
    print(f"完整路径: {jsonl_path}")

    found_data = None

    try:
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    subject = json.loads(line)

                    # 注意: JSON 文件中的 id 通常是数字，但 subject.get() 可能会返回 None
                    current_id = subject.get('id')

                    if current_id == subject_id:
                        found_data = subject
                        break  # 找到后立即停止读取文件

                except json.JSONDecodeError:
                    # 忽略无法解析的行
                    continue

    except FileNotFoundError:
        print(f"\n❌ 严重错误: 文件未找到在 {jsonl_path}")
        return None
    except Exception as e:
        print(f"\n❌ 读取文件时发生错误: {e}")
        return None

    if found_data:
        print("\n=======================================================")
        print(f"✅ 找到条目 ID {subject_id} 的原始 JSON 数据:")
        print("=======================================================")
        # 使用 json.dumps 格式化输出，方便阅读
        print(json.dumps(found_data, ensure_ascii=False, indent=4))
        print("=======================================================")
    else:
        print(f"\n❌ 警告: 在文件中未找到条目 ID {subject_id} 的数据。")
        print("这可能意味着该条目不存在或 ID 不正确。")

    return found_data


if __name__ == '__main__':
    find_subject_data(JSONL_PATH, TARGET_SUBJECT_ID)
