import time
import serial
import serial.tools.list_ports
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import Tk, Label, Frame, ttk

# Global Variables
ylim = 100
curr = 0
ser = None  # Global serial variable
latest_peak = None  # Store the latest peak value
persistent_lines = []  # Store all persistent peak lines
dataList = []  # Data list for animation

# Serial Communication Functions
def get_available_ports():
    """ Returns a list of available COM ports """
    return [port.device for port in serial.tools.list_ports.comports()]

def select_port(event):
    """ Select and open the serial port """
    global ser
    selected_port = com_port_var.get()
    try:
        if ser and ser.is_open:
            ser.close()
        ser = serial.Serial(selected_port, 9600, timeout=1)
        time.sleep(2)
        serial_status_label.config(text=f"{selected_port} Active", fg="green")
    except serial.SerialException:
        serial_status_label.config(text=f"{selected_port} Inactive", fg="red")
        ser = None

def animate(frame, dataList, ax, label):
    """ Animation function to update plot with serial data """
    global ser, latest_peak, persistent_lines
    try:
        if ser and ser.is_open and ser.in_waiting:
            arduinoData_bytes = ser.readline()
            try:
                arduinoData_string = arduinoData_bytes.decode('utf-8', errors='ignore').strip()
                if arduinoData_string.replace('.', '', 1).isdigit():
                    arduinoData_float = float(arduinoData_string)
                    label.config(text=f"Current Reading: {arduinoData_float} oz")
                    dataList.append(arduinoData_float)
                elif arduinoData_string in ['px', 'pz']:
                    latest_peak = None
                    persistent_lines.clear()
                elif arduinoData_string.startswith('p') and len(arduinoData_string) > 2:
                    peak = float(arduinoData_string[2:])
                    latest_peak = peak
                    peak_cnt = arduinoData_string[1:]
                    ax.axhline(y=latest_peak, color='r', linestyle='--', label=f"Peak {peak_cnt}: {latest_peak}")
                    persistent_lines.append(latest_peak)
                elif arduinoData_string == "LP":
                    status_label.config(text="Status: Asleep", fg="red")
                elif arduinoData_string == "WU":
                    status_label.config(text="Status: Awake", fg="green")
            except ValueError:
                pass

        # Update the plot with the latest data
        dataList = dataList[-50:]
        ax.clear()
        ax.plot(dataList)
        ax.set_ylim([0, ylim])
        ax.set_ylabel("Tension (oz)")
        for index, peak in enumerate(persistent_lines):
            ax.axhline(y=peak, color='r', linestyle='--', label=f"Peak {index+1}: {peak}")
        if persistent_lines:
            ax.legend()
        return dataList
    except serial.SerialException:
        serial_status_label.config(text=f"{com_port_var.get()} Inactive", fg="red")
        return dataList

# Data Control Functions
def update_value(entry_widget, label):
    """ Update the threshold or calibration value """
    global ser
    value = entry_widget.get()
    try:
        value_float = float(value)
        command = f"T{value}" if label == "Threshold" else f"C{value}"
        if ser and ser.is_open:
            ser.write(command.encode('utf-8'))
            print(f"Sent {label}: {value}")
    except ValueError:
        print(f"Invalid input for {label}. Please enter a valid number.")

def clear_plot_data(dataList, ax):
    """ Clears the plot data and resets persistent lines """
    global persistent_lines, latest_peak
    dataList.clear()
    persistent_lines.clear()
    latest_peak = None
    ax.clear()
    ax.set_ylim([0, ylim])
    ax.set_title("Load Cell Data")
    ax.set_ylabel("Tension (oz)")
    canvas.draw()

def plt_increase():
    """ Increase the plot's y-axis limit """
    global ylim
    ylim += 50
    ax.set_ylim([0, ylim])
    canvas.draw()

def plt_decrease():
    """ Decrease the plot's y-axis limit """
    global ylim
    ylim = max(0, ylim - 50)
    ax.set_ylim([0, ylim])
    canvas.draw()

# UI Update Functions
def refresh_ports():
    """ Refresh the list of available COM ports """
    available_ports = get_available_ports()
    com_port_dropdown['values'] = available_ports
    if available_ports:
        com_port_var.set(available_ports[0])  # Set default to first available port
        select_port(None)  # Automatically select and open the first port
    else:
        com_port_var.set("")  # Clear selection if no ports are available
        serial_status_label.config(text="No COM Ports Found", fg="red")


def create_ui():
    """ Create and configure the Tkinter UI """
    global root, com_port_var, serial_status_label, label, status_label, canvas, ax, com_port_dropdown  

    # Create Tkinter window
    root = Tk()
    root.title('Thrash Detection Disconnector GUI')

    # Grid configuration
    root.grid_rowconfigure(0, weight=1, minsize=100)  # Plot row will expand
    root.grid_rowconfigure(1, weight=0)  # Status row will not expand
    root.grid_rowconfigure(2, weight=0)  # Controls row will not expand
    root.grid_rowconfigure(3, weight=0)  # Status row at the bottom

    root.grid_columnconfigure(0, weight=1)  # Sidebar frame for controls
    root.grid_columnconfigure(1, weight=3)  # Main frame for plot

    # Frame for Controls (Sidebar)
    controls_frame = Frame(root, bg='#E0E0E0')  # Set background color
    controls_frame.grid(row=0, column=0, sticky="nswe", padx=10, pady=5)

    controls_frame.grid_rowconfigure(0, weight=1)
    controls_frame.grid_rowconfigure(1, weight=1)
    controls_frame.grid_rowconfigure(2, weight=1)

    controls_frame.grid_columnconfigure(0, weight=1)
    controls_frame.grid_columnconfigure(1, weight=3)  # Ensure it takes up more space than other columns
    controls_frame.grid_columnconfigure(2, weight=1)

    status_frame = Frame(root, bg='lightgray')  # Set background color
    status_frame.grid(row=1, column=0, sticky="nswe", padx=10, pady=5)

    status_frame.grid_rowconfigure(0, weight=1)
    status_frame.grid_rowconfigure(1, weight=1)
    status_frame.grid_rowconfigure(2, weight=1)
    status_frame.grid_columnconfigure(0, weight=1)

    # Frame for Plot
    plot_frame = Frame(root, bg="#D3D3D3")  # Set background color
    plot_frame.grid(row=0, column=1, rowspan=3, sticky="nsew", padx=10, pady=5)
    plot_frame.grid_rowconfigure(0, weight=1)
    plot_frame.grid_columnconfigure(0, weight=1)

    # Serial Status Label
    serial_status_label = Label(status_frame, text="Select a COM Port", font=("Helvetica", 12))  # Set background color
    serial_status_label.grid(row=0, column=0, columnspan=1, sticky="ew", pady=5, padx=5)

    # Dropdown for COM port selection
    com_port_var = tk.StringVar()
    available_ports = get_available_ports()
    com_port_dropdown = ttk.Combobox(controls_frame, textvariable=com_port_var, values=available_ports, state="readonly")
    com_port_dropdown.grid(row=0, column=2, padx=5, pady=5, sticky="ew")  # Added sticky="ew" to expand horizontally
    com_port_dropdown.bind("<<ComboboxSelected>>", select_port)

    # Refresh Button
    refresh_button = tk.Button(controls_frame, text="Refresh Ports", command=refresh_ports)
    refresh_button.grid(row=0, column=0, padx=5, pady=5, columnspan=2, sticky="ew")  # Added sticky="ew" to expand horizontally

    # Threshold Controls
    threshold_value = tk.Entry(controls_frame, width=22)
    threshold_value.grid(row=1, column=2, padx=5, pady=5, sticky="ew")  # Added sticky="ew" to expand horizontally
    threshold_Send = tk.Button(controls_frame, text="Set Threshold", command=lambda: update_value(threshold_value, "Threshold"))
    threshold_Send.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="ew")  # Added sticky="ew" to expand horizontally

    # Calibration Controls
    calibration_value = tk.Entry(controls_frame, width=22)
    calibration_value.grid(row=2, column=2, padx=5, pady=5, sticky="ew")  # Added sticky="ew" to expand horizontally
    calibration_Send = tk.Button(controls_frame, text="Set Calibration", command=lambda: update_value(calibration_value, "Calibration"))
    calibration_Send.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky="ew")  # Added sticky="ew" to expand horizontally

    clear_button = tk.Button(controls_frame, text="Clear Plot", command=lambda: clear_plot_data(dataList, ax))
    clear_button.grid(row=3, column=2, padx=5, pady=5, sticky="ew")  # Added sticky="ew" to expand horizontally

    plt_decrease_button = tk.Button(controls_frame, text="Zoom In", command=plt_decrease)
    plt_decrease_button.grid(row=3, column=1, padx=5, pady=5, sticky="ew")  # Added sticky="ew" to expand horizontally

    plt_increase_button = tk.Button(controls_frame, text="Zoom Out", command=plt_increase)
    plt_increase_button.grid(row=3, column=0, padx=5, pady=5, sticky="ew")  # Added sticky="ew" to expand horizontally

    # Current Reading Label
    label = tk.Label(status_frame, text=f"Current Reading: {curr}", font=("Helvetica", 12))  
    label.grid(row=1, column=0, columnspan=3, sticky="ew", pady=5,  padx=5)

    # Device Status Label
    status_label = Label(status_frame, text="Status: Unknown", font=("Helvetica", 12, "bold"), fg="black")  
    status_label.grid(row=2, column=0, columnspan=3, sticky="ew", pady=5, padx=5)

    # Matplotlib Figure
    fig = plt.Figure(figsize=(5, 4), dpi=100)
    ax = fig.add_subplot(111)

    # Embed Plot in Tkinter
    canvas = FigureCanvasTkAgg(fig, plot_frame)
    canvas_widget = canvas.get_tk_widget()
    canvas_widget.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    fig.tight_layout()

    # Set up animation
    ani = animation.FuncAnimation(fig, animate, fargs=(dataList, ax, label), interval=100, save_count=50)

    # Start Tkinter Main Loop
    root.mainloop()

    # Close Serial Port on Exit
    if ser is not None and ser.is_open:
        ser.close()

# Call to create the UI
create_ui()
