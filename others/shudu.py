def find_empty_location(board):
    """查找数独板上第一个空白单元格 (用 0 表示)。"""
    for r in range(9):
        for c in range(9):
            if board[r][c] == 0:
                return r, c
    return None


def is_safe(board, row, col, num):
    """检查在给定位置放置数字 num 是否合法。"""
    # 检查行
    if num in board[row]:
        return False

    # 检查列
    for r in range(9):
        if board[r][col] == num:
            return False

    # 检查 3x3 小九宫格
    start_row = row - row % 3
    start_col = col - col % 3
    for r in range(3):
        for c in range(3):
            if board[start_row + r][start_col + c] == num:
                return False

    return True


def solve_sudoku(board):
    """使用回溯法解决数独。这是核心的递归函数。"""
    empty_pos = find_empty_location(board)
    if not empty_pos:
        return True

    row, col = empty_pos

    for num in range(1, 10):
        if is_safe(board, row, col, num):
            board[row][col] = num
            if solve_sudoku(board):
                return True

            # 回溯
            board[row][col] = 0

    return False


def print_board(board):
    """以易于阅读的格式打印数独板。"""
    for r in range(9):
        if r % 3 == 0 and r != 0:
            print("- - - - - - - - - - - - ")

        for c in range(9):
            if c % 3 == 0 and c != 0:
                print(" | ", end="")

            # 将 0 显示为空格，更美观
            display_char = str(board[r][c]) if board[r][c] != 0 else " "

            if c == 8:
                print(display_char)
            else:
                print(display_char + " ", end="")


def get_user_input():
    """引导用户输入 9x9 数独谜题。"""
    print("=======================================")
    print("🔢 请输入 9x9 数独谜题，空缺处请使用 '0' 代替。")
    print("   请按行输入，每行 9 个数字，数字之间无需空格。")
    print("   示例输入 (第1行): 530070000")
    print("=======================================")

    puzzle = []

    for i in range(9):
        while True:
            try:
                line_input = input(f"请输入第 {i + 1} 行 (9个数字): ")

                # 检查长度
                if len(line_input) != 9:
                    print("⚠️ 错误：每行必须输入 9 个数字。请重试。")
                    continue

                # 转换并检查数字范围
                row = [int(c) for c in line_input]
                if any(c < 0 or c > 9 for c in row):
                    print("⚠️ 错误：数字必须在 0 到 9 之间。请重试。")
                    continue

                puzzle.append(row)
                break

            except ValueError:
                print("⚠️ 错误：输入中包含非数字字符。请重试。")
            except EOFError:
                # 处理某些环境下的输入结束问题
                print("\n输入提前结束。")
                return None

    return puzzle


# --- 主程序执行部分 ---
if __name__ == "__main__":
    initial_puzzle = get_user_input()

    if initial_puzzle and len(initial_puzzle) == 9:
        print("\n📝 您输入的谜题是:")
        print_board(initial_puzzle)
        print("\n" + "=" * 20 + "\n")

        # 验证初始谜题是否合法（可选：可以添加一个 is_valid_sudoku_start 检查）
        # 简单起见，我们直接尝试解决

        if solve_sudoku(initial_puzzle):
            print("✅ 数独已解决:")
            print_board(initial_puzzle)
        else:
            print("❌ 无法解决此数独。请检查您的初始输入是否合法或有解。")
    elif initial_puzzle:
        print("\n❌ 输入的行数不正确，必须是 9 行。")
    else:
        print("\n程序终止。")
