from tkinter import messagebox, simpledialog, ttk
import threading
import subprocess
import json
import os
from endpoints import run_server, ThreadedHTTPServer
import sys
import signal
import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
import pygetwindow as gw
import psutil
from time import sleep
import time
USER_JSON_FILE = "user.json"
ENDPOINTS_JSON_FILE = "endpoints.json"

def load_user_mapping():
    if os.path.exists(USER_JSON_FILE):
        with open(USER_JSON_FILE, "r") as f:
            return json.load(f)
    return {}

def save_user_mapping(user_mapping):
    with open(USER_JSON_FILE, "w") as f:
        json.dump(user_mapping, f)

def save_endpoints():
    running_endpoints = ThreadedHTTPServer.get_running_servers()
    endpoints_data = [{"port": port, "serial": serial} for port, serial in running_endpoints]
    with open(ENDPOINTS_JSON_FILE, "w") as f:
        json.dump(endpoints_data, f)
    messagebox.showinfo("Save Endpoints", "Current endpoints have been saved successfully.")

def load_endpoints():
    if os.path.exists(ENDPOINTS_JSON_FILE):
        with open(ENDPOINTS_JSON_FILE, "r") as f:
            endpoints_data = json.load(f)
        for endpoint in endpoints_data:
            port = endpoint["port"]
            serial = endpoint["serial"]
            threading.Thread(target=run_server, args=(port, serial), daemon=True).start()
        update_running_endpoints()
        messagebox.showinfo("Load Endpoints", "Endpoints have been loaded successfully.")


def get_connected_devices():
    try:
        result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, check=True)
        output = result.stdout.splitlines()
        devices = [line.split('\t')[0] for line in output[1:] if line.strip() != '']
        return devices
    except subprocess.CalledProcessError as e:
        print("Error:", e)
        return []

def on_listbox_click(event):
    if event.state & 0x4:  # CTRL key is pressed (state 0x4 represents CTRL)
        # Perform toggle selection (CTRL + Click behavior)
        if device_listbox.selection_includes(device_listbox.nearest(event.y)):
            device_listbox.selection_clear(device_listbox.nearest(event.y))
        else:
            device_listbox.selection_set(device_listbox.nearest(event.y))
    elif event.state & 0x1:  # Shift key is pressed (state 0x1 represents Shift)
        # Perform range selection (Shift + Click behavior)
        last_selected = device_listbox.curselection()[-1] if device_listbox.curselection() else 0
        clicked_index = device_listbox.nearest(event.y)
        device_listbox.selection_clear(0, tk.END)
        device_listbox.selection_set(min(last_selected, clicked_index), max(last_selected, clicked_index))
    else:
        # Regular click (single selection)
        device_listbox.selection_clear(0, tk.END)
        device_listbox.selection_set(device_listbox.nearest(event.y))

def on_ctrl_a(event):
    # Select all items when CTRL + A is pressed
    if event.state & 0x4:  # CTRL key is pressed
        device_listbox.selection_set(0, tk.END)


def auto_sort_scrcpy_windows():
    # Get all active scrcpy windows
    scrcpy_windows = [win for win in gw.getWindowsWithTitle('SM-') if win.visible]
    num_windows = len(scrcpy_windows)
    
    if num_windows == 0:
        messagebox.showinfo("No Active scrcpy Windows", "No active scrcpy windows found.")
        return

    # Get the screen size
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # Calculate grid dimensions (rows and columns)
    if num_windows <= 3:
        rows, cols = 1, num_windows
    else:
        rows = 2
        cols = (num_windows + 1) // 2  # Ensure the grid can fit all windows

    # Calculate the size of each window
    window_width = screen_width // cols
    window_height = screen_height // rows

    # Arrange the windows in a grid
    for i, window in enumerate(scrcpy_windows):
        row = i // cols
        col = i % cols
        x = col * window_width
        y = row * window_height
        window.moveTo(x, y)
        window.resizeTo(window_width, window_height)


def start_scrcpy(serial):
    try:
        scrcpy_path = r"C:\Users\Chaos\Documents\scrcpy-win64-v2.4\scrcpy.exe"  # Replace this with the full path to scrcpy
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

def start_scrcpy_tcpip(ip_address):
    try:
        scrcpy_path = r"C:\Users\Chaos\Documents\scrcpy-win64-v2.4\scrcpy.exe"  # Replace this with the full path to scrcpy
        print("Starting scrcpy with device (TCP/IP):", ip_address)
        command = [scrcpy_path, '--tcpip=' + ip_address]
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
        selected_device_display = device_listbox.get(selected_index[0])
        serial = selected_device_display.split(' -- ')[0]
        print("Selected device:", serial)


def refresh_device_list(search_text=""):
    print("Refreshing device list...")
    device_listbox.delete(0, tk.END)
    devices = get_connected_devices()
    user_mapping = load_user_mapping()
    for device in devices:
        display_name = f"{device} -- {user_mapping[device]}" if device in user_mapping else device
        if search_text.lower() in display_name.lower():
            device_listbox.insert(tk.END, display_name)


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
    selected_indices = device_listbox.curselection()
    if selected_indices:
        user_mapping = load_user_mapping()
        for selected_index in selected_indices:
            selected_device_display = device_listbox.get(selected_index)
            serial = selected_device_display.split(' -- ')[0]
            print(f"Connecting device: {serial}")
            start_scrcpy(serial)
            time.sleep(1)


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

def list_enabled_network_interfaces():
    interfaces = psutil.net_if_addrs()
    interface_stats = psutil.net_if_stats()

    enabled_interfaces = []
    for iface, stats in interface_stats.items():
        if stats.isup:
            ip_addresses = [addr.address for addr in interfaces.get(iface, []) if addr.family == 2]
            enabled_interfaces.append((iface, ip_addresses))
    return enabled_interfaces

def display_interfaces(filter_text=""):
    # Clear the listbox before refreshing
    listbox.delete(0, tk.END)

    interfaces = list_enabled_network_interfaces()
    for iface, ips in interfaces:
        display_text = f"{iface} -- {', '.join(ips)}"
        if filter_text.lower() in display_text.lower():
            listbox.insert(tk.END, display_text)

def refresh_interfaces():
    display_interfaces(search_var.get())

def search_interfaces(*args):
    display_interfaces(search_var.get())


# Set appearance mode to dark and use a custom dark background color
ctk.set_appearance_mode("dark")
bg_color = "#1e1e1e"  # Dark gray background color
fg_color = "#ffffff"  # White foreground (text) color

# Initialize the main window
root = ctk.CTk()
root.title("Device Controller")
console_window = None

root.geometry("800x600")

# Create a notebook with two tabs using ttk.Notebook
tabview = ctk.CTkTabview(master=root)


tabview.pack(fill="both", expand=True, padx=20, pady=20)

main_frame = tabview.add("Main")
end_points = tabview.add("Endpoints")
proxy_tab  = tabview.add("Proxies")

# Endpoints frame and widgets
endpoints_frame = ctk.CTkFrame(end_points)
endpoints_frame.pack(side=ctk.TOP, fill=ctk.BOTH, padx=10, pady=5)

port_label = ctk.CTkLabel(endpoints_frame, text="Port:")
port_label.pack(side=ctk.LEFT)

port_entry = ctk.CTkEntry(endpoints_frame, width=100)
port_entry.pack(side=ctk.LEFT, padx=5)

serial_label = ctk.CTkLabel(endpoints_frame, text="Serial")
serial_label.pack(side=ctk.LEFT)

serial_entry = ctk.CTkEntry(endpoints_frame, width=100)
serial_entry.pack(side=ctk.LEFT, padx=5)

create_endpoint_button = ctk.CTkButton(endpoints_frame, text="Create Endpoint", command=create_custom_endpoint)
create_endpoint_button.pack(side=ctk.LEFT, padx=5)


save_endpoints_button = ctk.CTkButton(endpoints_frame, text="Save Endpoints", command=save_endpoints)
save_endpoints_button.pack(side=ctk.LEFT, padx=5)


load_endpoints_button = ctk.CTkButton(endpoints_frame, text="Load Endpoints", command=load_endpoints)
load_endpoints_button.pack(side=ctk.LEFT, padx=5)


# Main frame and widgets
search_frame = ctk.CTkFrame(main_frame)
search_frame.pack(side=ctk.TOP, fill=ctk.X, padx=10, pady=5)

search_label = ctk.CTkLabel(search_frame, text="Search:")
search_label.pack(side=ctk.LEFT)

search_entry = ctk.CTkEntry(search_frame, width=100)
search_entry.pack(side=ctk.LEFT, padx=5)
search_entry.bind("<KeyRelease>", lambda event: refresh_device_list(search_entry.get()))

device_frame = ctk.CTkFrame(main_frame)
device_frame.pack(side=ctk.TOP, fill=ctk.BOTH, padx=10, pady=5, expand=True)

device_label = ctk.CTkLabel(device_frame, text="Connected Devices")
device_label.pack()

device_listbox = tk.Listbox(device_frame, bg="#333333", fg="#FFFFFF", selectbackground="#444444",
                            selectforeground="#FFFFFF", activestyle='none', font=("Arial", 12),
                            selectmode=tk.EXTENDED)  # Enable multiple selections

device_listbox.pack(pady=5, fill=tk.BOTH, expand=True)

# Bind mouse and key events for selection behavior
device_listbox.bind("<Button-1>", on_listbox_click)  # Single and multi-click
device_listbox.bind("<Control-a>", on_ctrl_a)  # CTRL + A to select all


buttons_frame = ctk.CTkFrame(main_frame)
buttons_frame.pack(side=ctk.BOTTOM, fill=ctk.X, padx=10, pady=5)

refresh_button = ctk.CTkButton(buttons_frame, text="Refresh", command=lambda: refresh_device_list(search_entry.get()))
refresh_button.pack(side=ctk.LEFT, padx=5)

rename_button = ctk.CTkButton(buttons_frame, text="Rename", command=rename_device)
rename_button.pack(side=ctk.LEFT, padx=5)

connect_button = ctk.CTkButton(buttons_frame, text="Connect", command=connect_device)
connect_button.pack(side=ctk.LEFT, padx=5)

# Add the button to the main frame
auto_sort_button = ctk.CTkButton(buttons_frame, text="Auto Sort Windows", command=auto_sort_scrcpy_windows)
auto_sort_button.pack(side=ctk.LEFT, padx=5)

console_button = ctk.CTkButton(buttons_frame, text="Show Console", command=show_console)
console_button.pack(side=ctk.RIGHT, padx=5)



# Endpoints Listbox and kill server section
endpoints_listbox = tk.Listbox(end_points , bg="#333333", fg="#FFFFFF", selectbackground="#444444", selectforeground="#FFFFFF", activestyle='none', font=("Arial", 12))
endpoints_listbox.pack(pady=5, fill=tk.BOTH, expand=True)

serial_kill_frame = ctk.CTkFrame(end_points)
serial_kill_frame.pack(side=ctk.BOTTOM, fill=ctk.X, padx=10, pady=5)

serial_kill_label = ctk.CTkLabel(serial_kill_frame, text="Enter Serial to Kill Server:")
serial_kill_label.pack(side=ctk.LEFT)

serial_kill_entry = ctk.CTkEntry(serial_kill_frame, width=100)
serial_kill_entry.pack(side=ctk.LEFT, padx=5)

kill_button = ctk.CTkButton(serial_kill_frame, text="Kill Server", command=kill_server_by_serial)
kill_button.pack(side=ctk.LEFT, padx=5)




network_interface_label = ctk.CTkLabel(proxy_tab, text="Network Interfaces")
network_interface_label.pack()

# Search box
search_var = tk.StringVar()
search_var.trace("w", search_interfaces)
search_entry = ctk.CTkEntry(tabview.tab("Proxies"), textvariable=search_var, placeholder_text="Search...")
search_entry.pack(pady=10, padx=10, fill="x")

# Listbox with a scrollbar
listbox_frame = ctk.CTkFrame(tabview.tab("Proxies"))
listbox_frame.pack(fill="both", expand=True, padx=10, pady=10)

listbox = tk.Listbox(listbox_frame, bg="#333333", fg="#FFFFFF", selectbackground="#444444", selectforeground="#FFFFFF", activestyle='none', font=("Arial", 12))
listbox.pack(side="left", fill="both", expand=True)

scrollbar = ctk.CTkScrollbar(listbox_frame, command=listbox.yview)
scrollbar.pack(side="right", fill="y")
listbox.config(yscrollcommand=scrollbar.set)

# Refresh button at the bottom
refresh_button = ctk.CTkButton(tabview.tab("Proxies"), text="Refresh", command=refresh_interfaces)
refresh_button.pack(pady=10, side="bottom")

display_interfaces()
# Start updating the list of running endpoints periodically
refresh_running_endpoints()



# Run the main loop
root.mainloop()
