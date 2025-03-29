# utils.py
import subprocess
import ctypes
import os
import platform
import locale
from typing import List, Dict, Tuple, Optional

# is_admin() 函数保持不变
def is_admin() -> bool:
    """
    检查当前脚本是否以管理员权限运行 (仅限Windows)。
    """
    try:
        if platform.system().lower() == 'windows':
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        else:
            return False
    except AttributeError:
        print("警告：无法检查管理员权限。假定非管理员运行。")
        return False
    except Exception as e:
        print(f"检查管理员权限时出错: {e}")
        return False

# --- 修改后的 _run_command 函数 ---
def _run_command(command: List[str]) -> Tuple[bool, str]:
    """
    执行一个外部命令并返回结果。优先使用 UTF-8 解码。

    Args:
        command (List[str]): 要执行的命令及其参数列表。

    Returns:
        Tuple[bool, str]: 一个元组，第一个元素表示是否成功 (True/False)，
                          第二个元素是命令的 stdout (成功时) 或 stderr (失败时)。
    """
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE

        result = subprocess.run(
            command,
            capture_output=True, # 获取原始字节
            check=False,
            startupinfo=startupinfo
        )

        stdout_bytes = result.stdout
        stderr_bytes = result.stderr
        output_decoded = ""
        error_decoded = ""

        # 尝试解码，优先 UTF-8
        encodings_to_try = list(dict.fromkeys(['utf-8', locale.getpreferredencoding(False), 'gbk', 'cp936']))

        # 解码 STDOUT
        for enc in encodings_to_try:
            try:
                output_decoded = stdout_bytes.decode(enc)
                if enc != 'utf-8':
                    print(f"提示：使用 '{enc}' 编码解码 STDOUT。") # 保留一个提示，如果不是UTF-8
                break # 成功则跳出
            except UnicodeDecodeError:
                continue # 失败则尝试下一个
            except Exception as e:
                print(f"解码 STDOUT 时出错 ({enc}): {e}")
                continue
        else: # 如果所有尝试都失败
            output_decoded = f"[无法解码 STDOUT: {stdout_bytes!r}]"

        # 解码 STDERR
        for enc in encodings_to_try:
            try:
                error_decoded = stderr_bytes.decode(enc)
                if enc != 'utf-8' and stderr_bytes: # 仅当stderr有内容且非utf-8时提示
                     print(f"提示：使用 '{enc}' 编码解码 STDERR。")
                break
            except UnicodeDecodeError:
                continue
            except Exception as e:
                print(f"解码 STDERR 时出错 ({enc}): {e}")
                continue
        else:
            error_decoded = f"[无法解码 STDERR: {stderr_bytes!r}]"

        if result.returncode == 0:
            return True, output_decoded.strip()
        else:
            # 优先返回 stderr，如果 stderr 为空，则返回 stdout
            error_message = error_decoded.strip() if error_decoded else output_decoded.strip()
            if not error_message: # 如果解码后的 stdout/stderr 都是空的
                error_message = f"命令执行失败，返回码: {result.returncode}"
            # 附加命令本身，方便调试
            error_message += f"\n执行的命令: {' '.join(command)}"
            return False, error_message

    except FileNotFoundError:
        return False, f"错误：命令 '{command[0]}' 未找到。请确保 'netsh' 在系统 PATH 中。"
    except Exception as e:
        # 捕获更广泛的异常
        return False, f"执行命令时发生意外错误: {e}\n执行的命令: {' '.join(command)}"

# get_network_adapters() 函数保持不变，它会接收 _run_command 返回的字符串
def get_network_adapters() -> Tuple[bool, List[Dict[str, str]] | str]:
    """
    获取系统上的网络适配器列表及其状态。
    """
    command = ["netsh", "interface", "show", "interface"]
    success, output = _run_command(command) # output 现在是尝试解码后的字符串

    if not success:
        # output 包含来自 _run_command 的错误信息
        return False, f"获取网络适配器列表失败: {output}"

    # --- 解析逻辑保持不变，但现在处理的是可能包含替换字符的字符串 ---
    adapters = []
    lines = output.splitlines()
    data_start_index = -1
    for i, line in enumerate(lines):
        if line.strip().startswith("---"):
            data_start_index = i + 1
            break

    if data_start_index == -1 or data_start_index >= len(lines):
        return False, "无法解析 'netsh interface show interface' 的输出格式 (可能解码不完全或格式意外)。"

    for line in lines[data_start_index:]:
        cleaned_line = line.strip()
        if not cleaned_line: # 跳过空行
            continue
        parts = cleaned_line.split()
        if len(parts) >= 4:
            try:
                admin_status = parts[0]
                # 改进名称提取：假设名字是最后一个可能包含空格的部分
                # 找到最后一个已知列（Type）的位置
                # 这个解析逻辑可能仍然脆弱，取决于netsh输出格式稳定性
                # 一个更健壮的方法可能是使用固定宽度或更智能的分割
                # 暂时使用之前的方法，看看解码后的字符串是否能正常工作
                state_part = parts[1]
                type_part = parts[2]

                # 简单拼接第三部分之后的所有内容作为名字
                name_parts = parts[3:]
                name = " ".join(name_parts).strip()

                # 另一种尝试：找到Type列在原始行中的结束位置
                try:
                    type_end_index = line.index(type_part) + len(type_part)
                    potential_name = line[type_end_index:].strip()
                    if potential_name: # 如果这种方法找到了名字，则优先使用
                        name = potential_name
                except ValueError:
                     # 如果找不到 type_part（例如，因为解码替换字符），则坚持使用之前的拼接方法
                     pass

                if name:
                    # 状态用 netsh 输出的原始值
                    adapters.append({
                        "name": name,
                        "status": admin_status # e.g., "Enabled", "Disabled"
                    })
                else:
                     print(f"警告：解析行时未能提取名称: '{cleaned_line}'")
            except Exception as parse_error:
                print(f"警告：解析行时出错 '{cleaned_line}': {parse_error}")
                continue
        else:
            print(f"警告：跳过格式不符的行: '{cleaned_line}'")

    if not adapters and output: # 如果解析后列表为空，但原始输出不为空
        print(f"警告：未能从以下输出中解析出任何适配器：\n{output}")
        # 可以考虑返回部分成功或特定错误

    return True, adapters

# _set_adapter_state, enable_adapter, disable_adapter 保持不变
def _set_adapter_state(adapter_name: str, state: str) -> Tuple[bool, str]:
    """内部函数，用于启用或禁用指定的网络适配器。"""
    if state not in ["enable", "disable"]:
        return False, "无效的状态，必须是 'enable' 或 'disable'"
    command = ["netsh", "interface", "set", "interface", f'name="{adapter_name}"', f"admin={state}"]
    success, output = _run_command(command)
    if success:
        # netsh 成功时通常没有重要输出，构建一个通用成功消息
        return True, f"适配器 '{adapter_name}' 操作 '{state}' 可能已成功。"
    else:
        return False, f"操作适配器 '{adapter_name}' 失败: {output}" # output 包含来自 _run_command 的错误

def enable_adapter(adapter_name: str) -> Tuple[bool, str]:
    """启用指定的网络适配器。"""
    return _set_adapter_state(adapter_name, "enable")

def disable_adapter(adapter_name: str) -> Tuple[bool, str]:
    """禁用指定的网络适配器。"""
    return _set_adapter_state(adapter_name, "disable")

# 主测试块保持不变
if __name__ == '__main__':
    print("正在执行 utils.py 作为主脚本进行测试...")
    # ... (其余测试代码不变) ...
    print("\n检查管理员权限:")
    is_admin_result = is_admin()
    print(f"是否为管理员: {is_admin_result}")
    if not is_admin_result:
        print("警告：许多功能（如启用/禁用网卡）需要管理员权限才能成功执行。")

    print("\n获取网络适配器:")
    success, adapters_or_error = get_network_adapters()

    if success:
        print("成功获取适配器列表 (或尝试解析):")
        if isinstance(adapters_or_error, list): # Type check for safety
             if adapters_or_error:
                 for adapter in adapters_or_error:
                     print(f"- 名称: {adapter['name']}, 状态: {adapter['status']}")
                 # 测试代码注释保持不变
             else:
                 print("未检测到或未能解析出任何网络适配器。")
        else:
             print("返回了意外的数据类型") # Should not happen

    else:
        print(f"获取适配器列表时出错:\n{adapters_or_error}")

    print("\nutils.py 测试结束。")