import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import utils  # 导入我们之前编写的 utils 模块
import sys    # 用于获取脚本路径和执行参数
import ctypes # 用于调用 Windows API

class NicManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("网络适配器管理器")
        # self.root.geometry("600x450") # 可以稍微调大一点高度

        self.adapters_data = [] # 用来存储从 utils 获取的适配器信息

        # --- 检查管理员权限 ---
        # is_admin() 现在由 utils 提供
        self.is_admin = utils.is_admin()

        # --- 创建 GUI 控件 ---
        self.create_widgets()

        # --- 如果不是管理员，显示提示并提供重新启动按钮 ---
        if not self.is_admin:
            self.show_admin_prompt()
            # 禁用主要操作按钮
            self.enable_button.config(state=tk.DISABLED)
            self.disable_button.config(state=tk.DISABLED)
            self.status_var.set("警告：非管理员模式，无法进行启用/禁用操作。")
        else:
             # 如果已经是管理员，直接加载列表
             self.refresh_adapter_list()

    def create_widgets(self):
        # --- Frame for Admin Prompt (Initially hidden or empty) ---
        self.admin_prompt_frame = ttk.Frame(self.root, padding="5 0 5 10") # 上下留空，左边缩进
        self.admin_prompt_frame.pack(fill=tk.X)
        # 这个 frame 的内容将在 show_admin_prompt 中填充

        # --- Frame for Listbox and Scrollbar ---
        list_frame = ttk.Frame(self.root, padding="10 5 10 10") # 左右下 10，上 5
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.adapter_listbox = tk.Listbox(list_frame, height=15, width=80)
        self.adapter_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.adapter_listbox.bind('<<ListboxSelect>>', self.on_adapter_select)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.adapter_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.adapter_listbox.config(yscrollcommand=scrollbar.set)

        # --- Frame for Buttons ---
        button_frame = ttk.Frame(self.root, padding="10")
        button_frame.pack(fill=tk.X)

        self.enable_button = ttk.Button(
            button_frame, text="启用选中适配器", command=self.enable_selected_adapter, state=tk.DISABLED
        )
        self.enable_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.disable_button = ttk.Button(
            button_frame, text="禁用选中适配器", command=self.disable_selected_adapter, state=tk.DISABLED
        )
        self.disable_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.refresh_button = ttk.Button(
            button_frame, text="刷新列表", command=self.refresh_adapter_list
        )
        # 如果不是管理员，刷新按钮也可能意义不大，但可以保留
        # if not self.is_admin:
        #    self.refresh_button.config(state=tk.DISABLED)
        self.refresh_button.pack(side=tk.RIGHT, padx=5, pady=5)

        # --- Status Bar ---
        self.status_var = tk.StringVar()
        self.status_var.set("正在检查权限...")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, padding="2 5")
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def show_admin_prompt(self):
        """如果不是管理员，在顶部显示提示和重新运行按钮"""
        # 清空可能已有的旧内容
        for widget in self.admin_prompt_frame.winfo_children():
            widget.destroy()

        prompt_label = ttk.Label(
            self.admin_prompt_frame,
            text="需要管理员权限才能管理网络适配器。",
            foreground="red"
        )
        prompt_label.pack(side=tk.LEFT, padx=(0, 10)) # 右边留点空隙

        relaunch_button = ttk.Button(
            self.admin_prompt_frame,
            text="点击此处以管理员身份重新运行",
            command=self.relaunch_as_admin,
            style="Link.TButton" # 使用自定义样式模拟链接
        )
        relaunch_button.pack(side=tk.LEFT)

        # 定义一个简单的链接样式 (只改变前景色)
        style = ttk.Style()
        style.configure("Link.TButton", foreground="blue") #, font=('TkDefaultFont', 8, 'underline')) # 下划线字体可能不通用

    def relaunch_as_admin(self):
        """尝试以管理员权限重新启动当前脚本。"""
        try:
            script_path = sys.argv[0]
            python_executable = sys.executable # 获取当前运行的python解释器路径

            # 使用 ShellExecuteW 请求以管理员身份运行
            # 参数：
            # 0: hwnd (父窗口句柄，0表示无)
            # "runas": 操作谓词，表示请求管理员权限
            # python_executable: 要执行的程序
            # f'"{script_path}"': 传递给程序的参数 (脚本路径，加引号处理空格)
            # None: 工作目录 (使用默认)
            # 1: 显示命令 (SW_SHOWNORMAL)
            ret = ctypes.windll.shell32.ShellExecuteW(
                None, # hwnd
                "runas", # verb
                python_executable, # file
                f'"{script_path}"', # parameters
                None, # directory
                1 # show cmd (SW_SHOWNORMAL)
            )

            if ret > 32: # ShellExecuteW 成功时返回值大于 32
                # 关闭当前非管理员实例
                self.root.destroy() # 或者 sys.exit()
            else:
                # 处理常见的错误代码
                error_map = {
                    0: "内存不足",
                    2: "文件未找到 (Python解释器或脚本?)",
                    3: "路径未找到",
                    5: "访问被拒绝 (用户取消UAC或权限不足)",
                    8: "内存不足",
                    31: "没有关联的应用程序"
                 }
                error_message = f"尝试以管理员身份重新运行时出错。\n错误代码: {ret}\n"
                error_message += error_map.get(ret, "未知错误")
                messagebox.showerror("重新运行失败", error_message)

        except Exception as e:
            messagebox.showerror("重新运行失败", f"发生意外错误: {e}")

    def refresh_adapter_list(self):
        """获取最新的适配器列表并更新 Listbox"""
        self.status_var.set("正在刷新适配器列表...")
        self.root.update_idletasks() # 更新界面显示状态

        success, adapters_or_error = utils.get_network_adapters()

        self.adapter_listbox.delete(0, tk.END)
        self.adapters_data = []

        if success and isinstance(adapters_or_error, list):
            self.adapters_data = adapters_or_error
            if self.adapters_data:
                for i, adapter in enumerate(self.adapters_data):
                    display_text = f"{adapter['name']} ({adapter['status']})"
                    self.adapter_listbox.insert(tk.END, display_text)
                self.status_var.set("适配器列表已加载。请选择一项。")
            else:
                self.status_var.set("未找到网络适配器。")
                # 清空选择，重置按钮状态
                self.reset_button_states()
        else:
            error_msg = adapters_or_error if isinstance(adapters_or_error, str) else "获取适配器列表时发生未知错误。"
            messagebox.showerror("加载错误", f"无法获取网络适配器列表：\n{error_msg}")
            self.status_var.set("加载适配器列表失败！")
            self.reset_button_states()

        # 确保在非管理员模式下按钮保持禁用
        if not self.is_admin:
            self.enable_button.config(state=tk.DISABLED)
            self.disable_button.config(state=tk.DISABLED)

    def on_adapter_select(self, event=None):
        """当用户在 Listbox 中选择一项时触发"""
        selected_indices = self.adapter_listbox.curselection()
        if not selected_indices:
            self.reset_button_states()
            return

        selected_index = selected_indices[0]
        if 0 <= selected_index < len(self.adapters_data):
            selected_adapter = self.adapters_data[selected_index]
            self.status_var.set(f"已选择: {selected_adapter['name']}")

            # 只有在管理员模式下才更新按钮状态
            if self.is_admin:
                if selected_adapter['status'] == '已禁用':
                    self.enable_button.config(state=tk.NORMAL)
                    self.disable_button.config(state=tk.DISABLED)
                elif selected_adapter['status'] == '已启用':
                    self.enable_button.config(state=tk.DISABLED)
                    self.disable_button.config(state=tk.NORMAL)
                else:
                    self.reset_button_states()
            # else: 按钮保持禁用状态 (在 refresh_adapter_list 和 init 中已设置)
        else:
            self.reset_button_states()

    def reset_button_states(self):
        """重置启用/禁用按钮为禁用状态，并处理状态栏文本"""
        # 默认都禁用
        self.enable_button.config(state=tk.DISABLED)
        self.disable_button.config(state=tk.DISABLED)

        # 根据是否为管理员和是否有选择来更新状态栏
        if not self.is_admin:
             self.status_var.set("警告：非管理员模式，无法进行启用/禁用操作。")
        elif not self.adapter_listbox.curselection():
             if self.adapters_data: # 如果列表有数据但未选择
                 self.status_var.set("请选择一个适配器进行操作。")
             # else: 列表为空时，refresh_adapter_list 会设置状态
        # else: 有选择时，on_adapter_select 会设置状态

    def enable_selected_adapter(self):
        """启用当前选中的适配器 (仅当 is_admin 为 True 时才应可调用)"""
        if not self.is_admin: return # 双重保险

        selected_indices = self.adapter_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("未选择", "请先选择一个要启用的适配器。")
            return

        selected_index = selected_indices[0]
        if 0 <= selected_index < len(self.adapters_data):
            adapter_name = self.adapters_data[selected_index]['name']
            self.status_var.set(f"正在启用 '{adapter_name}'...")
            self.root.update_idletasks()

            success, message = utils.enable_adapter(adapter_name)

            if success:
                messagebox.showinfo("操作成功", message)
                self.refresh_adapter_list()
            else:
                messagebox.showerror("操作失败", message)
                self.status_var.set(f"启用 '{adapter_name}' 失败。")
        else:
             messagebox.showerror("错误", "选择索引无效。")

    def disable_selected_adapter(self):
        """禁用当前选中的适配器 (仅当 is_admin 为 True 时才应可调用)"""
        if not self.is_admin: return # 双重保险

        selected_indices = self.adapter_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("未选择", "请先选择一个要禁用的适配器。")
            return

        selected_index = selected_indices[0]
        if 0 <= selected_index < len(self.adapters_data):
            adapter_name = self.adapters_data[selected_index]['name']
            self.status_var.set(f"正在禁用 '{adapter_name}'...")
            self.root.update_idletasks()

            success, message = utils.disable_adapter(adapter_name)

            if success:
                messagebox.showinfo("操作成功", message)
                self.refresh_adapter_list()
            else:
                messagebox.showerror("操作失败", message)
                self.status_var.set(f"禁用 '{adapter_name}' 失败。")
        else:
            messagebox.showerror("错误", "选择索引无效。")

# --- 主程序入口 ---
if __name__ == "__main__":
    # DPI 感知设置保持不变
    try:
       from ctypes import windll
       windll.shcore.SetProcessDpiAwareness(1)
    except ImportError: pass # 忽略未安装 pypiwin32
    except AttributeError:
       try: windll.user32.SetProcessDPIAware()
       except AttributeError: pass # 忽略旧版 Windows 不支持
       except Exception: pass # 忽略其他 DPI 相关错误
    except Exception: pass

    root = tk.Tk()
    app = NicManagerApp(root)
    root.mainloop()
