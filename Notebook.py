#一个 Bug 是 Bug ，一堆 Bug 是 Debug ；能跑起来的叫 Feature ，跑不起来的叫 Debug ，跑起来了但不知所云的叫玄学，而你的 Debugger 妈妈能把“不知为何能跑”改成“不知为何跑不起来”的，如果你乱动，那么本来能跑的也跑不起来了，这叫 Release ，你盯着日志它不复现，你一去倒水它就崩，这叫 Heisenbug ，稳定复现，像玻尔模型一样老实的叫 Bohrbug ，你不看代码它有问题，一看代码它又好像正常的叫 Schrödinbug ，像混沌分形的，你修一个角，它炸一片的叫 Mandelbug~
#早期 Harvard Mark II 计算机里发现过一只飞蛾，被贴在本子上写着 “First actual case of bug being found”
#Debugger 就是去除 Bug 的东西——只不过去除方式是先制造一个更确定的 Bug ~awa


import json
import os
import re
import sys
import csv
import time
import sqlite3
import tkinter as tk
import customtkinter as ctk
from tkinter import ttk, filedialog

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


FOLDER = "C:\\Notebook"
DB_FILE = os.path.join(FOLDER, "notes.db")
SETTINGS_FILE = os.path.join(FOLDER, "settings.json")


DEFAULT_SETTINGS = {
    "appearance_mode": "Dark",
    "font_size": 11,
    "text_color": "#ffffff",
    "selected_color": "#1f6aa5",
}


def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            result = DEFAULT_SETTINGS.copy()
            result.update(data)
            return result
        except Exception:
            return DEFAULT_SETTINGS.copy()
    return DEFAULT_SETTINGS.copy()


def save_settings(settings):
    try:
        os.makedirs(FOLDER, exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def resource_path(relative):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative)
    return os.path.join(os.path.abspath("."), relative)


def format_time(timestamp):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))


#数据库

def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            permanent INTEGER NOT NULL,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_updated ON notes(updated_at DESC)")
    conn.commit()
    conn.close()


def create_note(content, permanent):
    now = time.time()
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO notes (content, permanent, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (content, 1 if permanent else 0, now, now)
    )
    note_id = cur.lastrowid
    conn.commit()
    conn.close()
    return note_id


def list_notes():
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, content, permanent, updated_at FROM notes ORDER BY updated_at DESC"
    ).fetchall()
    conn.close()
    return rows


def get_note(note_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT id, content, permanent, created_at, updated_at FROM notes WHERE id = ?",
        (note_id,)
    ).fetchone()
    conn.close()
    return row


def update_note(note_id, content):
    conn = get_conn()
    conn.execute(
        "UPDATE notes SET content = ?, updated_at = ? WHERE id = ?",
        (content, time.time(), note_id)
    )
    conn.commit()
    conn.close()


def remove_note(note_id):
    conn = get_conn()
    conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    conn.commit()
    conn.close()


def clean_temp_notes():
    conn = get_conn()
    cur = conn.execute("DELETE FROM notes WHERE permanent = 0")
    count = cur.rowcount
    conn.commit()
    conn.close()
    return count


def count_temp_notes():
    conn = get_conn()
    row = conn.execute("SELECT COUNT(*) AS c FROM notes WHERE permanent = 0").fetchone()
    conn.close()
    return row["c"]


#搜索

def search_notes(keyword, use_regex=False):
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, content, permanent, updated_at FROM notes ORDER BY updated_at DESC"
    ).fetchall()
    conn.close()

    if not keyword or not keyword.strip():
        return rows

    keyword = keyword.strip()
    results = []

    if use_regex:
        try:
            pattern = re.compile(keyword, re.IGNORECASE)
        except re.error:
            return []
        for row in rows:
            if pattern.search(row["content"]):
                results.append(row)
    else:
        kw = keyword.lower()
        for row in rows:
            if kw in row["content"].lower():
                results.append(row)
    return results


#导入导出

def export_to_json(file_path):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM notes ORDER BY id").fetchall()
    conn.close()

    data = [dict(row) for row in rows]
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    return len(data)


def export_to_csv(file_path):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM notes ORDER BY id").fetchall()
    conn.close()

    with open(file_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "content", "permanent", "created_at", "updated_at"])
        for row in rows:
            writer.writerow([
                row["id"], row["content"], row["permanent"],
                row["created_at"], row["updated_at"]
            ])
    return len(rows)


def import_from_json(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    conn = get_conn()
    count = 0
    for item in data:
        conn.execute(
            "INSERT INTO notes (content, permanent, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (
                item.get("content", ""),
                1 if item.get("permanent") else 0,
                item.get("created_at", time.time()),
                item.get("updated_at", time.time())
            )
        )
        count += 1
    conn.commit()
    conn.close()
    return count


def import_from_csv(file_path):
    conn = get_conn()
    count = 0
    with open(file_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                created = float(row.get("created_at", time.time()))
                updated = float(row.get("updated_at", time.time()))
            except ValueError:
                created = updated = time.time()

            conn.execute(
                "INSERT INTO notes (content, permanent, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (
                    row.get("content", ""),
                    int(row.get("permanent", 0) or 0),
                    created,
                    updated
                )
            )
            count += 1
    conn.commit()
    conn.close()
    return count


#自定义弹窗

class InfoDialog(ctk.CTkToplevel):
    def __init__(self, parent, title, message):
        super().__init__(parent)
        self.title(title)
        self.geometry("300x100")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._fullscreen = False

        parent.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 300) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 100) // 2
        self.geometry(f"+{x}+{y}")

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True)

        self.textbox = ctk.CTkTextbox(
            container, wrap="word",
            font=("Microsoft YaHei", 11),
            corner_radius=10
        )
        self.textbox.pack(fill="both", expand=True, padx=20, pady=(15, 5))
        self.textbox.insert("1.0", message)
        self.textbox.configure(state="disabled")

        ctk.CTkLabel(
            container,
            text="F11 / Double-click to zoom    Esc to close",
            font=("Microsoft YaHei", 9),
            text_color="gray"
        ).pack(pady=(0, 10))

        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<F11>", self._toggle_fullscreen)
        self.bind("<Double-Button-1>", self._toggle_fullscreen)
        self.focus_set()

    def _toggle_fullscreen(self, event=None):
        self._fullscreen = not self._fullscreen
        self.attributes("-fullscreen", self._fullscreen)


class YesNoDialog(ctk.CTkToplevel):
    def __init__(self, parent, title, message, callback):
        super().__init__(parent)
        self.callback = callback
        self.title(title)
        self.geometry("200x140")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        parent.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 200) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 140) // 2
        self.geometry(f"+{x}+{y}")

        ctk.CTkLabel(
            self, text=message,
            font=("Microsoft YaHei", 12),
            wraplength=300
        ).pack(pady=(25, 10))

        ctk.CTkLabel(
            self,
            text="Enter = Yes    Esc = No",
            font=("Microsoft YaHei", 9),
            text_color="gray"
        ).pack()

        self.bind("<Return>", lambda e: self._finish(True))
        self.bind("<Escape>", lambda e: self._finish(False))
        self.focus_set()

    def _finish(self, result):
        self.destroy()
        self.callback(result)


class StringDialog(ctk.CTkToplevel):
    def __init__(self, parent, title, prompt, callback, initial=""):
        super().__init__(parent)
        self.callback = callback
        self.title(title)
        self.geometry("420x220")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._fullscreen = False

        parent.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 420) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 220) // 2
        self.geometry(f"+{x}+{y}")

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True)

        self.textbox = ctk.CTkTextbox(
            container, wrap="word",
            font=("Microsoft YaHei", 11),
            corner_radius=10
        )
        self.textbox.pack(fill="both", expand=True, padx=20, pady=(15, 5))
        self.textbox.insert("1.0", initial)
        self.textbox.focus_set()

        ctk.CTkLabel(
            container,
            text="Ctrl+Enter = OK    Esc = Cancel    F11 = Zoom",
            font=("Microsoft YaHei", 9),
            text_color="#888888"
        ).pack(pady=(0, 10))

        self.bind("<Escape>", lambda e: self._finish(None))
        self.bind("<F11>", self._toggle_fullscreen)
        self.textbox.bind("<Control-Return>", lambda e: self._finish(self._get_text()))

    def _get_text(self):
        return self.textbox.get("1.0", "end-1c").strip()

    def _toggle_fullscreen(self, event=None):
        self._fullscreen = not self._fullscreen
        self.attributes("-fullscreen", self._fullscreen)

    def _finish(self, result):
        self.destroy()
        self.callback(result)


class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, parent, app, settings):
        super().__init__(parent)
        self.app = app
        self.settings = settings.copy()
        self._closing = False  #防止关闭时回调还在跑，我就是差点没有发现这个错误被程序给崩了一脸错误

        self.title("Settings")
        self.geometry("440x460")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        parent.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 440) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 460) // 2
        self.geometry(f"+{x}+{y}")

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=25, pady=20)

        #外观模式
        ctk.CTkLabel(
            container, text="外观模式 / Appearance Mode",
            font=("Microsoft YaHei", 12), anchor="w"
        ).pack(fill="x", pady=(0, 4))
        self.appearance_var = tk.StringVar(value=self.settings["appearance_mode"])
        ctk.CTkOptionMenu(
            container,
            values=["Dark", "Light", "System"],
            variable=self.appearance_var,
            font=("Microsoft YaHei", 11),
            height=32
        ).pack(fill="x", pady=(0, 14))

        #字体大小
        ctk.CTkLabel(
            container, text="字体大小 / Font Size",
            font=("Microsoft YaHei", 12), anchor="w"
        ).pack(fill="x", pady=(0, 4))

        font_row = ctk.CTkFrame(container, fg_color="transparent")
        font_row.pack(fill="x", pady=(0, 14))

        self.font_size_var = tk.IntVar(value=self.settings["font_size"])
        self.font_size_label = ctk.CTkLabel(
            font_row, text=str(self.settings["font_size"]),
            font=("Microsoft YaHei", 12, "bold"),
            width=40
        )
        self.font_size_label.pack(side="right")

        self.font_slider = ctk.CTkSlider(
            font_row,
            from_=8, to=24,
            number_of_steps=16,
            variable=self.font_size_var,
            command=self._on_font_change,
        )
        self.font_slider.pack(side="left", fill="x", expand=True, padx=(0, 10))

        #文本颜色
        ctk.CTkLabel(
            container, text="文本颜色 / Text Color (hex)",
            font=("Microsoft YaHei", 12), anchor="w"
        ).pack(fill="x", pady=(0, 4))
        self.text_color_var = tk.StringVar(value=self.settings["text_color"])
        ctk.CTkEntry(
            container, textvariable=self.text_color_var,
            font=("Microsoft YaHei", 11), height=32
        ).pack(fill="x", pady=(0, 14))

        #选中高亮色
        ctk.CTkLabel(
            container, text="选中高亮色 / Selected Highlight (hex)",
            font=("Microsoft YaHei", 12), anchor="w"
        ).pack(fill="x", pady=(0, 4))
        self.selected_color_var = tk.StringVar(value=self.settings["selected_color"])
        ctk.CTkEntry(
            container, textvariable=self.selected_color_var,
            font=("Microsoft YaHei", 11), height=32
        ).pack(fill="x", pady=(0, 14))

        #提示
        ctk.CTkLabel(
            container,
            text="提示：颜色格式如 #ffffff / #1f6aa5",
            font=("Microsoft YaHei", 10),
            text_color="#888888"
        ).pack(pady=(0, 10))

        #按钮行
        btn_row = ctk.CTkFrame(container, fg_color="transparent")
        btn_row.pack(fill="x", pady=(10, 0))

        ctk.CTkButton(
            btn_row, text="重置默认", command=self._reset,
            font=("Microsoft YaHei", 11), width=110, height=34
        ).pack(side="left")

        ctk.CTkButton(
            btn_row, text="取消", command=self._close,
            font=("Microsoft YaHei", 11), width=80, height=34,
            fg_color="#555555", hover_color="#444444"
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            btn_row, text="应用", command=self._apply,
            font=("Microsoft YaHei", 11), width=80, height=34
        ).pack(side="right")

        self.bind("<Escape>", lambda e: self._close())
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.focus_set()

    def _on_font_change(self, value):
        # 关闭过程中直接忽略
        if self._closing:
            return
        try:
            if not self.winfo_exists():
                return
            self.font_size_label.configure(text=str(int(float(value))))
        except Exception:
            pass

    def _reset(self):
        if self._closing:
            return
        self.appearance_var.set(DEFAULT_SETTINGS["appearance_mode"])
        self.font_size_var.set(DEFAULT_SETTINGS["font_size"])
        try:
            self.font_size_label.configure(text=str(DEFAULT_SETTINGS["font_size"]))
        except Exception:
            pass
        self.text_color_var.set(DEFAULT_SETTINGS["text_color"])
        self.selected_color_var.set(DEFAULT_SETTINGS["selected_color"])

    def _apply(self):
        if self._closing:
            return
        self.settings["appearance_mode"] = self.appearance_var.get()
        self.settings["font_size"] = int(self.font_size_var.get())
        self.settings["text_color"] = self.text_color_var.get().strip()
        self.settings["selected_color"] = self.selected_color_var.get().strip()
        # 先关闭自己，再应用设置（避免设置应用过程中弹窗/刷样式时打到自己）
        self._close()
        self.app.apply_settings(self.settings)

    def _close(self):
        if self._closing:
            return
        self._closing = True
        # 解除滑块 command，防止销毁过程中回调
        try:
            self.font_slider.configure(command=lambda v: None)
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass


#GUI

class NotebookApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Notebook")
        try:
            self.root.iconbitmap(resource_path("icon.ico"))
        except Exception:
            pass
        self.root.geometry("1000x620")
        self.root.minsize(700, 460)

        self.settings = load_settings()
        self._fullscreen = False

        #应用外观模式（在创建控件之前）
        ctk.set_appearance_mode(self.settings["appearance_mode"])

        #搜索栏
        search_frame = ctk.CTkFrame(root, fg_color="transparent")
        search_frame.pack(fill="x", padx=20, pady=(10, 0))

        self.search_var = tk.StringVar()
        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Search... (Ctrl+F)",
            textvariable=self.search_var,
            font=("Microsoft YaHei", self.settings["font_size"]),
            height=32
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.search_var.trace_add("write", lambda *a: self.refresh_list())

        self.regex_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            search_frame, text="Regex",
            variable=self.regex_var,
            command=self.refresh_list,
            font=("Microsoft YaHei", 10),
            width=70
        ).pack(side="left")

        #表格
        table_frame = ctk.CTkFrame(root, corner_radius=15)
        table_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.style = ttk.Style()
        self.style.theme_use("default")

        columns = ("id", "updated", "type", "preview")
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse"
        )

        self.tree.heading("id", text="ID")
        self.tree.heading("updated", text="Updated")
        self.tree.heading("type", text="Type")
        self.tree.heading("preview", text="Preview")

        self.tree.column("id", width=60, anchor="center")
        self.tree.column("updated", width=170, anchor="center")
        self.tree.column("type", width=70, anchor="center")
        self.tree.column("preview", width=500, anchor="w")

        scrollbar = ctk.CTkScrollbar(table_frame, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        scrollbar.pack(side="right", fill="y", padx=(0, 10), pady=10)

        #路径显示标签
        self.path_label = ctk.CTkLabel(
            root, text=f"Path: {DB_FILE}",
            font=("Microsoft YaHei", 12),
            text_color="#888888"
        )
        self.path_label.pack(pady=(0, 5))

        #底部灰字快捷键提示
        self.hint = ctk.CTkLabel(
            root,
            text=(
                "Ctrl+N New   Enter View   F2 Edit   Del Delete   Ctrl+F Search   "
                "Ctrl+O Path   Ctrl+D Clean   Ctrl+0~9 Select   Ctrl+G Goto   "
                "Ctrl+E Export   Ctrl+I Import   Ctrl+S Settings   F11 Fullscreen"
            ),
            font=("Microsoft YaHei", 11),
            text_color="#aaaaaa"
        )
        self.hint.pack(pady=(0, 12))

        #快捷键绑定，全局
        self.root.bind("<Control-n>", lambda e: self.new_note())
        self.root.bind("<Control-N>", lambda e: self.new_note())
        self.root.bind("<Control-o>", lambda e: self.change_folder())
        self.root.bind("<Control-O>", lambda e: self.change_folder())
        self.root.bind("<Control-d>", lambda e: self.clean_temp())
        self.root.bind("<Control-D>", lambda e: self.clean_temp())
        self.root.bind("<Control-g>", lambda e: self.goto_index())
        self.root.bind("<Control-G>", lambda e: self.goto_index())
        self.root.bind("<Control-e>", lambda e: self.export_menu())
        self.root.bind("<Control-E>", lambda e: self.export_menu())
        self.root.bind("<Control-i>", lambda e: self.import_menu())
        self.root.bind("<Control-I>", lambda e: self.import_menu())
        self.root.bind("<Control-f>", lambda e: self.focus_search())
        self.root.bind("<Control-F>", lambda e: self.focus_search())
        self.root.bind("<Control-s>", lambda e: self.open_settings())
        self.root.bind("<Control-S>", lambda e: self.open_settings())
        self.root.bind("<F11>", lambda e: self.toggle_fullscreen())
        #搜索框有内容就先清空，否则关程序
        self.root.bind("<Escape>", lambda e: self.on_escape())

        #Ctrl+0~9选择第1~10条
        for i in range(10):
            self.root.bind(
                f"<Control-Key-{i}>",
                lambda e, idx=i: self.select_index(idx)
            )

        #快捷键绑定，针对选中项
        self.tree.bind("<Double-1>", lambda e: self.view_note())
        self.tree.bind("<Return>", lambda e: self.view_note())
        self.tree.bind("<F2>", lambda e: self.edit_note())
        self.tree.bind("<Delete>", lambda e: self.delete_note())

        #首次应用设置（字体、颜色等）
        self._apply_style_only()

        self.refresh_list()

    #设置

    def open_settings(self):
        SettingsDialog(self.root, self, self.settings)

    def apply_settings(self, new_settings):
        self.settings = new_settings
        save_settings(new_settings)

        ctk.set_appearance_mode(new_settings["appearance_mode"])

        #更新搜索框字体
        try:
            self.search_entry.configure(font=("Microsoft YaHei", new_settings["font_size"]))
        except Exception:
            pass

        #更新风格
        self._apply_style_only()

        self._info("Success", "Settings applied!")

    def _apply_style_only(self):
        #根据当前settings更新Treeview样式、路径标签和提示标签的字体。
        font_size = self.settings["font_size"]
        is_dark = ctk.get_appearance_mode() == "Dark"

        bg_color = "#2b2b2b" if is_dark else "#f0f0f0"
        fg_color = self.settings["text_color"]
        selected_color = self.settings["selected_color"]

        self.style.configure(
            "Treeview",
            background=bg_color,
            foreground=fg_color,
            fieldbackground=bg_color,
            borderwidth=0,
            rowheight=max(28, font_size * 2 + 8),
            font=("Microsoft YaHei", font_size)
        )
        self.style.configure(
            "Treeview.Heading",
            font=("Microsoft YaHei", max(9, font_size - 1), "bold")
        )
        self.style.map("Treeview", background=[("selected", selected_color)])

        self.path_label.configure(font=("Microsoft YaHei", max(10, font_size)))
        self.hint.configure(font=("Microsoft YaHei", max(10, font_size - 1)))

    #全屏

    def toggle_fullscreen(self):
        self._fullscreen = not self._fullscreen
        self.root.attributes("-fullscreen", self._fullscreen)

    #搜索相关

    def focus_search(self):
        self.search_entry.focus_set()
        self.search_entry.select_range(0, "end")

    def on_escape(self):
        # 如果处于全屏，先退出全屏
        if self._fullscreen:
            self._fullscreen = False
            self.root.attributes("-fullscreen", False)
            return
        if self.search_var.get():
            self.search_var.set("")
        else:
            self.root.destroy()

    #路径

    def change_folder(self):
        global FOLDER, DB_FILE, SETTINGS_FILE

        folder_selected = filedialog.askdirectory(title="Select save folder")
        if not folder_selected:
            self._info("Notice", "You didn't select any folder (or clicked Cancel)!")
            return

        FOLDER = folder_selected
        DB_FILE = os.path.join(FOLDER, "notes.db")
        SETTINGS_FILE = os.path.join(FOLDER, "settings.json")

        if not os.path.exists(FOLDER):
            os.makedirs(FOLDER, exist_ok=True)

        init_db()
        self.refresh_list()

        self.path_label.configure(text=f"Path: {DB_FILE}")

        self.root.update_idletasks()
        self.root.update()

        self._info("Success", f"Path changed to:\n{FOLDER}\n\nNew DB File:\n{DB_FILE}")

    #列表

    def refresh_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        keyword = self.search_var.get() if hasattr(self, "search_var") else ""
        use_regex = self.regex_var.get() if hasattr(self, "regex_var") else False

        for row in search_notes(keyword, use_regex):
            preview = row["content"][:40].replace("\n", " ")
            tag = "Perm" if row["permanent"] else "Temp"
            self.tree.insert(
                "",
                "end",
                iid=str(row["id"]),
                values=(row["id"], format_time(row["updated_at"]), tag, preview)
            )

    def get_selected_id(self):
        selection = self.tree.selection()
        if not selection:
            self._info("Notice", "Please select a note first")
            return None
        return selection[0]

    #条目选择

    def select_index(self, index):
        children = self.tree.get_children()
        if index < 0 or index >= len(children):
            return
        item = children[index]
        self.tree.selection_set(item)
        self.tree.focus(item)
        self.tree.see(item)

    def goto_index(self):
        def on_number(text):
            if not text:
                return
            try:
                n = int(text)
            except ValueError:
                self._info("Notice", "Please enter a number")
                return
            self.select_index(n - 1)

        self._askstring("Goto", "", on_number)

    #导入导出

    def export_menu(self):
        def on_format(fmt):
            if not fmt:
                return
            fmt = fmt.strip().lower()

            if fmt == "json":
                file_path = filedialog.asksaveasfilename(
                    title="Export to JSON",
                    defaultextension=".json",
                    filetypes=[("JSON", "*.json")]
                )
                if not file_path:
                    return
                count = export_to_json(file_path)
                self._info("Success", f"Exported {count} notes to:\n{file_path}")

            elif fmt == "csv":
                file_path = filedialog.asksaveasfilename(
                    title="Export to CSV",
                    defaultextension=".csv",
                    filetypes=[("CSV", "*.csv")]
                )
                if not file_path:
                    return
                count = export_to_csv(file_path)
                self._info("Success", f"Exported {count} notes to:\n{file_path}")

            else:
                self._info("Notice", "Please enter json or csv")

        self._askstring("Export", "", on_format)

    def import_menu(self):
        def on_format(fmt):
            if not fmt:
                return
            fmt = fmt.strip().lower()

            if fmt == "json":
                file_path = filedialog.askopenfilename(
                    title="Import from JSON",
                    filetypes=[("JSON", "*.json")]
                )
                if not file_path:
                    return
                count = import_from_json(file_path)
                self.refresh_list()
                self._info("Success", f"Imported {count} notes")

            elif fmt == "csv":
                file_path = filedialog.askopenfilename(
                    title="Import from CSV",
                    filetypes=[("CSV", "*.csv")]
                )
                if not file_path:
                    return
                count = import_from_csv(file_path)
                self.refresh_list()
                self._info("Success", f"Imported {count} notes")

            else:
                self._info("Notice", "Please enter json or csv")

        self._askstring("Import", "", on_format)

    #自定义弹窗封装

    def _info(self, title, message):
        InfoDialog(self.root, title, message)

    def _yesno(self, title, message, callback):
        YesNoDialog(self.root, title, message, callback)

    def _askstring(self, title, prompt, callback, initial=""):
        StringDialog(self.root, title, prompt, callback, initial)

    #操作

    def new_note(self):
        def on_content(content):
            if not content:
                return

            def on_permanent(permanent):
                note_id = create_note(content, permanent)
                self.refresh_list()
                self._info("Success", f"Created, ID: {note_id}")

            self._yesno("Save Type", "Save permanently?\nYes = Permanent, No = Temporary", on_permanent)

        self._askstring("New Note", "", on_content)

    def view_note(self):
        note_id = self.get_selected_id()
        if note_id is None:
            return
        note = get_note(int(note_id))
        if note is None:
            self._info("Notice", "Note not found")
            return
        info = (
            f"Created: {format_time(note['created_at'])}\n"
            f"Updated: {format_time(note['updated_at'])}\n"
            f"Type: {'Permanent' if note['permanent'] else 'Temporary'}\n\n"
            f"{note['content']}"
        )
        self._info(f"Note {note['id']}", info)

    def edit_note(self):
        note_id = self.get_selected_id()
        if note_id is None:
            return
        note = get_note(int(note_id))
        if note is None:
            self._info("Notice", "Note not found")
            return

        def on_content(new_content):
            if new_content is None:
                return
            update_note(int(note_id), new_content)
            self.refresh_list()
            self._info("Success", "Updated")

        self._askstring("Edit Note", "", on_content, initial=note["content"])

    def delete_note(self):
        note_id = self.get_selected_id()
        if note_id is None:
            return

        def on_confirm(result):
            if not result:
                return
            remove_note(int(note_id))
            self.refresh_list()
            self._info("Success", "Deleted")

        self._yesno("Confirm", f"Delete note {note_id}?", on_confirm)

    def clean_temp(self):
        count = count_temp_notes()
        if count == 0:
            self._info("Notice", "No temporary notes to clean")
            return

        def on_confirm(result):
            if not result:
                return
            removed = clean_temp_notes()
            self.refresh_list()
            self._info("Success", f"Cleaned {removed} temporary note(s)")

        self._yesno("Confirm", f"Clean {count} temporary note(s)?", on_confirm)


#启动

def main():
    if not os.path.exists(FOLDER):
        os.makedirs(FOLDER, exist_ok=True)

    init_db()

    root = ctk.CTk()
    app = NotebookApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()