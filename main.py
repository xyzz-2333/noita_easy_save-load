import tkinter as tk
from tkinter import ttk, messagebox
import shutil
import os
import datetime
import threading
from pathlib import Path

# ================= 配置 =================
NOITA_SAVE_PATH = Path.home() / "AppData" / "LocalLow" / "Nolla_Games_Noita" / "save00"
BACKUP_DIR = Path(__file__).parent / "backups"
BACKUP_DIR.mkdir(exist_ok=True)

# 高 DPI 优化（Windows 高分辨率模糊问题）
try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)  # 1 = 系统 DPI 感知（推荐）
except:
    pass  # 非 Windows 或失败就跳过

def get_timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")

def get_dir_size(path):
    """计算文件夹总大小，返回友好字符串"""
    if not path.exists():
        return "0 B"
    total = 0
    try:
        for dirpath, _, filenames in os.walk(path):
            for f in filenames:
                fp = Path(dirpath) / f
                if fp.is_file():
                    total += fp.stat().st_size
    except:
        return "~错误"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if total < 1024:
            return f"{total:.1f} {unit}" if unit != 'B' else f"{int(total)} {unit}"
        total /= 1024
    return f"{total:.1f} PB"

def get_backup_list():
    backups = []
    for item in BACKUP_DIR.iterdir():
        if item.is_dir() and (item.name.endswith("_full") or item.name.endswith("_world")):
            timestamp_part = item.name.split("_", 2)[:2]
            time_str = f"{timestamp_part[0]} {timestamp_part[1].replace('-', ':')}"
            size_str = get_dir_size(item)
            typ = "完整" if item.name.endswith("_full") else "仅世界"
            backups.append((item.name, typ, time_str, size_str))
    backups.sort(reverse=True)  # 最新在上
    return backups

def refresh_list():
    listbox.delete(0, tk.END)
    for name, typ, time_str, size_str in get_backup_list():
        listbox.insert(tk.END, f"[{typ}] {time_str}  {size_str}  -  {name}")

# ================= 带进度条的复制函数 =================
def copy_with_progress(src, dst, progress_bar, status_label, callback):
    def do_copy():
        try:
            total_files = sum(len(files) for _, _, files in os.walk(src))
            copied = 0

            def copy_item(src_item, dst_item):
                nonlocal copied
                if os.path.isfile(src_item):
                    shutil.copy2(src_item, dst_item)
                elif os.path.isdir(src_item):
                    os.makedirs(dst_item, exist_ok=True)
                    for item in os.listdir(src_item):
                        copy_item(os.path.join(src_item, item), os.path.join(dst_item, item))
                copied += 1
                if total_files > 0:
                    progress_bar['value'] = (copied / total_files) * 100
                status_label.config(text=f"处理中... {copied}/{total_files} 文件")

            if src.is_dir() and not dst.exists():
                os.makedirs(dst.parent, exist_ok=True)

            copy_item(src, dst)

            root.after(0, lambda: [
                progress_bar.stop(),
                progress_bar.pack_forget(),
                status_label.config(text=""),
                callback(True, "完成")
            ])
        except Exception as e:
            root.after(0, lambda: [
                progress_bar.stop(),
                progress_bar.pack_forget(),
                status_label.config(text=""),
                callback(False, str(e))
            ])

    progress_bar.pack(pady=5, fill=tk.X, padx=20)
    progress_bar.start(10)
    status_label.config(text="准备中...")
    threading.Thread(target=do_copy, daemon=True).start()

# ================= 操作函数 =================
def save_backup(mode="full"):
    if not NOITA_SAVE_PATH.exists():
        messagebox.showerror("错误", "Noita save00 不存在！请先运行游戏创建存档。")
        return

    timestamp = get_timestamp()
    backup_name = f"{timestamp}_{mode}"
    target = BACKUP_DIR / backup_name

    def on_finish(success, msg):
        if success:
            messagebox.showinfo("成功", f"已保存：{backup_name}")
            refresh_list()
        else:
            messagebox.showerror("保存失败", msg)

    if mode == "full":
        copy_with_progress(NOITA_SAVE_PATH, target, progress, status_lbl, on_finish)
    else:
        copy_with_progress(NOITA_SAVE_PATH / "world", target / "world", progress, status_lbl, on_finish)

def restore_selected():
    sel = listbox.curselection()
    if not sel:
        messagebox.showwarning("提示", "请先选择一个存档")
        return

    idx = sel[0]
    name, typ, _, _ = get_backup_list()[idx]
    backup_path = BACKUP_DIR / name

    if messagebox.askyesno("确认", f"恢复 {name} ({typ})？") == tk.NO:
        return

    def on_finish(success, msg):
        if success:
            msg = "世界存档已恢复！" if typ == "仅世界" else f"完整存档已恢复！\n当前存档已自动备份"
            messagebox.showinfo("成功", msg)
            refresh_list()
        else:
            messagebox.showerror("恢复失败", msg)

    if typ == "仅世界":
        target_world = NOITA_SAVE_PATH / "world"
        if target_world.exists():
            shutil.rmtree(target_world)
        copy_with_progress(backup_path / "world", target_world, progress, status_lbl, on_finish)
    else:
        # 先备份当前
        current_name = f"{get_timestamp()}_before_restore"
        current_path = BACKUP_DIR / current_name
        copy_with_progress(NOITA_SAVE_PATH, current_path, progress, status_lbl, lambda s, m: None)

        # 再覆盖目标
        if NOITA_SAVE_PATH.exists():
            shutil.rmtree(NOITA_SAVE_PATH)
        copy_with_progress(backup_path, NOITA_SAVE_PATH, progress, status_lbl, on_finish)

def delete_selected():
    sel = listbox.curselection()
    if not sel:
        return
    idx = sel[0]
    name, _, _, _ = get_backup_list()[idx]

    if messagebox.askyesno("删除确认", f"删除 {name}？（不可恢复）") == tk.YES:
        try:
            shutil.rmtree(BACKUP_DIR / name)
            messagebox.showinfo("已删除", f"{name} 已删除")
            refresh_list()
        except Exception as e:
            messagebox.showerror("删除失败", str(e))

# ================= GUI =================
root = tk.Tk()
root.title("Noita 存档工具")
root.geometry("1170x790")
root.configure(bg="white")

# 高 DPI 优化已在上方

# 全局字体 fallback（可选，但保持一致）
root.option_add("*Background", "white")
root.option_add("*Foreground", "black")
# root.option_add("*Font", ("Segoe UI", 11))  # 如果想全局小字体，可以开这行

# 标题
tk.Label(root, text="Noita 存档管理", 
         font=("Segoe UI", 16, "bold"), bg="white").pack(pady=15)

frame_btn = tk.Frame(root, bg="white")
frame_btn.pack(pady=15)

# 统一按钮样式：字体大小一致 + width 以字符计 + height 行数
BTN_FONT = ("Segoe UI", 13, "bold")   # 统一 13 bold，看起来大气又不夸张
BTN_WIDTH = 16                        # 字符宽度，够放“保存完整存档”
BTN_HEIGHT = 2                      # 行高
BTN_PADX = 10                        # 额外内边距
BTN_PADY = 8

btn_full = tk.Button(frame_btn, text="保存完整存档", 
                     font=BTN_FONT, width=BTN_WIDTH, height=BTN_HEIGHT,
                     command=lambda: save_backup("full"), 
                     bg="#e8f0fe", relief="flat", bd=1,
                     padx=BTN_PADX, pady=BTN_PADY)
btn_full.pack(side=tk.LEFT, padx=30)

btn_world = tk.Button(frame_btn, text="仅保存世界", 
                      font=BTN_FONT, width=BTN_WIDTH, height=BTN_HEIGHT,
                      command=lambda: save_backup("world"), 
                      bg="#e8f0fe", relief="flat", bd=1,
                      padx=BTN_PADX, pady=BTN_PADY)
btn_world.pack(side=tk.LEFT, padx=30)

# 已保存存档标签
tk.Label(root, text="已保存存档（最新在上）", 
         font=("Segoe UI", 12, "bold"), bg="white").pack(pady=8)

listbox_frame = tk.Frame(root, bg="white")
listbox_frame.pack(fill=tk.BOTH, expand=True, padx=25, pady=5)

listbox = tk.Listbox(listbox_frame, font=("Consolas", 11), height=12, width=65, selectmode=tk.SINGLE,
                     bg="#f8f9fa", relief="flat", bd=1, highlightthickness=1, highlightbackground="#d0d0d0")
listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

scroll = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=listbox.yview)
scroll.pack(side=tk.RIGHT, fill=tk.Y)
listbox.config(yscrollcommand=scroll.set)

progress = ttk.Progressbar(root, mode='indeterminate', length=480)
status_lbl = tk.Label(root, text="", bg="white", fg="#666", font=("Segoe UI", 10))

status_lbl.pack(pady=3)

frame_op = tk.Frame(root, bg="white")
frame_op.pack(pady=20)

# 操作按钮也统一大小（稍小一点，但和上面风格一致）
OP_BTN_FONT = ("Segoe UI", 12, "bold")
OP_BTN_WIDTH = 16
OP_BTN_HEIGHT = 2

btn_restore = tk.Button(frame_op, text="恢复选中存档", 
                        font=OP_BTN_FONT, width=OP_BTN_WIDTH, height=OP_BTN_HEIGHT,
                        command=restore_selected, bg="#cce5ff", relief="flat", bd=1,
                        padx=BTN_PADX, pady=BTN_PADY)
btn_restore.pack(side=tk.LEFT, padx=25)

btn_delete = tk.Button(frame_op, text="删除选中存档", 
                       font=OP_BTN_FONT, width=OP_BTN_WIDTH, height=OP_BTN_HEIGHT,
                       command=delete_selected, bg="#ffebee", relief="flat", bd=1,
                       padx=BTN_PADX, pady=BTN_PADY)
btn_delete.pack(side=tk.LEFT, padx=25)

refresh_list()

root.mainloop()