#Thrash Detection Disconnector

Overview

This repository contains all code and documentation for Capstone 350 & 450. The project includes a Python-based graphical user interface (GUI) and Arduino code for a Heltec microcontroller.

Repository Structure

/project-root
│── python/         # Contains the Python Tkinter-based GUI and executable
│── arduino/        # Contains the Arduino code for the Heltec microcontroller
│── README.md       # Project documentation

Python (Tkinter GUI)

The python directory contains:

A Tkinter-based GUI implemented in Python.

An executable file for running the application without requiring Python installation.

Arduino (Heltec MCU Arduino Code)

The arduino directory includes:

Code for the Heltec microcontroller, responsible for interfacing with hardware components.

Requirements

Python

Python 3.10-3.11

Required libraries (install via pip install -r requirements.txt if applicable)

Arduino

Arduino IDE

Heltec ESP board libraries

Installation & Usage

Clone the repository:

git clone https://github.com/your-repo/project-name.git
cd project-name

For Python:

Run the GUI:

python main.py

For Arduino:

Open the Arduino sketch in the Arduino IDE.

Compile and upload the code to the Heltec microcontroller.
