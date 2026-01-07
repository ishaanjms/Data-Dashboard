#!/usr/bin/env python3
"""
Python Flask API Server
Receives sensor data from an ESP8266 and stores it in categorized CSV files.
Refactored for clarity, robustness, and reduced code duplication.
"""

import os
import csv
import logging
from datetime import datetime
from flask import Flask, request, jsonify
import pytz

# --- CONFIGURATION ---
IST = pytz.timezone('Asia/Kolkata')
UTC = pytz.utc
# Use absolute path to ensure files are saved in the right location
CSV_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Database'))

# --- LOGGING SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# --- FLASK APP INITIALIZATION ---
app = Flask(__name__)

# --- HELPER FUNCTIONS ---

def datetime_to_mjd(dt_obj_utc):
    """
    Converts a UTC datetime object to Modified Julian Date.
    The input datetime object MUST be in UTC for an accurate calculation.
    """
    jd = (
        367 * dt_obj_utc.year
        - int(7 * (dt_obj_utc.year + int((dt_obj_utc.month + 9) / 12)) / 4)
        + int(275 * dt_obj_utc.month / 9)
        + dt_obj_utc.day
        + 1721013.5
    )
    jd += (dt_obj_utc.hour + dt_obj_utc.minute / 60.0 + dt_obj_utc.second / 3600.0) / 24.0
    return jd - 2400000.5

def get_time_data(form_data):
    """
    Determines the timestamp from request data or server time, converts it to
    IST and UTC, and calculates the MJD. Returns a dictionary with time info.
    """
    # Use Arduino timestamp if provided and valid, otherwise use server time
    try:
        arduino_epoch = int(form_data['timestamp'])
        timestamp_ist = datetime.fromtimestamp(arduino_epoch, tz=IST)
        logger.info(f"Using valid Arduino timestamp: {timestamp_ist.strftime('%Y-%m-%d %H:%M:%S IST')}")
    except (KeyError, ValueError, OSError):
        timestamp_ist = datetime.now(IST)
        logger.warning("Using server time (Arduino timestamp missing, invalid, or out of range).")
        
    timestamp_utc = timestamp_ist.astimezone(UTC)
    mjd = datetime_to_mjd(timestamp_utc)
    
    return {
        "ist_str": timestamp_ist.strftime('%Y-%m-%d %H:%M:%S IST'),
        "utc_str": timestamp_utc.strftime('%Y-%m-%d %H:%M:%S UTC'),
        "mjd": mjd
    }

def write_to_csv(data_type, headers, data_row):
    """
    A generic function to write a data row to the appropriate CSV file.
    Handles directory/file creation and header writing automatically.
    """
    try:
        now = datetime.now(IST)
        month_year = now.strftime('%B_%Y')
        today = now.strftime('%Y-%m-%d')
        
        dir_path = os.path.join(CSV_BASE_DIR, f'{data_type}_data', month_year)
        os.makedirs(dir_path, exist_ok=True)
        
        filename = f'{data_type}_data_{today}.csv'
        filepath = os.path.join(dir_path, filename)
        
        file_exists = os.path.exists(filepath)
        
        with open(filepath, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(headers)
            writer.writerow(data_row)
            
        logger.info(f"{data_type} data written to {os.path.basename(filepath)}")
        return True
    except Exception as e:
        logger.error(f"Failed to write {data_type} CSV: {e}")
        return False

# --- FLASK API ENDPOINTS ---

@app.route('/api/sensor-data', methods=['POST'])
def save_sensor_data():
    """Main API endpoint to receive and store sensor data."""
    required_fields = {
        'photodiode': ['P1', 'P2', 'P3', 'P4', 'P5'],
        'lasers': ['X1', 'X2', 'Y1', 'Y2', 'Z1', 'Z2', 'D1', 'D2']
    }
    all_fields = required_fields['photodiode'] + required_fields['lasers']
    
    # 1. Validate request data
    if not request.form:
        return "Request body cannot be empty.", 400
        
    missing_fields = [field for field in all_fields if field not in request.form]
    if missing_fields:
        msg = f"Missing data fields: {', '.join(missing_fields)}"
        logger.warning(msg)
        return msg, 400

    try:
        sensor_data = {field: float(request.form[field]) for field in all_fields}
    except ValueError as e:
        msg = f"Invalid numeric value in form data: {e}"
        logger.error(msg)
        return msg, 400
    
    # 2. Get all time-related data in one call
    time_data = get_time_data(request.form)
    
    # 3. Prepare and write Photodiode data
    photodiode_headers = ['timestamp', 'UTC_timestamp', 'MJD'] + required_fields['photodiode']
    photodiode_row = [time_data['ist_str'], time_data['utc_str'], time_data['mjd']] + \
                      [sensor_data[field] for field in required_fields['photodiode']]
    photodiode_ok = write_to_csv('Photodiode', photodiode_headers, photodiode_row)
    
    # 4. Prepare and write Lasers data
    lasers_headers = ['timestamp', 'UTC_timestamp', 'MJD'] + required_fields['lasers']
    lasers_row = [time_data['ist_str'], time_data['utc_str'], time_data['mjd']] + \
                 [sensor_data[field] for field in required_fields['lasers']]
    lasers_ok = write_to_csv('Lasers', lasers_headers, lasers_row)
    
    # 5. Send response
    if photodiode_ok and lasers_ok:
        return f"Data saved successfully at {time_data['ist_str']}", 200
    else:
        return "Failed to write data to one or both CSV files.", 500

@app.route('/phpfiles/save_val.php', methods=['POST'])
def save_sensor_data_legacy():
    """Legacy endpoint for backward compatibility."""
    logger.info("Redirecting request from legacy PHP endpoint.")
    return save_sensor_data()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint to confirm the server is running."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S IST'),
        'csv_base_directory': CSV_BASE_DIR
    })

@app.route('/', methods=['GET'])
def index():
    """Root endpoint with API information."""
    return jsonify({
        'service': 'Sensor Data API Server',
        'version': '3.0 (Refactored)',
        'timezone': str(IST),
        'endpoints': {
            'POST /api/sensor-data': 'Main endpoint for ESP8266 data.',
            'POST /phpfiles/save_val.php': 'Legacy compatibility endpoint.',
            'GET /health': 'Service health check.',
            'GET /': 'This information.'
        }
    })

# --- MAIN EXECUTION ---
if __name__ == '__main__':
    os.makedirs(CSV_BASE_DIR, exist_ok=True)
    logger.info("🚀 Starting Sensor Data API Server...")
    logger.info(f"🕒 Timezone: {str(IST)}")
    logger.info(f"🕒 Current IST Time: {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"📁 CSV Base Directory: {CSV_BASE_DIR}")
    logger.info("🔌 Listening on http://0.0.0.0:5176")
    
    # Note: For production, a proper WSGI server like Gunicorn or Waitress should be used.
    app.run(host='0.0.0.0', port=5176, debug=False)