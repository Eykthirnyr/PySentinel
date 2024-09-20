import subprocess
import sys
import os
import tkinter as tk
from tkinter import ttk
import psutil
import GPUtil  # For GPU monitoring
import wmi  # For disk usage monitoring on Windows
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import time
import configparser
import socket
import csv
import threading
from email_sender import send_drive_space_alert, send_threshold_alert, send_daily_report, send_email

# Setup the path for the configuration file
CONFIG_DIR = os.path.join(os.getcwd(), 'config')
CONFIG_FILE_PATH = os.path.join(CONFIG_DIR, 'config.ini')

def check_and_install_dependencies():
    required_packages = {
        'psutil': 'psutil',
        'matplotlib': 'matplotlib',
        'pandas': 'pandas',
        'setuptools': 'setuptools',
        'pyarrow': 'pyarrow',
        'GPUtil': 'GPUtil',  # Added GPUtil for GPU monitoring
        'WMI': 'wmi'  # Added WMI for disk usage monitoring on Windows
    }

    for package_name, module_name in required_packages.items():
        try:
            __import__(module_name)
        except ImportError:
            print(f"{package_name} not found. Installing...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
            print(f"{package_name} installed successfully.")

def load_settings():
    """Load settings from the config.ini file."""
    config = configparser.ConfigParser()
    if not os.path.exists(CONFIG_FILE_PATH):
        return  # If config file doesn't exist, skip loading
    
    config.read(CONFIG_FILE_PATH)
    # Load settings
    settings['refresh_rate'] = config.getint('General', 'refresh_rate', fallback=60)
    settings['smtp_server'] = config.get('Email', 'smtp_server', fallback='')
    settings['smtp_port'] = config.get('Email', 'smtp_port', fallback='')
    settings['smtp_username'] = config.get('Email', 'smtp_username', fallback='')
    settings['smtp_password'] = config.get('Email', 'smtp_password', fallback='')
    settings['email_recipient'] = config.get('Email', 'email_recipient', fallback='')
    settings['email_interval'] = config.getint('Email', 'email_interval', fallback=5)
    settings['send_on_threshold_violation'] = config.getint('Email', 'send_on_threshold_violation', fallback=0)

    # Ensure thresholds are integers; convert if they are floats
    settings['cpu_min_threshold'] = int(float(config.get('Thresholds', 'cpu_min_threshold', fallback=0)))
    settings['cpu_max_threshold'] = int(float(config.get('Thresholds', 'cpu_max_threshold', fallback=100)))
    settings['ram_min_threshold'] = int(float(config.get('Thresholds', 'ram_min_threshold', fallback=0)))
    settings['ram_max_threshold'] = int(float(config.get('Thresholds', 'ram_max_threshold', fallback=100)))
    settings['disk_min_threshold'] = int(float(config.get('Thresholds', 'disk_min_threshold', fallback=0)))
    settings['disk_max_threshold'] = int(float(config.get('Thresholds', 'disk_max_threshold', fallback=100)))
    settings['network_upload_min_threshold'] = int(float(config.get('Thresholds', 'network_upload_min_threshold', fallback=0)))
    settings['network_upload_max_threshold'] = int(float(config.get('Thresholds', 'network_upload_max_threshold', fallback=1000)))
    settings['network_download_min_threshold'] = int(float(config.get('Thresholds', 'network_download_min_threshold', fallback=0)))
    settings['network_download_max_threshold'] = int(float(config.get('Thresholds', 'network_download_max_threshold', fallback=1000)))
    
    # Load drive thresholds
    for partition in psutil.disk_partitions():
        drive_letter = partition.device.strip('\\')
        settings[f'drive_{drive_letter}_min_threshold'] = int(float(config.get('Thresholds', f'drive_{drive_letter}_min_threshold', fallback=10)))

def save_settings():
    """Save settings to the config.ini file."""
    config = configparser.ConfigParser()
    config['General'] = {
        'refresh_rate': str(settings['refresh_rate']),
    }
    config['Email'] = {
        'smtp_server': settings['smtp_server'],
        'smtp_port': settings['smtp_port'],
        'smtp_username': settings['smtp_username'],
        'smtp_password': settings['smtp_password'],
        'email_recipient': settings['email_recipient'],
        'email_interval': str(settings['email_interval']),
        'send_on_threshold_violation': str(settings['send_on_threshold_violation']),
    }
    config['Thresholds'] = {
        'cpu_min_threshold': str(settings['cpu_min_threshold']),
        'cpu_max_threshold': str(settings['cpu_max_threshold']),
        'ram_min_threshold': str(settings['ram_min_threshold']),
        'ram_max_threshold': str(settings['ram_max_threshold']),
        'disk_min_threshold': str(settings['disk_min_threshold']),
        'disk_max_threshold': str(settings['disk_max_threshold']),
        'network_upload_min_threshold': str(settings['network_upload_min_threshold']),
        'network_upload_max_threshold': str(settings['network_upload_max_threshold']),
        'network_download_min_threshold': str(settings['network_download_min_threshold']),
        'network_download_max_threshold': str(settings['network_download_max_threshold']),
    }

    # Save drive thresholds
    for partition in psutil.disk_partitions():
        drive_letter = partition.device.strip('\\')
        config['Thresholds'][f'drive_{drive_letter}_min_threshold'] = str(settings.get(f'drive_{drive_letter}_min_threshold', 10))

    # Ensure the directory exists
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)

    # Write the settings to the config file
    with open(CONFIG_FILE_PATH, 'w') as configfile:
        config.write(configfile)

class RangeSlider(tk.Canvas):
    def __init__(self, parent, min_val, max_val, start_min, start_max, min_label, max_label, unit='', **kwargs):
        super().__init__(parent, **kwargs)  # Initialize the Canvas with parent and **kwargs
        
        self.min_val = min_val
        self.max_val = max_val
        self.start_min = start_min
        self.start_max = start_max
        self.unit = unit
        self.width = kwargs.get('width', 300)
        self.height = kwargs.get('height', 50)
        self.slider_width = 10
        self.range_line = None
        self.min_handle = None
        self.max_handle = None

        self.min_position = self.val_to_pos(start_min)
        self.max_position = self.val_to_pos(start_max)

        # Labels for displaying min and max values
        self.min_label_var = min_label
        self.max_label_var = max_label

        self.create_widgets()
        self.bind("<B1-Motion>", self.move_handle)

    def create_widgets(self):
        # Draw the range line
        self.range_line = self.create_line(self.slider_width, self.height // 2, self.width - self.slider_width, self.height // 2, fill='gray', width=2)

        # Draw the min and max handles
        self.min_handle = self.create_rectangle(self.min_position - self.slider_width // 2, (self.height // 2) - 5,
                                                self.min_position + self.slider_width // 2, (self.height // 2) + 5, fill='blue')
        self.max_handle = self.create_rectangle(self.max_position - self.slider_width // 2, (self.height // 2) - 5,
                                                self.max_position + self.slider_width // 2, (self.height // 2) + 5, fill='red')
        
        # Initialize labels
        self.update_labels()

    def val_to_pos(self, value):
        """Convert value to canvas position."""
        range_width = self.width - 2 * self.slider_width
        return self.slider_width + (value - self.min_val) / (self.max_val - self.min_val) * range_width

    def pos_to_val(self, pos):
        """Convert canvas position to value."""
        range_width = self.width - 2 * self.slider_width
        return self.min_val + (pos - self.slider_width) / range_width * (self.max_val - self.min_val)

    def move_handle(self, event):
        """Move the min or max handle."""
        if self.min_handle is not None and self.max_handle is not None:
            # Get the x-coordinate of the event
            x = event.x
            # Determine which handle to move
            if abs(x - self.coords(self.min_handle)[0]) < abs(x - self.coords(self.max_handle)[0]):
                # Move min handle
                if self.slider_width <= x <= self.coords(self.max_handle)[0]:
                    self.coords(self.min_handle, x - self.slider_width // 2, (self.height // 2) - 5, x + self.slider_width // 2, (self.height // 2) + 5)
                    self.min_position = x
            else:
                # Move max handle
                if self.coords(self.min_handle)[2] <= x <= self.width - self.slider_width:
                    self.coords(self.max_handle, x - self.slider_width // 2, (self.height // 2) - 5, x + self.slider_width // 2, (self.height // 2) + 5)
                    self.max_position = x

            # Update labels
            self.update_labels()

    def update_labels(self):
        """Update the min and max labels."""
        self.min_label_var.set(f"Min: {self.get_min_value():.0f}{self.unit}")
        self.max_label_var.set(f"Max: {self.get_max_value():.0f}{self.unit}")

    def get_min_value(self):
        """Get the minimum value."""
        return self.pos_to_val(self.min_position)

    def get_max_value(self):
        """Get the maximum value."""
        return self.pos_to_val(self.max_position)

class LiveGraph:
    def __init__(self, parent, plot_type):
        self.figure, self.ax = plt.subplots(figsize=(8, 4))  # Adjust the size to make the GUI more compact
        self.canvas = FigureCanvasTkAgg(self.figure, parent)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.plot_type = plot_type
        self.data = {'cpu': [], 'ram': [], 'disk': [], 'gpu': [], 'network_in': [], 'network_out': []}
        self.time_stamps = []
        self.max_data_points = 20

        # Store the initial network I/O counters to initialize cumulative data to 0
        self.initial_net_io = psutil.net_io_counters()

        # Initialize WMI for disk usage monitoring
        self.wmi_interface = wmi.WMI()
        
        # CSV-related attributes
        self.machine_name = socket.gethostname()
        self.current_date = time.strftime("%Y-%m-%d")
        self.csv_file_path = self.create_csv_file()

        # Initialize graphs
        self.update_plot(None)

    def create_csv_file(self):
        """Create a new CSV file for the current day."""
        filename = f"{self.machine_name}_{self.current_date}.csv"
        file_path = os.path.join(os.getcwd(), filename)
        # Create the file and write the header
        with open(file_path, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Date', 'Time', 'CPU Usage (%)', 'RAM Usage (%)', 'Disk Usage (%)', 
                             'GPU Usage (%)', 'Network In (MB)', 'Network Out (MB)'])
        return file_path

    def write_to_csv(self, data_row):
        """Write a row of data to the CSV file."""
        with open(self.csv_file_path, 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(data_row)

    def get_gpu_usage(self):
        """Fetch the current GPU usage using GPUtil."""
        gpus = GPUtil.getGPUs()
        if gpus:
            return gpus[0].load * 100  # GPU load is a fraction, convert to percentage
        else:
            return 0  # No GPU found

    def get_disk_usage(self):
        """Fetch disk usage percentage using WMI."""
        disk_usage_percentage = 0
        try:
            for disk in self.wmi_interface.Win32_PerfFormattedData_PerfDisk_LogicalDisk():
                if disk.Name == "_Total":  # Use "_Total" to get the overall disk usage
                    disk_usage_percentage = float(disk.PercentDiskTime)
                    break
        except Exception as e:
            print(f"Error getting disk usage: {e}")
        # Ensure the disk usage percentage is clamped between 0 and 100
        disk_usage_percentage = max(0, min(disk_usage_percentage, 100))
        return disk_usage_percentage

    def update_plot(self, frame):
        current_time = time.strftime("%H:%M:%S")
        current_date = time.strftime("%Y-%m-%d")
        self.time_stamps.append(current_time)
        
        if len(self.time_stamps) > self.max_data_points:
            self.time_stamps.pop(0)
            for key in self.data:
                self.data[key].pop(0)
        
        # Collect data
        cpu_usage = psutil.cpu_percent(interval=1)
        ram_usage = psutil.virtual_memory().percent
        disk_usage = self.get_disk_usage()  # Updated disk usage
        gpu_usage = self.get_gpu_usage()
        # Update GPU usage using GPUtil
        self.data['cpu'].append(cpu_usage)
        self.data['ram'].append(ram_usage)
        self.data['disk'].append(disk_usage)
        self.data['gpu'].append(gpu_usage)

        # Get the current network I/O counters
        current_net_io = psutil.net_io_counters()

        # Calculate cumulative data by subtracting initial counters
        network_in_cumulative = (current_net_io.bytes_recv - self.initial_net_io.bytes_recv) / (1024 * 1024)
        network_out_cumulative = (current_net_io.bytes_sent - self.initial_net_io.bytes_sent) / (1024 * 1024)

        # Append cumulative data to the graph data
        self.data['network_in'].append(network_in_cumulative)
        self.data['network_out'].append(network_out_cumulative)

        # Write to CSV
        data_row = [
            current_date, current_time, cpu_usage, ram_usage, disk_usage, 
            gpu_usage, network_in_cumulative, network_out_cumulative
        ]
        self.write_to_csv(data_row)

        # Create a new CSV file if the day has changed
        if current_date != self.current_date:
            self.current_date = current_date
            self.csv_file_path = self.create_csv_file()

        # Clear the plot
        self.ax.clear()

        if self.plot_type == "system":
            # Update CPU, RAM, Disk, and GPU Usage plot
            self.ax.plot(self.time_stamps, self.data['cpu'], label='CPU Usage')
            self.ax.plot(self.time_stamps, self.data['ram'], label='RAM Usage')
            self.ax.plot(self.time_stamps, self.data['disk'], label='Disk Usage')
            self.ax.plot(self.time_stamps, self.data['gpu'], label='GPU Usage')
            self.ax.set_title('System Resources Over Time')
            self.ax.set_ylabel('Usage (%)')
            self.ax.set_ylim(0, 100)  # Set the y-axis limits to 0-100%
        
        elif self.plot_type == "network":
            # Update Network Usage plot
            self.ax.plot(self.time_stamps, self.data['network_in'], label='Network In')
            self.ax.plot(self.time_stamps, self.data['network_out'], label='Network Out')
            self.ax.set_title('Network Cumulative Data Usage Over Time')
            self.ax.set_ylabel('Cumulative Data (MB)')

        self.ax.legend(loc='upper left')
        self.ax.set_xlabel('Time')
        self.ax.set_xticks(self.time_stamps)
        self.ax.set_xticklabels(self.time_stamps, rotation=90)  # Rotate time labels 90 degrees
        
        self.canvas.draw()

def create_drive_frame(drive, drive_info):
    """Create a frame for each drive with threshold settings and options."""
    global drive_sliders  # Use the global drive_sliders dictionary
    drive_frame = tk.LabelFrame(drive_tab, text=f"Drive {drive}: {drive_info['total']} GB total")
    drive_frame.pack(fill="x", padx=10, pady=5)

    # Space Thresholds
    threshold_label = tk.Label(drive_frame, text="Occupied Space Threshold (GB):")
    threshold_label.pack(anchor="w")
    min_label = tk.StringVar()
    max_label = tk.StringVar()
    drive_slider = RangeSlider(drive_frame, 0, drive_info['total'], 0, drive_info['total'] * 0.8, min_label, max_label, unit=' GB', width=300, height=50)
    drive_slider.pack()
    min_display = tk.Label(drive_frame, textvariable=min_label, width=15)
    min_display.pack(side="left", padx=(5, 0))
    max_display = tk.Label(drive_frame, textvariable=max_label, width=15)
    max_display.pack(side="left")

    # Store the slider in the global dictionary
    drive_letter = drive.strip(':\\')
    drive_sliders[drive_letter] = drive_slider

settings = {
    'refresh_rate': 60,
    'smtp_server': '',
    'smtp_port': '',
    'smtp_username': '',
    'smtp_password': '',
    'email_recipient': '',
    'email_interval': 5,
    'send_on_threshold_violation': 0,
    'cpu_min_threshold': 0,
    'cpu_max_threshold': 100,
    'ram_min_threshold': 0,
    'ram_max_threshold': 100,
    'disk_min_threshold': 0,
    'disk_max_threshold': 100,
    'network_upload_min_threshold': 0,
    'network_upload_max_threshold': 1000,
    'network_download_min_threshold': 0,
    'network_download_max_threshold': 1000,
}

# Global dictionary to store drive sliders
drive_sliders = {}

def apply_settings():
    global refresh_rate_entry, smtp_entry, port_entry, username_entry, password_entry, recipient_entry
    global interval_entry, send_on_threshold_var
    global cpu_slider, ram_slider, disk_slider, upload_slider, download_slider
    global drive_sliders  # Access the drive sliders dictionary

    # Apply refresh rate
    try:
        new_refresh_rate = int(refresh_rate_entry.get())
        settings['refresh_rate'] = new_refresh_rate if new_refresh_rate > 0 else 60
    except ValueError:
        settings['refresh_rate'] = 60  # Default to 60 seconds

    # Apply email settings
    settings['smtp_server'] = smtp_entry.get()
    settings['smtp_port'] = port_entry.get()
    settings['smtp_username'] = username_entry.get()
    settings['smtp_password'] = password_entry.get()
    settings['email_recipient'] = recipient_entry.get()

    # Apply email interval
    try:
        new_email_interval = int(interval_entry.get())
        settings['email_interval'] = new_email_interval if new_email_interval > 0 else 5
    except ValueError:
        settings['email_interval'] = 5  # Default to 5 minutes
    
    settings['send_on_threshold_violation'] = send_on_threshold_var.get()

    # Apply thresholds
    settings['cpu_min_threshold'] = int(cpu_slider.get_min_value())  # Use int to ensure the correct type
    settings['cpu_max_threshold'] = int(cpu_slider.get_max_value())
    settings['ram_min_threshold'] = int(ram_slider.get_min_value())
    settings['ram_max_threshold'] = int(ram_slider.get_max_value())
    settings['disk_min_threshold'] = int(disk_slider.get_min_value())
    settings['disk_max_threshold'] = int(disk_slider.get_max_value())
    settings['network_upload_min_threshold'] = int(upload_slider.get_min_value())
    settings['network_upload_max_threshold'] = int(upload_slider.get_max_value())
    settings['network_download_min_threshold'] = int(download_slider.get_min_value())
    settings['network_download_max_threshold'] = int(download_slider.get_max_value())

    # Save drive thresholds using the drive sliders
    for drive_letter, slider in drive_sliders.items():
        settings[f'drive_{drive_letter}_min_threshold'] = int(slider.get_min_value())

    # Save settings to config file
    save_settings()

    # Display a message indicating the settings have been applied
    print("Settings have been applied.")
    print(f"Current Settings: {settings}")

def send_test_email():
    """Send a test email using the current SMTP settings."""
    def email_thread():
        try:
            print("Sending test email...")
            send_email(
                subject=f"Test Email from {socket.gethostname()}",
                body="This is a test email to verify the SMTP settings."
            )
            print("Test email sent successfully.")
        except Exception as e:
            print(f"Failed to send test email: {e}")
    
    # Run the email sending in a separate thread to avoid freezing the GUI
    threading.Thread(target=email_thread).start()

def monitor_drive_space():
    """Monitor the free space of each drive and send an alert if below the threshold."""
    def email_thread(drive_letter, free_space_gb):
        try:
            print(f"Sending email alert for drive {drive_letter} with free space: {free_space_gb:.2f} GB")
            send_drive_space_alert(drive_letter, free_space_gb)
        except Exception as e:
            print(f"Failed to send email alert for drive space: {e}")
    
    for partition in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            free_space_gb = usage.free / (1024 ** 3)  # Convert bytes to GB
            
            # Get thresholds from settings (assumes thresholds are saved for each drive, e.g., drive_C_min_threshold)
            drive_letter = partition.device.strip('\\')
            min_threshold = settings.get(f'drive_{drive_letter}_min_threshold', 10)  # Default threshold to 10GB
            
            # Check if the free space is below the threshold
            if free_space_gb < min_threshold:
                # Trigger an alert in a separate thread to avoid freezing the GUI
                threading.Thread(target=email_thread, args=(drive_letter, free_space_gb)).start()
        except PermissionError:
            print(f"Permission denied for {partition.device}")

def start_monitoring(root):
    """Start the periodic monitoring process."""
    monitor_drive_space()  # Check drive space
    # Call other monitoring functions as needed, e.g., monitor_thresholds()

    # Schedule next check (e.g., every minute)
    root.after(60 * 1000, start_monitoring, root)  # Pass `root` as an argument

def setup_gui():
    global refresh_rate_entry, smtp_entry, port_entry, username_entry, password_entry, recipient_entry
    global interval_entry, send_on_threshold_var
    global cpu_slider, ram_slider, disk_slider, upload_slider, download_slider
    global drive_tab  # Make sure drive_tab is accessible
    
    # Load settings from the config file
    load_settings()
    
    root = tk.Tk()
    root.title("System Monitoring Tool")
    root.geometry("800x600")  # Adjusted the default window size to make it more compact

    # Create notebook for tabs
    notebook = ttk.Notebook(root)
    main_tab = ttk.Frame(notebook)
    network_tab = ttk.Frame(notebook)  # New Network Tab
    settings_tab = ttk.Frame(notebook)
    drive_tab = ttk.Frame(notebook)  # Define the drive_tab variable here

    notebook.add(main_tab, text="Main")
    notebook.add(network_tab, text="Network")  # Add the new Network Tab
    notebook.add(settings_tab, text="Settings")
    notebook.add(drive_tab, text="Drives")  # Add Drive Tab
    notebook.pack(expand=True, fill='both')

    # Setup Main Tab for System Resources
    live_graph_system = LiveGraph(main_tab, plot_type="system")

    # Setup Network Tab for Network Usage
    live_graph_network = LiveGraph(network_tab, plot_type="network")

    # Setup Drive Tab
    drive_label = tk.Label(drive_tab, text="Drive Monitoring", font=("Arial", 14))
    drive_label.pack(pady=10)

    # Get available drives and create frames
    partitions = psutil.disk_partitions()
    for partition in partitions:
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            drive_info = {
                'total': usage.total // (1024 ** 3),  # Convert to GB
            }
            create_drive_frame(partition.device, drive_info)
        except PermissionError:
            # Handle the case where access to a partition is restricted
            print(f"Permission denied for {partition.device}")

    # Setup Settings Tab
    settings_label = tk.Label(settings_tab, text="Settings", font=("Arial", 14))
    settings_label.pack(pady=10)

    # Email Settings
    email_frame = tk.LabelFrame(settings_tab, text="Email Settings", padx=10, pady=10)
    email_frame.pack(padx=10, pady=10, fill="x")

    smtp_label = tk.Label(email_frame, text="SMTP Server:")
    smtp_label.pack(anchor="w")
    smtp_entry = tk.Entry(email_frame)
    smtp_entry.pack(fill="x")
    smtp_entry.insert(0, settings['smtp_server'])  # Insert saved value

    port_label = tk.Label(email_frame, text="Port:")
    port_label.pack(anchor="w")
    port_entry = tk.Entry(email_frame)
    port_entry.pack(fill="x")
    port_entry.insert(0, settings['smtp_port'])  # Insert saved value

    username_label = tk.Label(email_frame, text="Username:")
    username_label.pack(anchor="w")
    username_entry = tk.Entry(email_frame)
    username_entry.pack(fill="x")
    username_entry.insert(0, settings['smtp_username'])  # Insert saved value

    password_label = tk.Label(email_frame, text="Password:")
    password_label.pack(anchor="w")
    password_entry = tk.Entry(email_frame, show="*")
    password_entry.pack(fill="x")
    password_entry.insert(0, settings['smtp_password'])  # Insert saved value

    recipient_label = tk.Label(email_frame, text="Recipient Email:")
    recipient_label.pack(anchor="w")
    recipient_entry = tk.Entry(email_frame)
    recipient_entry.pack(fill="x")
    recipient_entry.insert(0, settings['email_recipient'])  # Insert saved value

    # Email Interval and Threshold Violation Settings
    email_interval_frame = tk.LabelFrame(settings_tab, text="Email Sending Options", padx=10, pady=10)
    email_interval_frame.pack(padx=10, pady=10, fill="x")

    interval_label = tk.Label(email_interval_frame, text="Email Interval (minutes):")
    interval_label.pack(anchor="w")
    interval_entry = tk.Entry(email_interval_frame)
    interval_entry.pack(fill="x")
    interval_entry.insert(0, str(settings['email_interval']))  # Insert saved value

    send_on_threshold_var = tk.IntVar(value=settings['send_on_threshold_violation'])  # Set saved value
    send_on_threshold_checkbox = tk.Checkbutton(email_interval_frame, text="Send email if a value is outside of threshold for 3 consecutive minutes", variable=send_on_threshold_var)
    send_on_threshold_checkbox.pack(anchor="w")

    # Send Test Email Button
    test_email_button = tk.Button(settings_tab, text="Send Test Email", command=send_test_email)
    test_email_button.pack(pady=5)

    # Threshold Settings
    threshold_frame = tk.LabelFrame(settings_tab, text="Threshold Settings", padx=10, pady=10)
    threshold_frame.pack(padx=10, pady=10, fill="x")

    # CPU Usage Threshold
    cpu_frame = tk.Frame(threshold_frame)
    cpu_frame.pack(pady=5, fill="x")
    cpu_threshold_label = tk.Label(cpu_frame, text="CPU Usage Threshold (%):")
    cpu_threshold_label.pack(side="left")
    cpu_min_label = tk.StringVar()
    cpu_max_label = tk.StringVar()
    cpu_slider = RangeSlider(cpu_frame, 0, 100, settings['cpu_min_threshold'], settings['cpu_max_threshold'], cpu_min_label, cpu_max_label, unit='%', width=300, height=50)  # Use saved values
    cpu_slider.pack(side="left")
    cpu_min_display = tk.Label(cpu_frame, textvariable=cpu_min_label, width=10)
    cpu_min_display.pack(side="left")
    cpu_max_display = tk.Label(cpu_frame, textvariable=cpu_max_label, width=10)
    cpu_max_display.pack(side="left")

    # RAM Usage Threshold
    ram_frame = tk.Frame(threshold_frame)
    ram_frame.pack(pady=5, fill="x")
    ram_threshold_label = tk.Label(ram_frame, text="RAM Usage Threshold (%):")
    ram_threshold_label.pack(side="left")
    ram_min_label = tk.StringVar()
    ram_max_label = tk.StringVar()
    ram_slider = RangeSlider(ram_frame, 0, 100, settings['ram_min_threshold'], settings['ram_max_threshold'], ram_min_label, ram_max_label, unit='%', width=300, height=50)  # Use saved values
    ram_slider.pack(side="left")
    ram_min_display = tk.Label(ram_frame, textvariable=ram_min_label, width=10)
    ram_min_display.pack(side="left")
    ram_max_display = tk.Label(ram_frame, textvariable=ram_max_label, width=10)
    ram_max_display.pack(side="left")

    # Disk Usage Threshold
    disk_frame = tk.Frame(threshold_frame)
    disk_frame.pack(pady=5, fill="x")
    disk_threshold_label = tk.Label(disk_frame, text="Disk Usage Threshold (%):")
    disk_threshold_label.pack(side="left")
    disk_min_label = tk.StringVar()
    disk_max_label = tk.StringVar()
    disk_slider = RangeSlider(disk_frame, 0, 100, settings['disk_min_threshold'], settings['disk_max_threshold'], disk_min_label, disk_max_label, unit='%', width=300, height=50)  # Use saved values
    disk_slider.pack(side="left")
    disk_min_display = tk.Label(disk_frame, textvariable=disk_min_label, width=10)
    disk_min_display.pack(side="left")
    disk_max_display = tk.Label(disk_frame, textvariable=disk_max_label, width=10)
    disk_max_display.pack(side="left")

    # Network Upload Threshold
    upload_frame = tk.Frame(threshold_frame)
    upload_frame.pack(pady=5, fill="x")
    upload_threshold_label = tk.Label(upload_frame, text="Network Upload Threshold (Mbps):")
    upload_threshold_label.pack(side="left")
    upload_min_label = tk.StringVar()
    upload_max_label = tk.StringVar()
    upload_slider = RangeSlider(upload_frame, 0, 1000, settings['network_upload_min_threshold'], settings['network_upload_max_threshold'], upload_min_label, upload_max_label, unit=' Mbps', width=300, height=50)  # Use saved values
    upload_slider.pack(side="left")
    upload_min_display = tk.Label(upload_frame, textvariable=upload_min_label, width=10)
    upload_min_display.pack(side="left", padx=(5, 50))  # Add 100 pixels space between labels
    upload_max_display = tk.Label(upload_frame, textvariable=upload_max_label, width=10)
    upload_max_display.pack(side="left", padx=(5, 50))  # Add 100 pixels space between labels

    # Network Download Threshold
    download_frame = tk.Frame(threshold_frame)
    download_frame.pack(pady=5, fill="x")
    download_threshold_label = tk.Label(download_frame, text="Network Download Threshold (Mbps):")
    download_threshold_label.pack(side="left")
    download_min_label = tk.StringVar()
    download_max_label = tk.StringVar()
    download_slider = RangeSlider(download_frame, 0, 1000, settings['network_download_min_threshold'], settings['network_download_max_threshold'], download_min_label, download_max_label, unit=' Mbps', width=300, height=50)  # Use saved values
    download_slider.pack(side="left")
    download_min_display = tk.Label(download_frame, textvariable=download_min_label, width=10)
    download_min_display.pack(side="left", padx=(5, 50))  # Add 100 pixels space between labels
    download_max_display = tk.Label(download_frame, textvariable=download_max_label, width=10)
    download_max_display.pack(side="left", padx=(5, 50))  # Add 100 pixels space between labels


    # Monitoring Refresh Rate - Moved to the bottom of the settings tab
    refresh_rate_frame = tk.LabelFrame(settings_tab, text="Monitoring Refresh Rate", padx=10, pady=10)
    refresh_rate_frame.pack(padx=10, pady=10, fill="x")

    refresh_rate_label = tk.Label(refresh_rate_frame, text="Refresh Rate (seconds):")
    refresh_rate_label.pack(anchor="w")
    refresh_rate_entry = tk.Entry(refresh_rate_frame)
    refresh_rate_entry.pack(fill="x")
    refresh_rate_entry.insert(0, str(settings['refresh_rate']))  # Insert saved value

    # Apply Button
    apply_button = tk.Button(settings_tab, text="Apply Settings", command=apply_settings)
    apply_button.pack(pady=10)

    # Function to update the graphs based on the refresh rate
    def update_graph():
        live_graph_system.update_plot(None)
        live_graph_network.update_plot(None)
        try:
            refresh_rate = settings['refresh_rate']  # Use the applied refresh rate from settings
        except ValueError:
            refresh_rate = 60  # Fallback default if parsing fails
        root.after(refresh_rate * 1000, update_graph)  # Convert to milliseconds

    update_graph()

    # Start monitoring process
    start_monitoring(root)

    # Start the GUI main loop
    root.mainloop()

if __name__ == "__main__":
    check_and_install_dependencies()
    setup_gui()
