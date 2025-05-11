import json
import threading
import subprocess
import keyboard
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from pystray import Icon, MenuItem as item, Menu
from PIL import Image, ImageDraw
import sys
import os
import psutil
import winreg

config_file = "shortcuts.json"
hotkey_refs = []
hotkeys_enabled = True

def load_config():
    try:
        with open(config_file, "r") as f:
            return json.load(f)
    except:
        return {}

def save_config(data):
    with open(config_file, "w") as f:
        json.dump(data, f, indent=2)

def register_hotkeys(shortcuts):
    global hotkey_refs
    for ref in hotkey_refs:
        keyboard.remove_hotkey(ref)
    hotkey_refs.clear()

    if hotkeys_enabled:
        for keys, cmd in shortcuts.items():
            ref = keyboard.add_hotkey(keys, lambda c=cmd: subprocess.Popen(c, shell=True))
            hotkey_refs.append(ref)

def set_high_priority():
    try:
        p = psutil.Process()
        p.nice(psutil.HIGH_PRIORITY_CLASS)
    except Exception as e:
        print("Failed to set high priority:", e)

def toggle_startup(enable):
    try:
        name = "KeyTask"
        path = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__)
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Run", 0,
                             winreg.KEY_SET_VALUE)
        if enable:
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, f'"{path}"')
        else:
            winreg.DeleteValue(key, name)
        winreg.CloseKey(key)
    except Exception as e:
        print("Error toggling startup:", e)

def is_startup_enabled():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Run", 0,
                             winreg.KEY_READ)
        _, _ = winreg.QueryValueEx(key, "KeyTask")
        winreg.CloseKey(key)
        return True
    except:
        return False

def open_settings():
    win = tk.Toplevel(root)
    win.title("Settings")
    win.geometry("300x180")
    win.resizable(False, False)

    try:
        win.iconphoto(True, tk.PhotoImage(file="KeyTask.png"))
    except:
        pass

    startup_var = tk.BooleanVar(value=is_startup_enabled())
    ttk.Checkbutton(win, text="Start with Windows", variable=startup_var).pack(pady=10)

    def apply_settings():
        toggle_startup(startup_var.get())
        messagebox.showinfo("Saved", "Settings updated.")
        win.destroy()

    ttk.Button(win, text="Save", command=apply_settings).pack(pady=10)

def create_tray_icon(root, shortcuts):
    def on_show():
        root.after(0, root.deiconify)

    def on_exit():
        icon.stop()
        root.after(0, root.destroy)

    def on_enable():
        global hotkeys_enabled
        hotkeys_enabled = True
        register_hotkeys(shortcuts)

    def on_disable():
        global hotkeys_enabled
        hotkeys_enabled = False
        register_hotkeys(shortcuts)

    def on_manage_hotkeys():
        root.after(0, on_show)

    def on_settings():
        root.after(0, open_settings)

    try:
        image = Image.open("KeyTask.png").resize((64, 64))
    except:
        image = Image.new('RGB', (64, 64), (70, 130, 180))
        draw = ImageDraw.Draw(image)
        draw.rectangle((16, 16, 48, 48), fill=(255, 255, 255))

    menu = Menu(
        item('Edit Shortcut', on_manage_hotkeys),
        item('Settings', on_settings),
        Menu.SEPARATOR,
        item('Enable', on_enable),
        item('Disable', on_disable),
        item('Exit', on_exit)
    )

    icon = Icon("KeyTask", image, "KeyTask", menu)

    def run_icon():
        icon.run()

    threading.Thread(target=run_icon, daemon=True).start()
    return icon

def open_ui():
    global root
    shortcuts = load_config()
    register_hotkeys(shortcuts)



    def refresh_tree():
        for i in tree.get_children():
            tree.delete(i)
        for key, cmd in shortcuts.items():
            tree.insert('', 'end', values=(key, cmd))

    def open_editor(old_key=None):
        editor = tk.Toplevel(root)
        editor.title("Edit Shortcut" if old_key else "Add Shortcut")
        editor.geometry("350x160")
        editor.resizable(False, False)

        try:
            editor.iconphoto(True, tk.PhotoImage(file="KeyTask.png"))
        except:
            pass

        tk.Label(editor, text="Hotkey:").pack(pady=(10, 0))
        key_var = tk.StringVar(value=old_key if old_key else "")
        key_entry = ttk.Entry(editor, textvariable=key_var, width=40)
        key_entry.pack(pady=5)

        tk.Label(editor, text="Command:").pack()
        cmd_var = tk.StringVar(value=shortcuts[old_key] if old_key else "")
        cmd_entry = ttk.Entry(editor, textvariable=cmd_var, width=40)
        cmd_entry.pack(pady=5)

        def save():
            new_key = key_var.get().strip()
            new_cmd = cmd_var.get().strip()
            if not new_key or not new_cmd:
                messagebox.showerror("Error", "Fields cannot be empty.")
                return
            if old_key and new_key != old_key:
                shortcuts.pop(old_key, None)
            shortcuts[new_key] = new_cmd
            save_config(shortcuts)
            register_hotkeys(shortcuts)
            refresh_tree()
            editor.destroy()

        ttk.Button(editor, text="Save", command=save).pack(pady=(10, 5))

    def add_shortcut():
        open_editor()

    def edit_shortcut():
        selected = tree.selection()
        if not selected:
            return
        key = tree.item(selected[0])['values'][0]
        open_editor(old_key=key)

    def delete_shortcut():
        selected = tree.selection()
        if not selected:
            return
        key = tree.item(selected[0])['values'][0]
        if messagebox.askyesno("Delete", f"Delete shortcut '{key}'?"):
            shortcuts.pop(key, None)
            save_config(shortcuts)
            register_hotkeys(shortcuts)
            refresh_tree()

    def on_close():
        root.withdraw()

    root = tk.Tk()
    root.title("KeyTask")
    root.geometry("500x300")
    root.resizable(False, False)

    try:
        root.iconphoto(True, tk.PhotoImage(file="KeyTask.png"))
    except:
        pass

    style = ttk.Style()
    style.theme_use("clam")

    tree = ttk.Treeview(root, columns=('Hotkey', 'Command'), show='headings')
    tree.heading('Hotkey', text='Hotkey')
    tree.heading('Command', text='Command')
    tree.column('Hotkey', width=150)
    tree.column('Command', width=330)
    tree.pack(pady=10)

    frame = ttk.Frame(root)
    frame.pack(pady=5)

    ttk.Button(frame, text="Add", command=add_shortcut).grid(row=0, column=0, padx=5)
    ttk.Button(frame, text="Edit", command=edit_shortcut).grid(row=0, column=1, padx=5)
    ttk.Button(frame, text="Delete", command=delete_shortcut).grid(row=0, column=2, padx=5)

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.withdraw()

    create_tray_icon(root, shortcuts)
    refresh_tree()
    root.mainloop()

# Start app
set_high_priority()
threading.Thread(target=keyboard.wait, daemon=True).start()
open_ui()
