import subprocess
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import json
import os
import threading
import sys

USER_JSON_FILE = "user.json"

def load_user_mapping():
    if os.path.exists(USER_JSON_FILE):
        with open(USER_JSON_FILE, "r") as f:
            return json.load(f)
    return {}

def save_user_mapping(user_mapping):
    with open(USER_JSON_FILE, "w") as f:
        json.dump(user_mapping, f)

def get_connected_devices():
    try:
        result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, check=True)
        output = result.stdout.splitlines()
        devices = [line.split('\t')[0] for line in output[1:] if line.strip() != '']
        return devices
    except subprocess.CalledProcessError as e:
        print("Error:", e)
        return []

def start_scrcpy(serial):
    try:
        scrcpy_path = r"C:\Users\Chaos\Documents\scrcpy-win64-v2.4\scrcpy.exe"  # Replace this with the full path to scrcpy
        print("Starting scrcpy with device:", serial)
        command = [scrcpy_path, '--turn-screen-off', '-s', serial]
        print("Executing command:", command)

        def run_scrcpy():
            subprocess.run(command)

        scrcpy_thread = threading.Thread(target=run_scrcpy)
        scrcpy_thread.start()

    except Exception as e:
        print("Exception:", e)
        messagebox.showerror("Error", str(e))

def on_device_select(event):
    selected_index = device_listbox.curselection()
    if selected_index:
        selected_device = device_listbox.get(selected_index[0])
        user_mapping = load_user_mapping()
        for serial, name in user_mapping.items():
            if name == selected_device:
                print("Selected device:", serial)
                return
        print("Selected device:", selected_device)

def refresh_device_list(search_text=""):
    print("Refreshing device list...")
    device_listbox.delete(0, tk.END)
    devices = get_connected_devices()
    user_mapping = load_user_mapping()
    for device in devices:
        if device in user_mapping:
            device_name = user_mapping[device]
            if search_text.lower() in device_name.lower():
                device_listbox.insert(tk.END, device_name)
        else:
            if search_text.lower() in device.lower():
                device_listbox.insert(tk.END, device)

def rename_device():
    selected_index = device_listbox.curselection()
    if selected_index:
        selected_device = device_listbox.get(selected_index[0])
        user_mapping = load_user_mapping()
        for serial, name in user_mapping.items():
            if name == selected_device:
                selected_serial = serial
                break
        else:
            selected_serial = selected_device

        new_name = simpledialog.askstring("Rename Device", "Enter a new name for the device:")
        if new_name:
            user_mapping[selected_serial] = new_name
            save_user_mapping(user_mapping)
            refresh_device_list(search_entry.get())

def connect_device():
    selected_index = device_listbox.curselection()
    if selected_index:
        selected_device = device_listbox.get(selected_index[0])
        user_mapping = load_user_mapping()
        for serial, name in user_mapping.items():
            if name == selected_device:
                start_scrcpy(serial)
                return
        start_scrcpy(selected_device)

def show_console():
    global console_window
    if console_window:
        console_window.deiconify()
    else:
        console_window = tk.Toplevel()
        console_window.title("Debug Console")
        console_window.geometry("600x400")
        console_window.protocol("WM_DELETE_WINDOW", hide_console)
        console_window.bind("<KeyPress>", lambda event: console_text.focus_set())
        console_text = tk.Text(console_window, wrap="word", undo=True, bg="black", fg="white")
        console_text.pack(expand=True, fill="both")
        console_text.config(state=tk.DISABLED)
        console_text.bind("<Key>", lambda event: "break")
        console_text.focus_set()
        sys.stdout = ConsoleRedirector(console_text)
        print("Debug console initialized")

def hide_console():
    global console_window
    console_window.withdraw()

class ConsoleRedirector:
    def __init__(self, widget):
        self.widget = widget

    def write(self, text):
        self.widget.config(state=tk.NORMAL)
        self.widget.insert(tk.END, text)
        self.widget.see(tk.END)
        self.widget.config(state=tk.DISABLED)

    def flush(self):
        pass
# Set custom background and foreground colors
bg_color = "#1e1e1e"  # Dark gray background color
fg_color = "#ffffff"  # White foreground color

root = tk.Tk()
root.title("Device Selector")

# Configure custom theme
root.configure(bg=bg_color)
style = ttk.Style(root)
style.theme_use("clam")
style.configure(".", background=bg_color, foreground=fg_color)
style.configure("TLabel", background=bg_color, foreground=fg_color)
style.configure("TButton", background=bg_color, foreground=fg_color)
style.configure("TEntry", background=bg_color, foreground=fg_color)
style.configure("TListbox", background=bg_color, foreground=fg_color)  # Configure listbox background color

root.geometry("600x500")

search_frame = ttk.Frame(root)
search_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

search_label = ttk.Label(search_frame, text="Search:")
search_label.pack(side=tk.LEFT)

search_entry = ttk.Entry(search_frame, width=20)
search_entry.pack(side=tk.LEFT, padx=5)
search_entry.bind("<KeyRelease>", lambda event: refresh_device_list(search_entry.get()))

device_frame = ttk.Frame(root)
device_frame.pack(side=tk.TOP, fill=tk.BOTH, padx=10, pady=5, expand=True)

device_label = ttk.Label(device_frame, text="Connected Devices:")
device_label.pack()

device_listbox = tk.Listbox(device_frame, width=30, height=10, bg=bg_color, fg=fg_color)  # Set listbox background color
device_listbox.pack(pady=5, fill=tk.BOTH, expand=True)
device_listbox.bind("<<ListboxSelect>>", on_device_select)

buttons_frame = ttk.Frame(root)
buttons_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

refresh_button = ttk.Button(buttons_frame, text="Refresh", command=lambda: refresh_device_list(search_entry.get()))
refresh_button.pack(side=tk.LEFT, padx=5)

rename_button = ttk.Button(buttons_frame, text="Rename", command=rename_device)
rename_button.pack(side=tk.LEFT, padx=5)

connect_button = ttk.Button(buttons_frame, text="Connect", command=connect_device)
connect_button.pack(side=tk.LEFT, padx=5)

console_window = None
console_button = ttk.Button(buttons_frame, text="Show Console", command=show_console)
console_button.pack(side=tk.RIGHT, padx=5)

refresh_device_list()

root.mainloop()