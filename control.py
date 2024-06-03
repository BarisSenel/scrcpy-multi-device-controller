import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import threading
import subprocess
import json
import os
from endpoints import run_server, ThreadedHTTPServer
import sys
import signal
import time
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
        scrcpy_path = r"C:\Program Files\scrcpy-win64-v2.4\scrcpy.exe"  # Replace this with the full path to scrcpy
        print("Starting scrcpy with device:", serial)
        command = [scrcpy_path, '-s', serial]
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

def execute_adb_command(command):
    subprocess.run(command, check=True, shell=True)

def create_proxy_thread(serial):
    try:
        print("Disabling Plane mode")
        execute_adb_command(f"adb -s {serial} shell cmd connectivity airplane-mode disable")
        print("Disabling Wifi")
        execute_adb_command(f"adb -s {serial} shell svc wifi disable")
        print("Enabling Mobile data")
        execute_adb_command(f"adb -s {serial} shell svc data enable")
        print("Enabling USB tethering")
        try:
            execute_adb_command(f"adb -s {serial} shell svc usb setFunctions rndis")
        except Exception as e:
            print("ignoring exepection") # adb gives exit code 255 for some reason?
        time.sleep(5)
        output = subprocess.run(f"adb -s {serial} shell cat /proc/net/arp", check=True, shell=True,capture_output=True).stdout.decode('utf-8')
        ip = output.split("\n")[1].split(" ")[0]
        print(ip)
        text = f"Rotating Proxy Info:\r\n IP:{ip}:1080\r\nReset Link:http://127.0.0.1:8000/ipreset?serial={serial}"
        print(text)
        messagebox.showinfo("Rotating Proxy Created!",text)
    except Exception as e:
        print("Exception:", e)
        messagebox.showerror("Error", str(e))

def create_proxy_with_serial(serial):
    try:
        print("Starting rotating proxy with device:", serial)
        proxy_thread = threading.Thread(target=create_proxy_thread, args=(serial,))
        proxy_thread.start()

    except Exception as e:
        print("Exception:", e)
        messagebox.showerror("Error", str(e))

def create_proxy():
    selected_index = device_listbox.curselection()
    if selected_index:
        selected_device = device_listbox.get(selected_index[0])
        user_mapping = load_user_mapping()
        for serial, name in user_mapping.items():
            if name == selected_device:
                create_proxy_with_serial(serial)
                return
        create_proxy_with_serial(selected_device)        

def kill_server_by_serial():
    serial_to_kill = serial_kill_entry.get().strip()
    if serial_to_kill:
        running_endpoints = ThreadedHTTPServer.get_running_servers()
        for endpoint in running_endpoints:
            _, serial = endpoint
            if serial == serial_to_kill:
                server = ThreadedHTTPServer.running_servers[endpoint]
                server.shutdown()  # Stop the server associated with the specified serial ID
                del ThreadedHTTPServer.running_servers[endpoint]
                messagebox.showinfo("Server Killed", f"Server for serial '{serial_to_kill}' has been killed.")
                update_running_endpoints()
                return
        messagebox.showerror("Error", f"No server found for serial '{serial_to_kill}'.")

def show_console():
    global console_window
    if console_window:
        console_window.deiconify()
    else:
        console_window = tk.Toplevel()
        console_window.title("Debug Console")
        console_window.geometry("600x400")
        console_window.protocol("WM_DELETE_WINDOW", hide_console)
        
        # Create a text widget
        console_text = tk.Text(console_window, wrap="word", undo=True, bg="white", fg="black")
        console_text.pack(expand=True, fill="both")
        console_text.config(state=tk.DISABLED)
        
        # Set up copying functionality
        def copy_text():
            console_text.clipboard_clear()
            console_text.clipboard_append(console_text.selection_get())
        
        # Bind the right-click event to show the context menu
        def show_context_menu(event):
            context_menu.post(event.x_root, event.y_root)
        
        context_menu = tk.Menu(console_window, tearoff=0)
        context_menu.add_command(label="Copy", command=copy_text)
        
        console_text.bind("<Button-3>", show_context_menu)
        
        # Redirect stdout to the console text widget
        sys.stdout = ConsoleRedirector(console_text)
        
        print("Debug console initialized")


def hide_console():
    global console_window
    console_window.withdraw()

def create_custom_endpoint():
    port = port_entry.get()
    serial = serial_entry.get()
    if port.isdigit():
        port = int(port)
        if port < 1024 or port > 65535:
            messagebox.showerror("Error", "Port number must be between 1024 and 65535")
            return
        else:
            running_endpoints = ThreadedHTTPServer.get_running_servers()
            for endpoint in running_endpoints:
                running_port, _ = endpoint
                if running_port == port:
                    messagebox.showerror("Error", f"Server already running on port {port}")
                    return
            try:
                # Start the HTTP server in a separate thread
                threading.Thread(target=run_server, args=(port, serial), daemon=True).start()
            except Exception as e:
                messagebox.showerror("Error", str(e))
    else:
        messagebox.showerror("Error", "Invalid port number")

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

def update_running_endpoints():
    running_endpoints = ThreadedHTTPServer.get_running_servers()
    endpoints_listbox.delete(0, tk.END)
    for endpoint in running_endpoints:
        port, serial = endpoint
        endpoints_listbox.insert(tk.END, f"Port: {port}, Serial: {serial}")

def refresh_running_endpoints():
    update_running_endpoints()
    root.after(10000, refresh_running_endpoints)  # Refresh every 10 seconds

bg_color = "#ffffff"
fg_color = "#1e1e1e"

root = tk.Tk()
root.title("Device Selector")

root.configure(bg=bg_color)
style = ttk.Style(root)
style.theme_use("clam")
style.configure(".", background=bg_color, foreground=fg_color)
style.configure("TLabel", background=bg_color, foreground=fg_color)
style.configure("TButton", background=bg_color, foreground=fg_color)
style.configure("TEntry", background=bg_color, foreground=fg_color)
style.configure("TListbox", background=bg_color, foreground=fg_color)

root.geometry("600x500")

menu_bar = tk.Menu(root)
root.config(menu=menu_bar)

file_menu = tk.Menu(menu_bar, tearoff=False)
menu_bar.add_cascade(label="File", menu=file_menu)
file_menu.add_command(label="Exit", command=root.quit)

help_menu = tk.Menu(menu_bar, tearoff=False)
menu_bar.add_cascade(label="Help", menu=help_menu)
help_menu.add_command(label="About", command=lambda: messagebox.showinfo("About", "Device Selector App"))

notebook = ttk.Notebook(root)
notebook.pack(fill='both', expand=True)

main_frame = ttk.Frame(notebook)
soon_frame = ttk.Frame(notebook)

notebook.add(main_frame, text='Main')
notebook.add(soon_frame, text='Endpoints')

endpoints_frame = ttk.Frame(soon_frame)
endpoints_frame.pack(side=tk.TOP, fill=tk.BOTH, padx=10, pady=5)

port_label = ttk.Label(endpoints_frame, text="Port:")
port_label.pack(side=tk.LEFT)

port_entry = ttk.Entry(endpoints_frame, width=10)
port_entry.pack(side=tk.LEFT, padx=5)

serial_label = ttk.Label(endpoints_frame, text="Serial:")
serial_label.pack(side=tk.LEFT)

serial_entry = ttk.Entry(endpoints_frame, width=20)
serial_entry.pack(side=tk.LEFT, padx=5)

create_endpoint_button = ttk.Button(endpoints_frame, text="Create Endpoint", command=create_custom_endpoint)
create_endpoint_button.pack(side=tk.LEFT, padx=5)

search_frame = ttk.Frame(main_frame)
search_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

search_label = ttk.Label(search_frame, text="Search:")
search_label.pack(side=tk.LEFT)

search_entry = ttk.Entry(search_frame, width=20)
search_entry.pack(side=tk.LEFT, padx=5)
search_entry.bind("<KeyRelease>", lambda event: refresh_device_list(search_entry.get()))

device_frame = ttk.Frame(main_frame)
device_frame.pack(side=tk.TOP, fill=tk.BOTH, padx=10, pady=5, expand=True)

device_label = ttk.Label(device_frame, text="Connected Devices:")
device_label.pack()

device_listbox = tk.Listbox(device_frame, width=30, height=10, bg=bg_color, fg=fg_color)
device_listbox.pack(pady=5, fill=tk.BOTH, expand=True)
device_listbox.bind("<<ListboxSelect>>", on_device_select)

buttons_frame = ttk.Frame(main_frame)
buttons_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

refresh_button = ttk.Button(buttons_frame, text="Refresh", command=lambda: refresh_device_list(search_entry.get()))
refresh_button.pack(side=tk.LEFT, padx=5)

rename_button = ttk.Button(buttons_frame, text="Rename", command=rename_device)
rename_button.pack(side=tk.LEFT, padx=5)

connect_button = ttk.Button(buttons_frame, text="Connect", command=connect_device)
connect_button.pack(side=tk.LEFT, padx=5)

create_proxy_button = ttk.Button(buttons_frame, text="Create Rotating proxy", command=create_proxy)
create_proxy_button.pack(side=tk.LEFT, padx=5)

console_window = None
console_button = ttk.Button(buttons_frame, text="Show Console", command=show_console)
console_button.pack(side=tk.RIGHT, padx=5)

endpoints_listbox = tk.Listbox(soon_frame, width=40, height=10, bg=bg_color, fg=fg_color)
endpoints_listbox.pack(pady=5, fill=tk.BOTH, expand=True)

serial_kill_frame = ttk.Frame(soon_frame)
serial_kill_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

serial_kill_label = ttk.Label(serial_kill_frame, text="Enter Serial to Kill Server:")
serial_kill_label.pack(side=tk.LEFT)

serial_kill_entry = ttk.Entry(serial_kill_frame, width=20)
serial_kill_entry.pack(side=tk.LEFT, padx=5)

kill_button = ttk.Button(serial_kill_frame, text="Kill Server", command=kill_server_by_serial)
kill_button.pack(side=tk.LEFT, padx=5)

# Start updating the list of running endpoints periodically
refresh_running_endpoints()
threading.Thread(target=run_server, args=(8000, "NULL"), daemon=True).start()
root.mainloop()
