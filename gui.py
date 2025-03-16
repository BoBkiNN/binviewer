import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import shutil
import subprocess
from PIL import Image, ImageTk
import base64
from io import BytesIO

ICON = "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAMAAAAoLQ9TAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAPUExURQAAALGytZOUlv/prwAAAM+/9f4AAAAFdFJOU/////8A+7YOUwAAAAlwSFlzAAAOwwAADsMBx2+oZAAAAFJJREFUKFNtzoEKACEIA1BN//+b22YaHSdC82Gg5ad+waYEZu6LvZxCYBY1aAWiP4AIGeY4GyHiK8CKMrvhTAOVaybMygXkB3gKJl1eIHqhK3MDNsUCVbD/bPkAAAAASUVORK5CYII="

def load_icon():
    icon_data = base64.b64decode(ICON)
    # Load image using PIL from bytes
    image = Image.open(BytesIO(icon_data))
    return ImageTk.PhotoImage(image)

def copy_single_file(file_path: str):
    # Ensure the file path is absolute
    abs_path = os.path.abspath(file_path)
    # Construct the PowerShell command
    command = f"powershell Set-Clipboard -Path '{abs_path}'"
    # Execute the command
    try:
        subprocess.run(command, shell=True, check=True)
    except Exception as e:
        print(f"Failed copying file: {e}")
        messagebox.showerror("Failed copying file", abs_path)

def human_size(bytes, units=[' bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB']):
    """ Returns a human readable string representation of bytes """
    return str(bytes) + units[0] if bytes < 1024 else human_size(bytes >> 10, units[1:])

class JsonViewerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("RecycleBinViewer")
        self.root.geometry("800x600")
        self.root.iconphoto(True, load_icon())

        self.data: dict = None
        self.missing_broken = []
        self.missing_actual = []
        self.items = {}
        
        self.row_data_map: dict[str, dict] = {}
        self.restore_folder: str = os.getcwd()

        self.create_context_menu()
        self.create_widgets()

    def create_widgets(self):
        # Menu Bar
        menubar = tk.Menu(self.root)
        menubar.add_command(label="Open", command=self.open_file_dialog)
        options_menu = tk.Menu(menubar, tearoff=0)
        options_menu.add_command(label="Set restored folder", command=self.open_set_folder_dialog)
        menubar.add_cascade(label="Options", menu=options_menu)
        self.root.config(menu=menubar)

        # Notebook (Tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Items Tab
        self.items_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.items_frame, text="Items")
        self.create_items_table()

        # Missing Broken Tab
        self.missing_broken_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.missing_broken_frame, text="Missing Broken")
        self.create_missing_list(self.missing_broken_frame, "missing_broken")

        # Missing Actual Tab
        self.missing_actual_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.missing_actual_frame, text="Missing Actual")
        self.create_missing_list(self.missing_actual_frame, "missing_actual")

    def create_items_table(self):
        columns = ("Type", "Name",
                   "Folder", "Size")
        self.tree = ttk.Treeview(
            self.items_frame, columns=columns, show="headings")
        for col in columns:
            if col == "Type":
                self.tree.heading(col, text=col)
                self.tree.column(col, anchor=tk.CENTER, stretch=False, width=35)
                continue
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor=tk.W)

        scrollbar = ttk.Scrollbar(
            self.items_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.bind("<Button-3>", self.show_context_menu)
        self.tree.bind("<Double-1>", self.on_double_click)

        # Grid placement
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.items_frame.rowconfigure(0, weight=1)
        self.items_frame.columnconfigure(0, weight=1)

    def create_missing_list(self, frame, attribute):
        text_widget = tk.Text(frame, wrap=tk.WORD)
        text_widget.pack(fill=tk.BOTH, expand=True)
        setattr(self, f"{attribute}_widget", text_widget)
    
    def open_set_folder_dialog(self):
        folder = filedialog.askdirectory(initialdir=self.restore_folder, mustexist=True)
        self.restore_folder = os.path.abspath(folder)

    def open_file_dialog(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filepath:
            self.load_json(filepath)
    
    def on_double_click(self, event: tk.Event):
        row_id = self.tree.identify_row(event.y)
        if not row_id: return
        data = self.row_data_map.get(row_id)
        if not data: return
        path: str = data["path"]
        is_dir: bool = data["item"]["is_directory"]
        if is_dir: return
        os.startfile(path)
    
    def show_context_menu(self, event):
        row_id = self.tree.identify_row(event.y)
        if row_id:
            # Add row under cursor to selection if not already selected
            if row_id not in self.tree.selection():
                self.tree.selection_add(row_id)
            self.context_menu.post(event.x_root, event.y_root)

    
    def create_context_menu(self):
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(
            label="Open", command=self.open_files)
        self.context_menu.add_command(
        label="Print Info", command=self.print_selected_rows)
        self.context_menu.add_command(
            label="Copy", command=self.copy_files)
        self.context_menu.add_command(
            label="Restore", command=lambda: self.restore_files(False))
        self.context_menu.add_command(
            label="Restore to origin", command=lambda: self.restore_files(True))
        self.context_menu.add_command(
            label="Delete forever", command=self.delete_items)
    
    def print_selected_rows(self):
        selected_rows = self.tree.selection()
        if not selected_rows:
            return
        for row_id in selected_rows:
            data = self.row_data_map.get(row_id)
            if data:
                print(f"Row Path: {data['path']}")
                print(f"Row Dict: {data['item']}")
                print("------")
    
    def restore_files(self, to_origin: bool):
        selected_rows = self.tree.selection()
        if not selected_rows:
            return
        for row_id in selected_rows:
            data = self.row_data_map.get(row_id)
            if not data:
                continue
            try:
                self.restore_file(data["path"], data["item"], to_origin)
            except Exception as e:
                messagebox.showerror("Error restoring", str(e))
                return
            self.delete_item(data)
            self.tree.selection_remove([row_id])
            self.tree.delete(row_id)
            self.row_data_map.pop(row_id)
    
    def restore_file(self, path: str, data: dict, to_origin: bool):
        original: str = data["original_location"]
        if not original:
            raise ValueError("Original location not found")
        fname = os.path.basename(original)
        target = original if to_origin else os.path.join(self.restore_folder, fname)
        folder = os.path.dirname(target)
        if not os.path.isdir(folder):
            os.makedirs(folder, exist_ok=True)
        is_dir = data["is_directory"]
        if not is_dir:
            shutil.copy2(path, target)
        else:
            shutil.copytree(path, target)
        print(f"Restored {path} to {target}")

    
    def copy_files(self):
        selected_rows = self.tree.selection()
        if not selected_rows:
            return
        paths: list[str] = []
        for row_id in selected_rows:
            data = self.row_data_map.get(row_id)
            if not data:
                continue
            paths.append(data["path"])
        if len(paths) < 1: return
        copy_single_file(paths[0])
        # copy_files_to_clipboard(paths)
    
    def open_files(self):
        selected_rows = self.tree.selection()
        if not selected_rows:
            return
        for row_id in selected_rows:
            data = self.row_data_map.get(row_id)
            if not data:
                continue
            os.startfile(data["path"])
    
    def delete_items(self):
        selected_rows = self.tree.selection()
        if not selected_rows:
            return
        for row_id in selected_rows:
            data = self.row_data_map.get(row_id)
            if not data: continue
            self.delete_item(data)
            self.tree.selection_remove([row_id])
            self.tree.delete(row_id)
            self.row_data_map.pop(row_id)
    
    def delete_item(self, data: dict[str, dict]):
        path: str = data["path"]
        item: str = data["item"]
        broken: str = item["broken"] # $I file
        is_dir: bool = item["is_directory"]
        print(f"Deleting: {data}")
        if is_dir:
            shutil.rmtree(path)
        else:
            os.remove(path)
        os.remove(broken)

    def load_json(self, filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                self.data = json.load(f)
            self.missing_broken = self.data.get("missing_broken", [])
            self.missing_actual = self.data.get("missing_actual", [])
            self.items = self.data.get("items", {})
            self.populate_items_table()
            self.populate_missing_list("missing_broken")
            self.populate_missing_list("missing_actual")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load JSON file: {e}")

    def populate_items_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        
        # Add tag configuration for red rows
        # Light red background
        self.tree.tag_configure("missing", background="#FFCCCC")
        self.tree.tag_configure("exists", background="#ccffcf")
        for path, item in self.items.items():
            item: dict
            path: str
            if not os.path.exists(path): continue # if outdated data
            is_dir: bool = item.get("is_directory")
            original = item.get("original_location")
            typec = "DIR" if is_dir else "FILE"
            name: str
            folder: str
            size: str
            tags: tuple = ()
            if original:
                name = os.path.basename(original)
                folder = os.path.dirname(original)
                if os.path.exists(original):
                    tags = ("exists",)
            else:
                name = os.path.basename(path)
                folder = os.path.dirname(path)
                tags = ("missing",)
            if name == ".": continue
            if not is_dir:
                try:
                    s = os.path.getsize(path)
                    size = f"{human_size(s)}"
                except Exception:
                    size = "N/A"
            else: size = "-"
            row_id = self.tree.insert("", tk.END, values=(typec, 
                name, folder, size), tags=tags)
            
            self.row_data_map[row_id] = {"path": path, "item": item}

    def populate_missing_list(self, attribute):
        widget = getattr(self, f"{attribute}_widget")
        widget.delete(1.0, tk.END)
        for path in getattr(self, attribute):
            widget.insert(tk.END, f"{path}\n")


if __name__ == "__main__":
    root = tk.Tk()
    app = JsonViewerApp(root)
    root.mainloop()
