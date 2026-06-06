# CsF1 Sensor Data Dashboard

This project collects laboratory sensor data, stores it as daily CSV files, and displays current plus historical readings in a Dash web dashboard.

The system is organized around three data streams:

- Temperature and humidity from a serial COM device, currently configured as `COM6`.
- Laser position channels from an ESP8266 and ADS1115 ADC boards.
- Photodiode voltage channels from the same ESP8266 and ADS1115 ADC boards.

All stored data includes local IST time, UTC time, and Modified Julian Date (MJD), which makes the CSV files useful for both live monitoring and later scientific analysis.

## Project Layout

```text
Data-Dashboard/
├── app.py
├── aurduino.cpp
├── Dockerfile
├── be/
│   ├── com4_reader.py
│   ├── data_pipeline.py
│   └── sensor_api_server.py
├── fe/
│   ├── csv_reader.py
│   ├── dash_app.py
│   ├── design.py
│   └── assets/
├── Database/
│   ├── Lasers_data/
│   ├── Photodiode_data/
│   └── Temp_Humidity_data/
├── README.md
└── requirements.txt
```

## Main Components

### ESP8266 / Arduino Sketch

File: `aurduino.cpp`

The sketch connects an ESP8266 to WiFi, reads four ADS1115 ADC boards, and posts sensor values to the Flask backend.

Configured values:

- WiFi SSID and password are hardcoded in the sketch.
- Backend host: `172.16.26.53`
- Backend port: `5176`
- Endpoint: `/api/sensor-data`
- ADC boards: `0x48`, `0x49`, `0x4A`, `0x4B`

Channel mapping:

```text
volt[0]  -> X1
volt[1]  -> X2
volt[2]  -> Y1
volt[3]  -> Y2
volt[4]  -> Z1
volt[5]  -> Z2
volt[6]  -> D1
volt[7]  -> D2
volt[8]  -> P1
volt[9]  -> P2
volt[10] -> P3
volt[11] -> P4
volt[12] -> P5
volt[13] -> EX1
volt[14] -> EX2
volt[15] -> EX3
```

The backend currently stores `X1` through `D2` and `P1` through `P5`. The `EX1`, `EX2`, and `EX3` values are sent by the sketch but not stored by the Flask endpoint.

### Backend API Server

File: `be/sensor_api_server.py`

This Flask app receives ESP8266 POST requests and writes laser plus photodiode data into daily CSV files.

Important endpoints:

- `POST /api/sensor-data` receives sensor data from the ESP8266.
- `POST /phpfiles/save_val.php` is a legacy alias for compatibility.
- `GET /health` reports API health and the active CSV directory.
- `GET /` returns basic service metadata.

The API writes files into:

```text
Database/Photodiode_data/<Month_Year>/Photodiode_data_<YYYY-MM-DD>.csv
Database/Lasers_data/<Month_Year>/Lasers_data_<YYYY-MM-DD>.csv
```

### Temperature / Humidity Pipeline

Files:

- `be/com4_reader.py`
- `be/data_pipeline.py`

`com4_reader.py` opens a serial connection to the temperature/humidity instrument and normalizes readings into:

```text
T1,H1,T2,H2
```

`data_pipeline.py` starts the Flask API server as a subprocess, polls the serial reader, computes IST/UTC/MJD timestamps, and writes temperature/humidity CSV files into:

```text
Database/Temp_Humidity_data/<Month_Year>/Temp_Humidity_data_<YYYY-MM-DD>.csv
```

Current backend defaults:

```text
COM_PORT = COM6
COM_BAUDRATE = 9600
POLL_INTERVAL = 120 seconds
```

### Dash Dashboard

File: `fe/dash_app.py`

This is the main frontend entry point.

The dashboard includes:

- Overview page for all subsystems.
- Temperature and humidity page.
- Laser monitoring page.
- Photodiode monitoring page.
- Historical data plotting and CSV download page.

The app reads CSV files through `fe/csv_reader.py` and refreshes live views every 10 seconds.

Default dashboard server:

```text
host = 0.0.0.0
port = 8000
```

## CSV Storage Format

The project stores data in a month-based directory structure:

```text
Database/<Data_Type>/<Month_Year>/<Data_Type>_<YYYY-MM-DD>.csv
```

Examples:

```text
Database/Temp_Humidity_data/September_2025/Temp_Humidity_data_2025-09-27.csv
Database/Lasers_data/September_2025/Lasers_data_2025-09-27.csv
Database/Photodiode_data/September_2025/Photodiode_data_2025-09-27.csv
```

Temperature/humidity schema:

```text
timestamp,UTC_timestamp,MJD,T1,H1,T2,H2
```

Laser schema:

```text
timestamp,UTC_timestamp,MJD,X1,X2,Y1,Y2,Z1,Z2,D1,D2
```

Photodiode schema:

```text
timestamp,UTC_timestamp,MJD,P1,P2,P3,P4,P5
```

## Python Setup

Python 3.10 or newer is recommended. The current local environment was checked with Python 3.10.6.

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Running The System

### Run only the dashboard

Use this when you already have CSV data and only want to view or download it.

```bash
python fe/dash_app.py
```

Then open:

```text
http://localhost:8000
```

If accessing from another machine on the same network, use the host machine IP:

```text
http://<host-ip>:8000
```

### Run only the API server

Use this when the ESP8266 is posting laser and photodiode data, but you do not need the serial temperature/humidity pipeline.

```bash
python be/sensor_api_server.py
```

Health check:

```text
http://localhost:5176/health
```

### Run the full backend pipeline

Use this when the temperature/humidity device is connected to the configured serial port and the API server should also be started.

```bash
python be/data_pipeline.py
```

This starts `sensor_api_server.py` and begins polling the serial device.

## Public Demo Deployment

For a portfolio link, deploy this as a demo dashboard that reads the included CSV files from `Database/`.

The cloud deployment does not connect to local lab hardware. It will not read the serial `COM6` device, and it will not receive ESP8266 requests from the lab network unless a public backend is configured separately. This is intentional for a portfolio demo: visitors can view the interface and historical sample data without needing access to the lab.

### Deployment Files

The repository includes these hosting-specific files:

- `app.py`: production import target for Gunicorn.
- `Dockerfile`: container build instructions for Hugging Face Spaces or another Docker host.
- `requirements.txt`: Python dependencies, including `gunicorn`.
- `.gitignore`: ignores virtual environments, bytecode, logs, and local environment files.

### Recommended Free Host

Use Hugging Face Spaces with the Docker SDK.

Suggested Space settings:

```text
SDK: Docker
Visibility: Public
App port: 7860
```

The Docker container runs:

```bash
gunicorn app:server --bind 0.0.0.0:7860 --workers 2
```

### Hugging Face Spaces Steps

1. Create a Hugging Face account.
2. Create a new Space.
3. Select `Docker` as the Space SDK.
4. Choose `Public` visibility for a portfolio-friendly link.
5. Push or upload this repository to the Space.
6. Wait for the Space build to finish.
7. Open the generated `.hf.space` URL and add it to your portfolio.

The public app URL will look like:

```text
https://<username>-<space-name>.hf.space
```

### Portfolio Description

Suggested wording:

```text
CsF1 Sensor Monitoring Dashboard: a Dash-based laboratory monitoring system for temperature, humidity, laser alignment, and photodiode signals. The public demo uses historical CSV data; the full system supports ESP8266 and serial-device ingestion.
```

## Historical Data Retrieval

The dashboard data retrieval page lets you select:

- Data source: temperature/humidity, lasers, or photodiodes.
- Start date.
- End date.

It can then:

- Plot matching historical readings.
- Download the selected range as CSV.

The reader functions live in `fe/csv_reader.py`.

## Configuration Checklist

Before running against real hardware, check these values:

- `aurduino.cpp`: WiFi SSID and password.
- `aurduino.cpp`: backend server IP and port.
- `be/com4_reader.py`: default serial port.
- `be/data_pipeline.py`: `COM_PORT`, `COM_BAUDRATE`, and `POLL_INTERVAL`.
- `fe/dash_app.py`: dashboard host and port.

## Arduino Dependencies

The Arduino sketch needs:

- ESP8266 board support installed in the Arduino IDE.
- `ESP8266WiFi`.
- `Adafruit_ADS1X15`.

These are not installed by `requirements.txt`; they are Arduino-side dependencies.

## Troubleshooting

If the dashboard shows empty values:

- Confirm that matching CSV files exist under `Database/`.
- Confirm that the filenames include the date in `YYYY-MM-DD` format.
- Confirm that each CSV contains the expected headers.
- Confirm that the dashboard is reading from this project root, not another copied folder.

If ESP8266 data is not saved:

- Start `be/sensor_api_server.py`.
- Visit `/health` to confirm the API is running.
- Confirm the ESP8266 `server` IP matches the backend machine IP.
- Confirm port `5176` is reachable on the network.
- Check that POST data includes all required fields: `P1` through `P5` and `X1` through `D2`.

If temperature/humidity data is not saved:

- Confirm the serial device is connected.
- Confirm the configured COM port is correct.
- Confirm no other program is holding the serial port open.
- Confirm the serial output can be normalized to `T1,H1,T2,H2`.

## Notes

- The old duplicate dashboard file was removed. The canonical dashboard is now `fe/dash_app.py`.
- WiFi credentials are currently hardcoded in `aurduino.cpp`. Avoid sharing this repository publicly without replacing or removing them.
- The backend uses Flask's development server. For production deployment, use a WSGI server and a controlled network environment.
