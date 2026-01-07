"""
data_pipeline.py
Fetches temperature/humidity data from a serial port and saves to CSV every 2 minutes.
Saves all data in the correct Database/Temp_Humidity_data structure, with daily CSVs.
Runs indefinitely and manages the sensor_api_server as a subprocess.
"""

import time
import os
import csv
import subprocess
import sys
import logging
from datetime import datetime
import pytz
from com4_reader import get_com4_reader

# --- CONFIGURATION ---
# Use absolute path to ensure files are saved in the right location
CSV_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Database'))
POLL_INTERVAL = 120  # seconds
COM_PORT = 'COM6'    # Set your COM port here
COM_BAUDRATE = 9600
IST = pytz.timezone('Asia/Kolkata')
UTC = pytz.utc

# --- LOGGING SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# --- HELPER FUNCTIONS ---

def datetime_to_mjd(dt_obj_utc):
    """
    Converts a UTC datetime object to Modified Julian Date.
    The input datetime object MUST be in UTC for an accurate calculation.
    """
    # Formula for Julian Date
    jd = (
        367 * dt_obj_utc.year
        - int(7 * (dt_obj_utc.year + int((dt_obj_utc.month + 9) / 12)) / 4)
        + int(275 * dt_obj_utc.month / 9)
        + dt_obj_utc.day
        + 1721013.5
    )
    # Add the fractional day
    jd += (dt_obj_utc.hour + dt_obj_utc.minute / 60.0 + dt_obj_utc.second / 3600.0) / 24.0
    # Convert Julian Date to Modified Julian Date
    mjd = jd - 2400000.5
    return mjd

def process_timestamp(timestamp_str=None):
    """
    Takes a naive timestamp string, processes it, and returns a dictionary
    containing IST, UTC, and MJD values.
    """
    now_naive = datetime.now()
    
    # 1. Determine the source datetime object (from string or current time)
    try:
        if timestamp_str:
            dt_naive = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        else:
            dt_naive = now_naive
            logger.info("No timestamp provided by device, using current server time.")
    except (ValueError, TypeError):
        dt_naive = now_naive
        logger.warning(f"Could not parse timestamp string '{timestamp_str}'. Falling back to server time.")
        
    # 2. Localize to IST and convert to UTC
    dt_ist = IST.localize(dt_naive)
    dt_utc = dt_ist.astimezone(UTC)
    
    # 3. Calculate MJD from the UTC datetime object
    mjd = datetime_to_mjd(dt_utc)
    
    return {
        "ist_str": dt_ist.strftime('%Y-%m-%d %H:%M:%S IST'),
        "utc_str": dt_utc.strftime('%Y-%m-%d %H:%M:%S UTC'),
        "mjd": mjd
    }

def get_csv_path():
    """Constructs the full, absolute path for today's CSV file."""
    month_year = datetime.now(IST).strftime('%B_%Y')
    today = datetime.now(IST).strftime('%Y-%m-%d')
    
    dir_path = os.path.join(CSV_BASE_DIR, 'Temp_Humidity_data', month_year)
    
    # Ensure the directory exists
    os.makedirs(dir_path, exist_ok=True)
    
    filename = f'Temp_Humidity_data_{today}.csv'
    return os.path.join(dir_path, filename)

def write_to_csv(filepath, data_row):
    """Writes a single data row to the specified CSV file."""
    headers = ['timestamp', 'UTC_timestamp', 'MJD', 'T1', 'H1', 'T2', 'H2']
    file_exists = os.path.exists(filepath)
    
    try:
        with open(filepath, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            if not file_exists:
                writer.writeheader()
                logger.info(f"Created new CSV file: {filepath}")
            writer.writerow(data_row)
        return True
    except IOError as e:
        logger.error(f"Could not write to CSV file {filepath}: {e}")
        return False

def start_api_server():
    """Starts the Flask API server as a background subprocess."""
    server_script_path = os.path.join(os.path.dirname(__file__), 'sensor_api_server.py')
    if not os.path.exists(server_script_path):
        logger.error(f"API server script not found at {server_script_path}. Aborting.")
        return None
        
    try:
        # sys.executable ensures we use the same Python interpreter
        server_process = subprocess.Popen([sys.executable, server_script_path])
        logger.info(f"Started ESP Flask API server as subprocess (PID: {server_process.pid}).")
        return server_process
    except Exception as e:
        logger.error(f"Failed to start the API server subprocess: {e}")
        return None

# --- MAIN EXECUTION ---
def main():
    """Main polling loop."""
    api_process = start_api_server()
    if not api_process:
        return # Exit if the server couldn't be started

    reader = get_com4_reader(port=COM_PORT, baudrate=COM_BAUDRATE)
    logger.info(f"Started polling for temperature/humidity data on {COM_PORT} every {POLL_INTERVAL} seconds.")

    try:
        while True:
            com4_data = reader()
            if com4_data:
                # The core logic is now cleaner.
                # All time conversions and MJD calculation happen inside process_timestamp.
                time_data = process_timestamp(com4_data.get('TIMESTAMPS'))
                
                # Prepare the row for the CSV file
                data_row = {
                    'timestamp': time_data['ist_str'],
                    'UTC_timestamp': time_data['utc_str'],
                    'MJD': time_data['mjd'],
                    'T1': com4_data.get('T1', ''),
                    'H1': com4_data.get('H1', ''),
                    'T2': com4_data.get('T2', ''),
                    'H2': com4_data.get('H2', ''),
                }
                
                csv_filepath = get_csv_path()
                if write_to_csv(csv_filepath, data_row):
                    logger.info(f"Successfully saved COM4 data to {os.path.basename(csv_filepath)}.")
                else:
                    logger.error("Failed to save COM4 data to CSV.")
            else:
                logger.warning("No valid data received from COM4.")
            
            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        logger.info("Shutdown signal received. Terminating processes.")
    finally:
        if api_process:
            api_process.terminate()
            logger.info("ESP Flask server subprocess terminated.")

if __name__ == "__main__":
    main()