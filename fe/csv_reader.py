"""
csv_reader.py
Utility for reading and merging sensor data from structured CSV files.
"""
import os
import csv
from datetime import datetime
import pytz
import glob
import pandas as pd
# import pathlib
import traceback
from collections import defaultdict

# Set this to the absolute path to your Database folder
DATASET_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Database'))
IST = pytz.timezone('Asia/Kolkata')

# Helper to get all CSV files for a data type (optionally in a date range)
def get_csv_files(data_type, start_date=None, end_date=None):
    pattern = os.path.join(DATASET_BASE_DIR, data_type, '*', f'{data_type}_*.csv')
    files = glob.glob(pattern)
    if start_date and end_date:
        files = [f for f in files if start_date <= extract_date_from_filename(f) <= end_date]
    return sorted(files)

def extract_date_from_filename(filename):
    # expects ..._YYYY-MM-DD.csv
    base = os.path.basename(filename)
    date_str = base.split('_')[-1].replace('.csv', '')
    return datetime.strptime(date_str, '%Y-%m-%d').date()

def read_csv_as_dicts(csv_file):
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            # Strip whitespace from headers
            reader.fieldnames = [field.strip() for field in reader.fieldnames]
            return list(reader)
    except Exception as e:
        print(f"[ERROR] Could not read {csv_file}: {e}")
        return []

def read_data_by_date(data_type, date):
    month_folder = date.strftime('%B_%Y')
    filename = f"{data_type}_{date.strftime('%Y-%m-%d')}.csv"
    path = os.path.join(DATASET_BASE_DIR, data_type, month_folder, filename)
    if os.path.exists(path):
        return read_csv_as_dicts(path)
    return []

def read_data_by_range(data_type, start_date, end_date):
    files = get_csv_files(data_type, start_date, end_date)
    data = []
    for f in files:
        data.extend(read_csv_as_dicts(f))
    return data

def get_most_recent(data_type):
    files = get_csv_files(data_type)
    if not files:
        return None
    last_file = sorted(files)[-1]
    rows = read_csv_as_dicts(last_file)
    return rows[-1] if rows else None

def merge_all_to_one(data_type, output_file):
    files = get_csv_files(data_type)
    with open(output_file, 'w', newline='', encoding='utf-8') as out:
        writer = None
        for f in files:
            with open(f, 'r', encoding='utf-8') as fin:
                reader = csv.DictReader(fin)
                if writer is None:
                    # Ensure MJD is included if present in any file
                    fieldnames = reader.fieldnames
                    if 'MJD' not in fieldnames:
                        # Find a file that has MJD if the first one doesn't
                        for other_f in files:
                            with open(other_f, 'r') as temp_f:
                                temp_reader = csv.reader(temp_f)
                                temp_header = next(temp_reader, [])
                                if 'MJD' in temp_header:
                                    fieldnames = temp_header
                                    break
                    writer = csv.DictWriter(out, fieldnames=fieldnames)
                    writer.writeheader()
                for row in reader:
                    writer.writerow(row)

# For charting: return pandas DataFrame
def get_dataframe(data_type, start_date=None, end_date=None):
    files = get_csv_files(data_type, start_date, end_date)
    dfs = [pd.read_csv(f) for f in files]
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    return pd.DataFrame()


# Functions specifically for dash_server.py
def get_latest_photodiode(folder_path):
    """
    Get the latest photodiode readings
    Returns a dictionary with P1, P2, P3, P4, P5, timestamp, MJD
    """
    try:
        # Try to find the most recent file
        pattern = os.path.join(folder_path, "*", "Photodiode_data_*.csv")
        files = sorted(glob.glob(pattern))
        if not files:
            return None
        latest_file = files[-1]
        with open(latest_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            # Only keep rows with valid timestamp and not just 'IST'
            rows = [row for row in reader if row.get('timestamp') and row['timestamp'].strip() and not row['timestamp'].strip().startswith('IST')]
            if not rows:
                return None
            latest_row = rows[-1]
            try:
                timestamp_str = latest_row.get('timestamp', '').replace(' IST', '').strip()
                timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                return {
                    'P1': float(latest_row.get('P1', 0)) if latest_row.get('P1') else None,
                    'P2': float(latest_row.get('P2', 0)) if latest_row.get('P2') else None,
                    'P3': float(latest_row.get('P3', 0)) if latest_row.get('P3') else None,
                    'P4': float(latest_row.get('P4', 0)) if latest_row.get('P4') else None,
                    'P5': float(latest_row.get('P5', 0)) if latest_row.get('P5') else None,
                    'MJD': float(latest_row.get('MJD', 0)) if latest_row.get('MJD') else None,
                    'timestamp': timestamp
                }
            except (ValueError, KeyError) as e:
                print(f"Error parsing photodiode row data: {e}")
                return None
    except Exception as e:
        print(f"Error in get_latest_photodiode: {e}")
        traceback.print_exc()
        return None

# --- RECTIFIED FUNCTION ---
def get_photodiode_plot_data(folder_path, max_points=50):
    """
    Get photodiode data for plotting. Now returns actual datetime objects for robust plotting.
    """
    empty_result = {
        'datetime': [], 'MJD': [],
        'P1': [], 'P2': [], 'P3': [], 'P4': [], 'P5': []
    }
    
    try:
        pattern = os.path.join(folder_path, "*", "Photodiode_data_*.csv")
        files = sorted(glob.glob(pattern))
        if not files:
            return empty_result

        dfs = []
        for file_path in reversed(files):
            try:
                df = pd.read_csv(file_path)
                required_columns = ['timestamp', 'MJD', 'P1', 'P2', 'P3', 'P4', 'P5']
                if not all(col in df.columns for col in required_columns):
                    continue
                
                df['timestamp'] = df['timestamp'].str.replace(' IST', '').str.strip()
                df['datetime'] = pd.to_datetime(df['timestamp'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
                df = df.dropna(subset=['datetime'])
                
                for col in ['MJD', 'P1', 'P2', 'P3', 'P4', 'P5']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                
                dfs.append(df)
                
                if sum(len(d) for d in dfs) >= max_points:
                    break
            except Exception as e:
                print(f"[ERROR] Error processing file {file_path}: {e}")
                continue
        
        if not dfs:
            return empty_result
            
        final_df = pd.concat(dfs, ignore_index=True)
        final_df = final_df.sort_values('datetime').tail(max_points)
        
        if final_df.empty:
            return empty_result
            
        result = empty_result.copy()
        result['datetime'] = final_df['datetime'].tolist() # Return datetime objects
        
        for col in ['MJD', 'P1', 'P2', 'P3', 'P4', 'P5']:
            result[col] = final_df[col].tolist()
        
        return result
        
    except Exception as e:
        print(f"Error in get_photodiode_plot_data: {e}")
        traceback.print_exc()
        return empty_result

def get_latest_temp_humidity(folder_path):
    """
    Get the latest temperature and humidity readings
    Returns a dictionary with temp1, humidity1, temp2, humidity2, timestamp, MJD
    """
    try:
        pattern = os.path.join(folder_path, "*", "Temp_Humidity_data_*.csv")
        files = sorted(glob.glob(pattern))
        if not files:
            return None
        latest_file = files[-1]
        with open(latest_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            rows = [row for row in reader if row.get('timestamp') and row['timestamp'].strip()]
            if not rows:
                return None
            latest_row = rows[-1]
            try:
                timestamp_str = latest_row.get('timestamp', '').strip()
                if timestamp_str.endswith(' IST'):
                    timestamp_str = timestamp_str[:-4]
                timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                return {
                    'temp1': float(latest_row.get('T1', 0)) if latest_row.get('T1') else None,
                    'humidity1': float(latest_row.get('H1', 0)) if latest_row.get('H1') else None,
                    'temp2': float(latest_row.get('T2', 0)) if latest_row.get('T2') else None,
                    'humidity2': float(latest_row.get('H2', 0)) if latest_row.get('H2') else None,
                    'MJD': float(latest_row.get('MJD', 0)) if latest_row.get('MJD') else None,
                    'timestamp': timestamp
                }
            except (ValueError, KeyError) as e:
                print(f"Error parsing temp/humidity row data: {e}")
                return None
    except Exception as e:
        print(f"Error in get_latest_temp_humidity: {e}")
        traceback.print_exc()
        return None


def get_temp_humidity_plot_data(folder_path, max_points=50):
    """
    Get temperature and humidity data for plotting
    Returns a dictionary with arrays of time_points, time_fmt, MJD, temp1, humidity1, temp2, humidity2
    """
    try:
        pattern = os.path.join(folder_path, "*", "Temp_Humidity_data_*.csv")
        files = sorted(glob.glob(pattern))
        if not files:
            return {'time_points': [], 'time_fmt': [], 'MJD': [], 'temp1': [], 'humidity1': [], 'temp2': [], 'humidity2': []}
        
        combined_data = []
        for file_path in reversed(files):
            with open(file_path, 'r', newline='') as f:
                reader = csv.DictReader(f)
                combined_data.extend(list(reader))
                if len(combined_data) >= max_points:
                    break
        
        recent_data = combined_data[-max_points:]
        result = {
            'time_points': list(range(len(recent_data))),
            'time_fmt': [], 'MJD': [],
            'temp1': [], 'humidity1': [], 'temp2': [], 'humidity2': []
        }
        
        for row in recent_data:
            try:
                timestamp_str = row.get('timestamp', '').strip()
                if timestamp_str.endswith(' IST'):
                    timestamp_str = timestamp_str[:-4]
                dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                result['time_fmt'].append(dt.strftime('%H:%M:%S'))
                result['MJD'].append(float(row.get('MJD')) if row.get('MJD') else None)
                result['temp1'].append(float(row.get('T1')) if row.get('T1') else None)
                result['humidity1'].append(float(row.get('H1')) if row.get('H1') else None)
                result['temp2'].append(float(row.get('T2')) if row.get('T2') else None)
                result['humidity2'].append(float(row.get('H2')) if row.get('H2') else None)
            except (ValueError, KeyError) as e:
                print(f"Error parsing temp/humidity row for plotting: {e}")
                continue
        return result
    except Exception as e:
        print(f"Error in get_temp_humidity_plot_data: {e}")
        traceback.print_exc()
        return {'time_points': [], 'time_fmt': [], 'MJD': [], 'temp1': [], 'humidity1': [], 'temp2': [], 'humidity2': []}

def get_latest_laser(folder_path):
    """
    Get the latest laser readings
    Returns a dictionary with X1..D2, timestamp, MJD
    """
    try:
        pattern = os.path.join(folder_path, "*", "Lasers_data_*.csv")
        files = sorted(glob.glob(pattern))
        if not files:
            return None
        latest_file = files[-1]
        with open(latest_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            if not rows:
                return None
            latest_row = rows[-1]
            try:
                timestamp_str = latest_row.get('timestamp', '').replace(' IST', '').strip()
                timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                return {
                    'X1': float(latest_row.get('X1', 0)) if latest_row.get('X1') else None,
                    'X2': float(latest_row.get('X2', 0)) if latest_row.get('X2') else None,
                    'Y1': float(latest_row.get('Y1', 0)) if latest_row.get('Y1') else None,
                    'Y2': float(latest_row.get('Y2', 0)) if latest_row.get('Y2') else None,
                    'Z1': float(latest_row.get('Z1', 0)) if latest_row.get('Z1') else None,
                    'Z2': float(latest_row.get('Z2', 0)) if latest_row.get('Z2') else None,
                    'D1': float(latest_row.get('D1', 0)) if latest_row.get('D1') else None,
                    'D2': float(latest_row.get('D2', 0)) if latest_row.get('D2') else None,
                    'MJD': float(latest_row.get('MJD', 0)) if latest_row.get('MJD') else None,
                    'timestamp': timestamp
                }
            except (ValueError, KeyError) as e:
                print(f"Error parsing laser row data: {e}")
                return None
    except Exception as e:
        print(f"Error in get_latest_laser: {e}")
        traceback.print_exc()
        return None

def get_laser_plot_data(folder_path, max_points=50):
    """
    Get laser data for plotting
    Returns a dictionary with arrays of time_points, time_fmt, MJD, X1..D2
    """
    try:
        pattern = os.path.join(folder_path, "*", "Lasers_data_*.csv")
        files = sorted(glob.glob(pattern))
        empty_result = {
            'time_points': [], 'time_fmt': [], 'MJD': [],
            'X1': [], 'X2': [], 'Y1': [], 'Y2': [],
            'Z1': [], 'Z2': [], 'D1': [], 'D2': []
        }
        if not files:
            return empty_result
        
        combined_data = []
        for file_path in reversed(files):
            with open(file_path, 'r', newline='') as f:
                reader = csv.DictReader(f)
                combined_data.extend(list(reader))
                if len(combined_data) >= max_points:
                    break
                    
        recent_data = combined_data[-max_points:]
        result = {
            'time_points': list(range(len(recent_data))),
            'time_fmt': [], 'MJD': [],
            'X1': [], 'X2': [], 'Y1': [], 'Y2': [],
            'Z1': [], 'Z2': [], 'D1': [], 'D2': []
        }
        for row in recent_data:
            try:
                timestamp_str = row.get('timestamp', '').replace(' IST', '').strip()
                dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                result['time_fmt'].append(dt.strftime('%H:%M:%S'))
                result['MJD'].append(float(row.get('MJD')) if row.get('MJD') else None)
                result['X1'].append(float(row.get('X1')) if row.get('X1') else None)
                result['X2'].append(float(row.get('X2')) if row.get('X2') else None)
                result['Y1'].append(float(row.get('Y1')) if row.get('Y1') else None)
                result['Y2'].append(float(row.get('Y2')) if row.get('Y2') else None)
                result['Z1'].append(float(row.get('Z1')) if row.get('Z1') else None)
                result['Z2'].append(float(row.get('Z2')) if row.get('Z2') else None)
                result['D1'].append(float(row.get('D1')) if row.get('D1') else None)
                result['D2'].append(float(row.get('D2')) if row.get('D2') else None)
            except (ValueError, KeyError) as e:
                print(f"Error parsing laser row for plotting: {e}")
                continue
        return result
    except Exception as e:
        print(f"Error in get_laser_plot_data: {e}")
        traceback.print_exc()
        return {
            'time_points': [], 'time_fmt': [], 'MJD': [],
            'X1': [], 'X2': [], 'Y1': [], 'Y2': [],
            'Z1': [], 'Z2': [], 'D1': [], 'D2': []
        }