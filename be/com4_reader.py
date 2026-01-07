import serial
import os
# import sys
import time
from datetime import datetime, timedelta, timezone

# Default serial port - change this to match your system's port
# Windows: 'COM4', 'COM6', etc.
# Linux/macOS: '/dev/ttyUSB0', '/dev/tty.usbserial-XXX', etc.
SERIAL_PORT = 'COM6'

# Default baudrate for FLUKE 1620A
BAUDRATE = 9600

# Maximum retries for serial connection
MAX_RETRIES = 3


def get_ist_time():
    ist = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(ist)

def normalize_line(line):
    line = line.strip()
    parts = line.split(',')

    if len(parts) == 4:
        try:
            [float(p.strip()) for p in parts]
            return line
        except ValueError:
            pass

    if len(parts) >= 8:
        values = [p.strip().replace('%', '').replace('C', '') for p in parts]
        extracted = [values[1], values[3], values[5], values[7]]
        return ','.join(extracted)

    return ""



def get_com4_reader(port=SERIAL_PORT, baudrate=BAUDRATE, timeout=1):
    """Return a function that fetches one reading from the given COM port and returns a dict or None."""
    ser = None
    for attempt in range(MAX_RETRIES):
        try:
            print(f"Attempting to connect to {port} (attempt {attempt+1}/{MAX_RETRIES})...")
            ser = serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                xonxoff=True,
                timeout=timeout
            )
            print(f"Successfully connected to {port}!")
            break
        except serial.SerialException as e:
            print(f"Error connecting to {port}: {e}")
            if attempt < MAX_RETRIES - 1:
                print(f"Retrying in 2 seconds...")
                time.sleep(2)
            else:
                print(f"Failed to connect to {port} after {MAX_RETRIES} attempts.")
                print("Please check if the device is connected and the port is correct.")
                print(f"You might need to modify the SERIAL_PORT value in {os.path.basename(__file__)}")
                
                # Return a dummy function that returns None
                def dummy_fetch():
                    print(f"WARNING: No serial connection to {port}. Returning dummy data.")
                    return None
                return dummy_fetch
    
    def fetch_one():
        if ser is None:
            return None
            
        try:
            ser.write(b'READ?\r\n')
            raw_line = ser.readline().decode('utf-8', errors='replace').strip()
            normalized_line = normalize_line(raw_line)
            if normalized_line:
                data_list = normalized_line.split(',')
                if len(data_list) == 4:
                    # Convert values to floats if possible
                    try:
                        return {
                            'T1': float(data_list[0]),
                            'H1': float(data_list[1]),
                            'T2': float(data_list[2]),
                            'H2': float(data_list[3]),
                            'TIMESTAMPS': get_ist_time().strftime('%Y-%m-%d %H:%M:%S')
                        }
                    except ValueError:
                        print(f"Warning: Could not convert values to float: {data_list}")
            return None
        except Exception as e:
            print(f"Error reading from serial port: {e}")
            return None
    return fetch_one

# Example usage:
# reader = get_com4_reader(port='COM4', baudrate=9600)
# data = reader()
# print(data)
