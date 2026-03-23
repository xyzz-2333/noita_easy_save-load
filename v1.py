import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import shutil
import os
import datetime
from pathlib import Path

# ================= 配置 =================
NOITA_SAVE_PATH = Path.home() / "AppData" / "LocalLow" / "Nolla_Games_Noita" / "save00"
BACKUP_DIR = Path(__file__).parent / "backups"

BACKUP_DIR.mkdir(exist_ok=True)

def get_timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")

def get_backup_list():
    backups = []
    for item in BACKUP_DIR.iterdir():
        if item.is_dir():
            name = item.name
            if name.endswith("_full") or name.endswith("_world"):
                time_part = name.split("_", 2)[0:2]
                time_str = f"{time_part[0]} {time_part[1].replace('-', ':')}"
                backups.append((name, "完整" if name.endswith("_full") else "仅世界", time_str))
    backups.sort(reverse=True)  # 最新在上
    return backups

def refresh_list():
    listbox.delete(0, tk.END)
    for name, typ, time_str in get_backup_list():
        listbox.insert(tk.END, f"[{typ}] {time_str}  -  {name}")

def save_backup(mode="full"):  # mode: "full" 或 "world"
    if not NOITA_SAVE_PATH.exists():
        messagebox.showerror("错误", "Noita save00 文件夹不存在！\n请确认游戏已创建存档。")
        return

    timestamp = get_timestamp()
    backup_name = f"{timestamp}_{mode}"
    target = BACKUP_DIR / backup_name

    try:
        if mode == "full":
            shutil.copytree(NOITA_SAVE_PATH, target)
        else:  # world only
            shutil.copytree(NOITA_SAVE_PATH / "world", target / "world", dirs_exist_ok=True)
        messagebox.showinfo("成功", f"已保存：{backup_name}")
        refresh_list()
    except Exception as e:
        messagebox.showerror("保存失败", str(e))

def restore_selected():
    sel = listbox.curselection()
    if not sel:
        messagebox.showwarning("提示", "请先选择一个存档")
        return

    idx = sel[0]
    name, typ, _ = get_backup_list()[idx]
    backup_path = BACKUP_DIR / name

    if not backup_path.exists():
        messagebox.showerror("错误", "备份文件夹丢失？")
        return

    if messagebox.askyesno("确认恢复", f"确定要恢复\n{name}\n({typ})？\n\n注意：完整存档会先备份当前存档") == tk.NO:
        return

    try:
        if typ == "仅世界":
            # 直接覆盖 world
            target_world = NOITA_SAVE_PATH / "world"
            if target_world.exists():
                shutil.rmtree(target_world)
            shutil.copytree(backup_path / "world", target_world)
            messagebox.showinfo("成功", "世界存档已恢复！")
        else:
            # 完整存档：先备份当前
            current_backup_name = f"{get_timestamp()}_current_before_restore"
            current_backup_path = BACKUP_DIR / current_backup_name
            shutil.copytree(NOITA_SAVE_PATH, current_backup_path)
            
            # 再覆盖
            if NOITA_SAVE_PATH.exists():
                shutil.rmtree(NOITA_SAVE_PATH)
            shutil.copytree(backup_path, NOITA_SAVE_PATH)
            
            messagebox.showinfo("成功", f"完整存档已恢复！\n当前存档已备份为：{current_backup_name}")
    except Exception as e:
        messagebox.showerror("恢复失败", str(e))

def delete_selected():
    sel = listbox.curselection()
    if not sel:
        return

    idx = sel[0]
    name, _, _ = get_backup_list()[idx]

    if messagebox.askyesno("确认删除", f"真的要删除\n{name}？\n无法恢复！") == tk.YES:
        try:
            shutil.rmtree(BACKUP_DIR / name)
            messagebox.showinfo("已删除", f"{name} 已删除")
            refresh_list()
        except Exception as e:
            messagebox.showerror("删除失败", str(e))

# ================= GUI =================
root = tk.Tk()
root.title("Noita 存档快速备份")
root.geometry("520x480")
root.configure(bg="white")

tk.Label(root, text="Noita 存档管理", font=("Microsoft YaHei", 14, "bold"), bg="white").pack(pady=10)

frame_btn = tk.Frame(root, bg="white")
frame_btn.pack(pady=10)

btn_full = tk.Button(frame_btn, text="保存完整存档", font=("Microsoft YaHei", 12), width=16, height=2,
                     command=lambda: save_backup("full"), bg="#e0e0e0")
btn_full.pack(side=tk.LEFT, padx=20)

btn_world = tk.Button(frame_btn, text="仅保存世界", font=("Microsoft YaHei", 12), width=16, height=2,
                      command=lambda: save_backup("world"), bg="#e0e0e0")
btn_world.pack(side=tk.LEFT, padx=20)

tk.Label(root, text="已保存存档（最新在上）", font=("Microsoft YaHei", 11), bg="white").pack(pady=5)

listbox = tk.Listbox(root, font=("Consolas", 11), height=12, width=60, selectmode=tk.SINGLE)
listbox.pack(pady=5)

scroll = ttk.Scrollbar(root, orient=tk.VERTICAL, command=listbox.yview)
scroll.pack(side=tk.RIGHT, fill=tk.Y)
listbox.config(yscrollcommand=scroll.set)

frame_op = tk.Frame(root, bg="white")
frame_op.pack(pady=15)

btn_restore = tk.Button(frame_op, text="恢复选中存档", font=("Microsoft YaHei", 11), width=15,
                        command=restore_selected, bg="#a0d0ff")
btn_restore.pack(side=tk.LEFT, padx=10)

btn_delete = tk.Button(frame_op, text="删除选中存档", font=("Microsoft YaHei", 11), width=15,
                       command=delete_selected, bg="#ffcccc")
btn_delete.pack(side=tk.LEFT, padx=10)

refresh_list()  # 初次加载

root.mainloop()