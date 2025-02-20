import time
import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import Tk, Label, Frame

ylim = 100
curr = 0
ser = None  # Declare global serial variable
latest_peak = None  # Store the latest peak value
persistent_lines = []  # Store all persistent peak lines

def animate(frame, dataList, ax, label):
    global ser, latest_peak, persistent_lines
    try:
        if ser and ser.is_open and ser.in_waiting:
            arduinoData_bytes = ser.readline()
            try:
                arduinoData_string = arduinoData_bytes.decode('utf-8', errors='ignore').strip()
                label.config(text=f"Current Reading: {arduinoData_string}")
                print(arduinoData_string)
                # Handle normal tension values
                if arduinoData_string.replace('.', '', 1).isdigit():
                    arduinoData_float = float(arduinoData_string)
                    dataList.append(arduinoData_float)
                    curr = arduinoData_float

                # Handle removing peak lines
                elif arduinoData_string in ['px', 'pz']:
                    for i in range(5):
                        print("hello")
                    latest_peak = None
                    persistent_lines.clear()

                # Handle peak messages
                elif arduinoData_string.startswith('p'):                    
                    if len(arduinoData_string) > 2:
                        peak = arduinoData_string[2:]
                        latest_peak = float(peak)  # Update latest_peak
                        peak_cnt = arduinoData_string[1:]  # Extract peak count
                        ax.axhline(y=latest_peak, color='r', linestyle='--', label=f"Peak {peak_cnt}: {latest_peak}")
                        persistent_lines.append(latest_peak)  # Append the updated peak to persistent_lines
                

            except ValueError:
                pass

        # Keep data limited to the last 50 points
        dataList = dataList[-50:]
        
        # Update the plot
        ax.clear()
        ax.plot(dataList)
        ax.set_ylim([0, ylim])
        ax.set_title("Load Cell Data")
        ax.set_ylabel("Tension (oz)")

        # Redraw persistent peak lines
        for index, peak in enumerate(persistent_lines):
            ax.axhline(y=peak, color='r', linestyle='--', label=f"Peak {index+1}: {peak}")
        if persistent_lines:
            ax.legend()

        return dataList

    except serial.SerialException:
        ser = None
        dataList.clear()
        ax.clear()
        ax.set_ylim([0, ylim])
        ax.set_title("Load Cell Data")
        ax.set_ylabel("Tension (oz)")
        serial_status_label.config(text="COM7 Inactive", fg="red")
        return dataList




def updateValue(entry_widget, label):
    global ser
    value = entry_widget.get()
    if value.isdigit():
        command = f"T{value}" if label == "Threshold" else f"C{value}"
        if ser and ser.is_open:
            ser.write(command.encode('utf-8'))
            print(f"Sent {label}: {value}")
    else:
        print(f"Invalid input for {label}. Please enter a valid number.")

def clearPlotData(dataList, ax):
    dataList.clear()
    ax.clear()
    ax.set_ylim([0, 2000])
    ax.set_title("Load Cell Data")
    ax.set_ylabel("Tension (oz)")
    canvas.draw()

def check_serial_connection():
    global ser
    try:
        if ser is None or not ser.is_open:
            ser = serial.Serial("COM7", 9600, timeout=1)
            time.sleep(2)
            serial_status_label.config(text="COM7 Active", fg="green")
    except serial.SerialException:
        if ser and ser.is_open:
            ser.close()
        serial_status_label.config(text="COM7 Inactive", fg="red")
        ser = None
    root.after(1000, check_serial_connection)

def plt_increase():
    global ylim
    ylim += 10
    ax.set_ylim([0, ylim])
    canvas.draw()

def plt_decrease():
    global ylim
    ylim = max(0, ylim - 10)
    ax.set_ylim([0, ylim])
    canvas.draw()

# Create Tkinter window
root = Tk()
root.title('Thrash Detection Disconnector GUI')

# Frame for Controls
controls_frame = Frame(root)
controls_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=5)

# Threshold Controls
threshold_label = tk.Label(controls_frame, text="Threshold:")
threshold_label.grid(row=0, column=0, padx=5)
threshold_value = tk.Entry(controls_frame, width=12)
threshold_value.grid(row=0, column=1, padx=5)
threshold_Send = tk.Button(controls_frame, text="Set Threshold", command=lambda: updateValue(threshold_value, "Threshold"))
threshold_Send.grid(row=0, column=2, padx=5, sticky="ew")

# Calibration Controls
calibration_label = tk.Label(controls_frame, text="Calibration:")
calibration_label.grid(row=1, column=0, padx=5)
calibration_value = tk.Entry(controls_frame, width=12)
calibration_value.grid(row=1, column=1, padx=5)
calibration_Send = tk.Button(controls_frame, text="Set Calibration", command=lambda: updateValue(calibration_value, "Calibration"))
calibration_Send.grid(row=1, column=2, padx=5, sticky="ew")

# Plot Control Buttons
plot_controls_frame = Frame(root)
plot_controls_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=5)

clear_button = tk.Button(plot_controls_frame, text="Clear Plot", command=lambda: clearPlotData(dataList, ax))
clear_button.grid(row=0, column=0, padx=5, sticky="ew")

plt_decrease_button = tk.Button(plot_controls_frame, text="Zoom Out", command=plt_decrease)
plt_decrease_button.grid(row=0, column=1, padx=5, sticky="ew")

plt_increase_button = tk.Button(plot_controls_frame, text="Zoom In", command=plt_increase)
plt_increase_button.grid(row=0, column=2, padx=5, sticky="ew")

# Serial Status Label
serial_status_label = Label(root, text="Checking COM7...", font=("Helvetica", 12))
serial_status_label.grid(row=3, column=0, columnspan=2, sticky="ew", pady=5)

# Current Reading Label
label = tk.Label(root, text=f"Current Reading: {curr}", font=("Helvetica", 12, "bold"))
label.grid(row=4, column=0, columnspan=2, sticky="ew", pady=5)

# Matplotlib Figure
fig = plt.Figure(figsize=(5, 4), dpi=100)
ax = fig.add_subplot(111)

# Embed Plot in Tkinter
canvas = FigureCanvasTkAgg(fig, root)
canvas_widget = canvas.get_tk_widget()
canvas_widget.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)

# Configure Grid Layout
root.grid_rowconfigure(0, weight=1)  # Allow plot to expand
root.grid_columnconfigure(0, weight=1)  # Allow resizing

# Data list for animation
dataList = []

# Set up animation
ani = animation.FuncAnimation(fig, animate, fargs=(dataList, ax, label), interval=100, save_count=50)

# Start Serial Connection Check
check_serial_connection()

# Start Tkinter Main Loop
root.mainloop()

# Close Serial Port on Exit
if ser is not None and ser.is_open:
    ser.close()