import ctypes
from ctypes import wintypes
import win32gui
import keyboard
import time

# Constants for Windows API
WM_INPUT = 0x00FF
RIDEV_INPUTSINK = 0x00000100

# Structures for RAW INPUT
class RAWINPUTDEVICE(ctypes.Structure):
    _fields_ = [
        ("usUsagePage", wintypes.USHORT),
        ("usUsage", wintypes.USHORT),
        ("dwFlags", wintypes.DWORD),
        ("hwndTarget", wintypes.HWND),
    ]

class RAWINPUTHEADER(ctypes.Structure):
    _fields_ = [
        ("dwType", wintypes.DWORD),
        ("dwSize", wintypes.DWORD),
        ("hDevice", wintypes.HANDLE),
        ("wParam", wintypes.WPARAM),
    ]

# Global variables
known_devices = []  # List of device handles for known mice
normal_mouse = None  # Handle for the "normal" mouse
sensor_mouse = None  # Handle for the "sensor" mouse
last_trigger = 0  # Timestamp of the last trigger
cooldown = 2  # Cooldown period in seconds

# Function to get the device handle from raw input data
def get_device_handle(lparam):
    header_size = ctypes.sizeof(RAWINPUTHEADER)
    header_buffer = ctypes.create_string_buffer(header_size)
    dwSize = wintypes.UINT(header_size)

    # Get the header of the raw input data
    ctypes.windll.user32.GetRawInputData(
        lparam,
        0x10000005,  # RID_HEADER
        ctypes.byref(header_buffer),
        ctypes.byref(dwSize),
        ctypes.sizeof(RAWINPUTHEADER),
    )

    # Extract the device handle from the header
    header = RAWINPUTHEADER.from_buffer(header_buffer)
    return header.hDevice

# Window procedure to handle raw input messages
def wnd_proc(hwnd, msg, wparam, lparam):
    global known_devices, normal_mouse, sensor_mouse, last_trigger

    if msg == WM_INPUT:
        device = get_device_handle(lparam)

        # Add the device to the list of known devices if it's not already there
        if device not in known_devices:
            known_devices.append(device)
            print(f"New mouse detected: {device}")

            # The first mouse is treated as normal; subsequent mice act as sensors
            if len(known_devices) == 1:
                normal_mouse = device
                print(f"Normal mouse assigned: {device}")
            else:
                sensor_mouse = device
                print(f"Sensor mouse assigned: {device}")

        # Trigger ALT+TAB only for the sensor mouse
        if device == sensor_mouse:
            now = time.time()
            if now - last_trigger > cooldown:
                print("Sensor mouse movement detected -> ALT+TAB")
                keyboard.press_and_release("alt+tab")
                last_trigger = now

    return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

# Main function to set up raw input monitoring
def main():
    user32 = ctypes.windll.user32

    # Register a hidden window to receive raw input messages
    wc = win32gui.WNDCLASS()
    wc.lpfnWndProc = wnd_proc
    wc.lpszClassName = "RawInputSensor"
    class_atom = win32gui.RegisterClass(wc)

    hwnd = win32gui.CreateWindow(
        class_atom,
        "hidden",
        0,
        0, 0, 0, 0,
        0, 0, 0, None
    )

    # Register raw input devices (mice)
    rid = RAWINPUTDEVICE()
    rid.usUsagePage = 0x01  # Generic desktop controls
    rid.usUsage = 0x02      # Mouse
    rid.dwFlags = RIDEV_INPUTSINK
    rid.hwndTarget = hwnd

    success = user32.RegisterRawInputDevices(
        ctypes.byref(rid), 1, ctypes.sizeof(rid)
    )
    if not success:
        print("Failed to register raw input devices.")
        return

    print("Script started. Connect a new mouse  it will become the motion sensor.")
    win32gui.PumpMessages()

if __name__ == "__main__":
    main()