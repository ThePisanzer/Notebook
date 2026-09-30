#一个 Bug 是 Bug ，一堆 Bug 是 Debug ；能跑起来的叫 Feature ，跑不起来的叫 Debug ，跑起来了但不知所云的叫玄学，而你的 Debugger 妈妈能把“不知为何能跑”改成“不知为何跑不起来”的，如果你乱动，那么本来能跑的也跑不起来了，这叫 Release ，你盯着日志它不复现，你一去倒水它就崩，这叫 Heisenbug ，稳定复现，像玻尔模型一样老实的叫 Bohrbug ，你不看代码它有问题，一看代码它又好像正常的叫 Schrödinbug ，像混沌分形的，你修一个角，它炸一片的叫 Mandelbug~
#早期 Harvard Mark II 计算机里发现过一只飞蛾，被贴在本子上写着 “First actual case of bug being found”
#Debugger 就是去除 Bug 的东西——只不过去除方式是先制造一个更确定的 Bug ~awa


import json
import os
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


#GUI

class NotebookApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Notebook - {DB_FILE}")
        try:
            self.root.iconbitmap(resource_path("icon.ico"))
        except Exception:
            pass
        self.root.geometry("1000x580")
        self.root.minsize(700, 420)

        table_frame = ctk.CTkFrame(root, corner_radius=15)
        table_frame.pack(fill="both", expand=True, padx=20, pady=10)

        style = ttk.Style()
        style.theme_use("default")

        bg_color = "#2b2b2b" if ctk.get_appearance_mode() == "Dark" else "#f0f0f0"
        fg_color = "#ffffff" if ctk.get_appearance_mode() == "Dark" else "#000000"
        selected_color = "#1f6aa5"

        style.configure(
            "Treeview",
            background=bg_color,
            foreground=fg_color,
            fieldbackground=bg_color,
            borderwidth=0,
            rowheight=30,
            font=("Microsoft YaHei", 10)
        )
        style.configure(
            "Treeview.Heading",
            font=("Microsoft YaHei", 10, "bold")
        )
        style.map("Treeview", background=[("selected", selected_color)])

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

        #底部灰字快捷键提示
        hint = ctk.CTkLabel(
            root,
            text=(
                "Ctrl+N New   Enter View   F2 Edit   Del Delete   Ctrl+O Path   Ctrl+D Clean   Ctrl+0~9 Select   Ctrl+G Goto   Ctrl+E Export   Ctrl+I Import"
            ),
            font=("Microsoft YaHei", 18),
            text_color="#aaaaaa"
        )
        hint.pack(pady=(0, 12))

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
        self.root.bind("<Escape>", lambda e: self.root.destroy())

        #Ctrl+0~9 选择第 1~10 条
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

        self.refresh_list()

    #路径

    def change_folder(self):
        global FOLDER, DB_FILE

        folder_selected = filedialog.askdirectory(title="Select save folder")
        if not folder_selected:
            return

        FOLDER = folder_selected
        DB_FILE = os.path.join(FOLDER, "notes.db")
        if not os.path.exists(FOLDER):
            os.makedirs(FOLDER, exist_ok=True)

        init_db()
        self.refresh_list()
        self.path_label.config(text=f"Path: {DB_FILE}")
        self._info("Success", f"Path changed to:\n{FOLDER}")

    #列表

    def refresh_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for row in list_notes():
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