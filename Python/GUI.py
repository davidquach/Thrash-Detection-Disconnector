import time
import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import Tk, Label

ylim = 2000

# Declare global serial variable
ser = None

# Load Cell Real-Time Plot
def animate(i, dataList, ax):
    global ser  # Ensure ser is accessible
    try:
        if ser and ser.is_open and ser.in_waiting:
            arduinoData_bytes = ser.readline()
            try:
                arduinoData_string = arduinoData_bytes.decode('utf-8', errors='ignore').strip()
                arduinoData_float = float(arduinoData_string)
                dataList.append(arduinoData_float)
            except ValueError:
                pass
            dataList = dataList[-50:]  # Limit data to last 50 points
            ax.clear()  # Clear the previous plot
            ax.plot(dataList)  # Plot the new data
            ax.set_ylim([0, ylim])
            ax.set_title("Load Cell Data")
            ax.set_ylabel("Tension (oz)")
        return dataList
    except serial.SerialException:
        ser = None  # Reset serial connection
        dataList.clear()  # Clear the dataList
        ax.clear()  # Clear the plot
        ax.set_ylim([0, ylim])
        ax.set_title("Load Cell Data")
        ax.set_ylabel("Tension (oz)")
        serial_status_label.config(text="COM7 Inactive", fg="red")
        return dataList

def updateValue(entry_widget, label):
    global ser  # Ensure ser is accessible
    value = entry_widget.get()  
    if value.isdigit():  
        if label == "Threshold":
            command = f"T{value}"  
        elif label == "Calibration":
            command = f"C{value}"  
        if ser and ser.is_open:  
            ser.write(command.encode('utf-8')) 
            print(f"Sent {label}: {value}") 
    else:
        print(f"Invalid input for {label}. Please enter a valid number.")  # Debugging message for invalid input

def clearPlotData(dataList, ax):
    dataList.clear()  
    ax.clear()  
    ax.set_ylim([0, 2000])
    ax.set_title("Load Cell Data")
    ax.set_ylabel("Tension (oz)")
    canvas.draw()  

def check_serial_connection():
    global ser  # Ensure ser is accessible
    try:
        # Attempt to initialize the serial port if not already connected
        if ser is None or not ser.is_open:
            ser = serial.Serial("COM7", 9600, timeout=1)
            time.sleep(2)  # Allow Arduino to initialize
            serial_status_label.config(text="COM7 Active", fg="green")
    except serial.SerialException:
        if ser and ser.is_open:
            ser.close()  # Close the serial port if it was open
        serial_status_label.config(text="COM7 Inactive", fg="red")
        ser = None  # Reset ser if the connection failed
    root.after(1000, check_serial_connection)

# Create Tkinter window
root = Tk()
root.title('Thrash Detection Disconnector GUI')

# Add entry box and button for threshold
threshold_value = tk.Entry(root, width=10)  # Entry widget to input threshold
threshold_value.grid(row=0, column=0, sticky="ew")  # Stretch entry horizontally

threshold_Send = tk.Button(root, text="Update Threshold", 
                            command=lambda: updateValue(threshold_value, "Threshold"))  # On click, call updateValue with "Threshold"
threshold_Send.grid(row=0, column=1, sticky="ew")  # Stretch button horizontally

calibration_value = tk.Entry(root, width=10)  # Entry widget to input calibration value
calibration_value.grid(row=1, column=0, sticky="ew")  # Stretch entry horizontally

calibration_Send = tk.Button(root, text="Update Calibration", 
                              command=lambda: updateValue(calibration_value, "Calibration"))  # On click, call updateValue with "Calibration"
calibration_Send.grid(row=1, column=1, sticky="ew")  # Stretch button horizontally

# Add a Clear Data button
clear_button = tk.Button(root, text="Clear Plot Data", 
                         command=lambda: clearPlotData(dataList, ax))  # On click, call clearPlotData function
clear_button.grid(row=2, column=1, sticky="ew")  # Stretch button horizontally


def plt_increase():
    global ylim
    ylim += 250
    ax.set_ylim([0, ylim])  # Update the y-axis range
    canvas.draw()  # Redraw the canvas to reflect changes

def plt_decrease():
    global ylim
    ylim -= 250
    if ylim < 0:
        ylim = 0
    ax.set_ylim([0, ylim])  # Update the y-axis range
    canvas.draw()  # Redraw the canvas to reflect changes


plt_decrease_button = tk.Button(root, text="Decrease Plot Range", 
                         command=lambda: plt_decrease())  # On click, call clearPlotData function
plt_decrease_button.grid(row=4, column=0, sticky="ew")  # Stretch button horizontally

plt_increase_button = tk.Button(root, text="Increase Plot Range", 
                         command=lambda: plt_increase())  # On click, call clearPlotData function
plt_increase_button.grid(row=4, column=1, sticky="ew")  # Stretch button horizontally


# Create serial connection status label
serial_status_label = Label(root, text="Checking COM7...", font=("Helvetica", 12))
serial_status_label.grid(row=3, column=0, columnspan=2, sticky="ew")  # Center label

# Create matplotlib figure
fig = plt.Figure(figsize=(5, 4), dpi=100)
ax = fig.add_subplot(111)

# Embed the matplotlib figure in the Tkinter window
canvas = FigureCanvasTkAgg(fig, root)
canvas_widget = canvas.get_tk_widget()
canvas_widget.grid(row=5, column=0, columnspan=2, sticky="nsew")  # Allow canvas to stretch

# Configure grid layout for resizing
root.grid_rowconfigure(5, weight=1)  # Make row 4 (plot area) expandable
root.grid_columnconfigure(0, weight=1)  # Make column 0 expandable
root.grid_columnconfigure(1, weight=1)  # Make column 1 expandable

# Data list for animation
dataList = []

# Set up animation
ani = animation.FuncAnimation(fig, animate, fargs=(dataList, ax), interval=100, save_count=50)

# Start the check for the serial connection
check_serial_connection()

# Start Tkinter main loop
root.mainloop()

# Close serial port when GUI is closed
if ser is not None and ser.is_open:
    ser.close()
