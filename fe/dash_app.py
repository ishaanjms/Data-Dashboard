import os
import sys
from datetime import datetime, timedelta
import dash
from dash import dcc, html, Output, Input, State, callback_context
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import io
import base64
from flask import send_file
import csv

# Add parent directory to path to import from project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import modules
from fe.csv_reader import (
    get_latest_temp_humidity, get_temp_humidity_plot_data,
    get_latest_laser, get_laser_plot_data,
    get_latest_photodiode, get_photodiode_plot_data,
    read_data_by_range, DATASET_BASE_DIR
)

from fe.design import design_string

# Constants
REFRESH_INTERVAL_SECONDS = 10
MAX_POINTS = 50
CURRENT_DATETIME = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Initialize the app
app = dash.Dash(
    __name__, 
    title="CsF1 Monitoring Dashboard",
    assets_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets'),
    update_title=None,  # Don't show "Updating..." title
    suppress_callback_exceptions=True  # Suppress exceptions for components not in the initial layout
)

app.index_string = design_string()
server = app.server

# Define reusable components for modular design
def create_sidebar():
    """Create the sidebar navigation component."""
    return html.Div(
        className="sidebar",
        id="sidebar",
        children=[
            html.Div(
                className="sidebar-header",
                children=[
                    # The html.Img line that was here has been removed
                    html.H2("CsF1", style={"margin": "10px 0", "color": "#00ffff"}),
                ],
                style={"display": "flex", "alignItems": "center", "justifyContent": "center", "padding": "20px", "borderBottom": "1px solid #00ffff30"}
            ),
            html.Button(
                id="sidebar-toggle",
                className="sidebar-toggle",
                children=html.I(className="fa fa-chevron-left")
            ),
            html.Div(
                className="nav-links",
                children=[
                    html.A(
                        className="nav-link",
                        id="temp-humidity-link",
                        href="#",
                        children=[
                            html.Img(src="assets/Temperature.svg", alt="Temperature & Humidity"),
                            html.Span("Temperature & Humidity")
                        ]
                    ),
                    html.A(
                        className="nav-link",
                        id="laser-link",
                        href="#",
                        children=[
                            html.Img(src="assets/Laser.svg", alt="Lasers"),
                            html.Span("Lasers")
                        ]
                    ),
                    html.A(
                        className="nav-link",
                        id="photodiode-link",
                        href="#",
                        children=[
                            html.Img(src="assets/Photodiode.svg", alt="Photodiodes"),
                            html.Span("Photodiodes")
                        ]
                    ),
                    
                    html.Hr(style={'borderColor': 'rgba(0, 255, 255, 0.2)', 'margin': '15px 10px'}),
                    
                    html.A(
                        className="nav-link",
                        id="data-retrieval-link",
                        href="#",
                        children=[
                            html.I(className="fa fa-download"),
                            html.Span("Retrieve Data")
                        ]
                    ),
                ],
                style={"marginTop": "20px"}
            ),
        ]
    )

def create_header(title, subtitle):
    """Create a header component with title and subtitle."""
    return html.Div(
        className="dashboard-header",
        children=[
            html.H1(title, className="header-title"),
            html.P(subtitle, className="header-subtitle"),
            html.Div(
                id="connection-status",
                className="connection-status",
                children=[
                    html.Span(className="status-indicator status-connected"),
                    html.Span(id="connection-text", children=f"Connected | Last Update: {CURRENT_DATETIME}")
                ],
                style={"textAlign": "right", "fontSize": "0.8rem"}
            )
        ]
    )

def create_sensor_value_card(title, value, unit, color):
    """Create a card displaying a sensor value with styling."""
    return html.Div(
        className="sensor-card",
        children=[
            html.H3(title, style={"textAlign": "center", "color": "#ffffff"}),
            html.Div(
                className="value-display",
                style={"color": color},
                children=value
            ),
            html.Div(
                style={"textAlign": "center", "color": "#aaaaaa"},
                children=unit
            )
        ]
    )

def create_graph_card(id, title):
    """Create a card containing a graph with title."""
    return html.Div(
        className="graph-container",
        children=[
            html.H3(title, style={"marginBottom": "20px"}),
            dcc.Graph(
                id=id,
                config={'displayModeBar': False},
                style={"height": "300px"}
            )
        ]
    )

def create_sensor_selector(id, options):
    """Create a component for selecting which sensors to display."""
    return html.Div(
        style={"marginBottom": "15px", "display": "flex", "justifyContent": "center"},
        children=[
            dcc.RadioItems(
                id=id,
                options=options,
                value="both",
                inline=True,
                labelStyle={
                    "marginRight": "20px",
                    "cursor": "pointer",
                    "display": "inline-flex",
                    "alignItems": "center"
                },
                style={"display": "flex", "justifyContent": "center"}
            )
        ]
    )

# Define the layout for each page
def temp_humidity_layout():
    """Create the Temperature & Humidity page layout."""
    return html.Div([
        create_header("Temperature & Humidity", "Real-time Monitoring Dashboard"),
        
        # Current Values Section
        html.Div(
            className="row",
            style={"display": "flex", "justifyContent": "space-around"},
            children=[
                html.Div(
                    className="col",
                    style={"flex": "1"},
                    children=[
                        html.Div(
                            className="sensor-card",
                            children=[
                                html.H3("Sensor 1", style={"textAlign": "center", "color": "#ffffff"}),
                                html.Div(
                                    className="value-display temp-value",
                                    id="temp1-value",
                                    children="--.-"
                                ),
                                html.Div(
                                    style={"textAlign": "center", "color": "#aaaaaa"},
                                    children="Temperature (°C)"
                                ),
                                html.Div(
                                    className="value-display humidity-value",
                                    id="humidity1-value",
                                    children="--.-"
                                ),
                                html.Div(
                                    style={"textAlign": "center", "color": "#aaaaaa"},
                                    children="Humidity (%)"
                                )
                            ]
                        )
                    ]
                ),
                
                html.Div(
                    className="col",
                    style={"flex": "1"},
                    children=[
                        html.Div(
                            className="sensor-card",
                            children=[
                                html.H3("Sensor 2", style={"textAlign": "center", "color": "#ffffff"}),
                                html.Div(
                                    className="value-display temp-value",
                                    id="temp2-value",
                                    children="--.-"
                                ),
                                html.Div(
                                    style={"textAlign": "center", "color": "#aaaaaa"},
                                    children="Temperature (°C)"
                                ),
                                html.Div(
                                    className="value-display humidity-value",
                                    id="humidity2-value",
                                    children="--.-"
                                ),
                                html.Div(
                                    style={"textAlign": "center", "color": "#aaaaaa"},
                                    children="Humidity (%)"
                                )
                            ]
                        )
                    ]
                ),
            ]
        ),
        
        # Graphs Section
        html.Div(
            style={"display": "flex", "flexWrap": "wrap"},
            children=[
                html.Div(
                    style={"flex": "1 1 50%", "minWidth": "400px"},
                    children=[
                        create_sensor_selector(
                            "temp-sensor-selector",
                            [
                                {"label": html.Span([html.Span(className="status-indicator status-connected"), "Both Sensors"]), "value": "both"},
                                {"label": html.Span([html.Span(className="status-indicator", style={"backgroundColor": "#ff0000"}), "Sensor 1"]), "value": "sensor1"},
                                {"label": html.Span([html.Span(className="status-indicator", style={"backgroundColor": "#00ffff"}), "Sensor 2"]), "value": "sensor2"}
                            ]
                        ),
                        create_graph_card("temperature-graph", "Temperature (°C)")
                    ]
                ),
                html.Div(
                    style={"flex": "1 1 50%", "minWidth": "400px"},
                    children=[
                        create_sensor_selector(
                            "humidity-sensor-selector",
                            [
                                {"label": html.Span([html.Span(className="status-indicator status-connected"), "Both Sensors"]), "value": "both"},
                                {"label": html.Span([html.Span(className="status-indicator", style={"backgroundColor": "#ff0000"}), "Sensor 1"]), "value": "sensor1"},
                                {"label": html.Span([html.Span(className="status-indicator", style={"backgroundColor": "#00ffff"}), "Sensor 2"]), "value": "sensor2"}
                            ]
                        ),
                        create_graph_card("humidity-graph", "Humidity (%)")
                    ]
                )
            ]
        ),
        
        # Refresh interval component (hidden)
        dcc.Interval(
            id='temp-humidity-interval',
            interval=REFRESH_INTERVAL_SECONDS * 1000,  # in milliseconds
            n_intervals=0
        )
    ])

def lasers_layout():
    """Create the Lasers page layout."""
    return html.Div([
        create_header("Lasers", "Real-time Laser Position Monitoring"),
        
        # Current Values Section - X and Y Axis
        html.Div(
            style={"display": "flex", "flexWrap": "wrap", "justifyContent": "space-around"},
            children=[
                html.Div(
                    className="sensor-card",
                    style={"flex": "1", "minWidth": "300px", "border": "1px solid #9eff00"},
                    children=[
                        html.H3("X Axis", style={"textAlign": "center", "color": "#9eff00"}),
                        html.Div(
                            style={"display": "flex", "justifyContent": "space-around"},
                            children=[
                                html.Div(
                                    style={"textAlign": "center"},
                                    children=[
                                        html.Div("X1", style={"color": "#9eff00", "marginBottom": "5px"}),
                                        html.Div(
                                            id="x1-value",
                                            className="value-display",
                                            style={"color": "#9eff00", "fontSize": "2rem"},
                                            children="-.----"
                                        )
                                    ]
                                ),
                                html.Div(
                                    style={"textAlign": "center"},
                                    children=[
                                        html.Div("X2", style={"color": "#00ffff", "marginBottom": "5px"}),
                                        html.Div(
                                            id="x2-value",
                                            className="value-display",
                                            style={"color": "#00ffff", "fontSize": "2rem"},
                                            children="-.----"
                                        )
                                    ]
                                )
                            ]
                        )
                    ]
                ),
                
                html.Div(
                    className="sensor-card",
                    style={"flex": "1", "minWidth": "300px", "border": "1px solid #00ffff"},
                    children=[
                        html.H3("Y Axis", style={"textAlign": "center", "color": "#00ffff"}),
                        html.Div(
                            style={"display": "flex", "justifyContent": "space-around"},
                            children=[
                                html.Div(
                                    style={"textAlign": "center"},
                                    children=[
                                        html.Div("Y1", style={"color": "#9eff00", "marginBottom": "5px"}),
                                        html.Div(
                                            id="y1-value",
                                            className="value-display",
                                            style={"color": "#9eff00", "fontSize": "2rem"},
                                            children="-.----"
                                        )
                                    ]
                                ),
                                html.Div(
                                    style={"textAlign": "center"},
                                    children=[
                                        html.Div("Y2", style={"color": "#00ffff", "marginBottom": "5px"}),
                                        html.Div(
                                            id="y2-value",
                                            className="value-display",
                                            style={"color": "#00ffff", "fontSize": "2rem"},
                                            children="-.----"
                                        )
                                    ]
                                )
                            ]
                        )
                    ]
                ),
            ]
        ),
        
        # Current Values Section - Z and D Axis
        html.Div(
            style={"display": "flex", "flexWrap": "wrap", "justifyContent": "space-around", "marginTop": "20px"},
            children=[
                html.Div(
                    className="sensor-card",
                    style={"flex": "1", "minWidth": "300px", "border": "1px solid #9eff00"},
                    children=[
                        html.H3("Z Axis", style={"textAlign": "center", "color": "#9eff00"}),
                        html.Div(
                            style={"display": "flex", "justifyContent": "space-around"},
                            children=[
                                html.Div(
                                    style={"textAlign": "center"},
                                    children=[
                                        html.Div("Z1", style={"color": "#9eff00", "marginBottom": "5px"}),
                                        html.Div(
                                            id="z1-value",
                                            className="value-display",
                                            style={"color": "#9eff00", "fontSize": "2rem"},
                                            children="-.----"
                                        )
                                    ]
                                ),
                                html.Div(
                                    style={"textAlign": "center"},
                                    children=[
                                        html.Div("Z2", style={"color": "#00ffff", "marginBottom": "5px"}),
                                        html.Div(
                                            id="z2-value",
                                            className="value-display",
                                            style={"color": "#00ffff", "fontSize": "2rem"},
                                            children="-.----"
                                        )
                                    ]
                                )
                            ]
                        )
                    ]
                ),
                
                html.Div(
                    className="sensor-card",
                    style={"flex": "1", "minWidth": "300px", "border": "1px solid #00ffff"},
                    children=[
                        html.H3("D Axis", style={"textAlign": "center", "color": "#00ffff"}),
                        html.Div(
                            style={"display": "flex", "justifyContent": "space-around"},
                            children=[
                                html.Div(
                                    style={"textAlign": "center"},
                                    children=[
                                        html.Div("D1", style={"color": "#9eff00", "marginBottom": "5px"}),
                                        html.Div(
                                            id="d1-value",
                                            className="value-display",
                                            style={"color": "#9eff00", "fontSize": "2rem"},
                                            children="-.----"
                                        )
                                    ]
                                ),
                                html.Div(
                                    style={"textAlign": "center"},
                                    children=[
                                        html.Div("D2", style={"color": "#00ffff", "marginBottom": "5px"}),
                                        html.Div(
                                            id="d2-value",
                                            className="value-display",
                                            style={"color": "#00ffff", "fontSize": "2rem"},
                                            children="-.----"
                                        )
                                    ]
                                )
                            ]
                        )
                    ]
                ),
            ]
        ),
        
        # Graphs Section
        html.Div(
            style={"display": "flex", "flexWrap": "wrap", "marginTop": "20px"},
            children=[
                html.Div(
                    style={"flex": "1 1 50%", "minWidth": "400px"},
                    children=[
                        create_graph_card("x-axis-graph", "X-Axis Laser Readings")
                    ]
                ),
                html.Div(
                    style={"flex": "1 1 50%", "minWidth": "400px"},
                    children=[
                        create_graph_card("y-axis-graph", "Y-Axis Laser Readings")
                    ]
                ),
            ]
        ),
        
        html.Div(
            style={"display": "flex", "flexWrap": "wrap", "marginTop": "20px"},
            children=[
                html.Div(
                    style={"flex": "1 1 50%", "minWidth": "400px"},
                    children=[
                        create_graph_card("z-axis-graph", "Z-Axis Laser Readings")
                    ]
                ),
                html.Div(
                    style={"flex": "1 1 50%", "minWidth": "400px"},
                    children=[
                        create_graph_card("d-axis-graph", "D-Axis Laser Readings")
                    ]
                ),
            ]
        ),
        
        # Refresh interval component (hidden)
        dcc.Interval(
            id='lasers-interval',
            interval=REFRESH_INTERVAL_SECONDS * 1000,  # in milliseconds
            n_intervals=0
        )
    ])

def photodiodes_layout():
    """Create the Photodiodes page layout."""
    return html.Div([
        create_header("Photodiodes", "Real-time Photodiode Monitoring"),
        
        # Photodiode Selection Section
        html.Div(
            style={"display": "flex", "justifyContent": "center", "flexWrap": "wrap", "gap": "10px", "marginBottom": "20px"},
            children=[
                html.Button(
                    id="pd1-button",
                    className="sensor-card",
                    style={"padding": "15px", "cursor": "pointer", "backgroundColor": "rgba(0, 255, 0, 0.3)"},
                    children=[
                        html.H3("PD1", style={"margin": "0 0 5px 0", "color": "#9eff00"}),
                        html.Div(id="pd1-value", style={"color": "#9eff00", "fontWeight": "bold"})
                    ]
                ),
                html.Button(
                    id="pd2-button",
                    className="sensor-card",
                    style={"padding": "15px", "cursor": "pointer", "backgroundColor": "rgba(0, 255, 255, 0.3)"},
                    children=[
                        html.H3("PD2", style={"margin": "0 0 5px 0", "color": "#00ffff"}),
                        html.Div(id="pd2-value", style={"color": "#00ffff", "fontWeight": "bold"})
                    ]
                ),
                html.Button(
                    id="pd3-button",
                    className="sensor-card",
                    style={"padding": "15px", "cursor": "pointer", "backgroundColor": "rgba(0, 255, 0, 0.3)"},
                    children=[
                        html.H3("PD3", style={"margin": "0 0 5px 0", "color": "#9eff00"}),
                        html.Div(id="pd3-value", style={"color": "#9eff00", "fontWeight": "bold"})
                    ]
                ),
                html.Button(
                    id="pd4-button",
                    className="sensor-card",
                    style={"padding": "15px", "cursor": "pointer", "backgroundColor": "rgba(0, 255, 255, 0.3)"},
                    children=[
                        html.H3("PD4", style={"margin": "0 0 5px 0", "color": "#00ffff"}),
                        html.Div(id="pd4-value", style={"color": "#00ffff", "fontWeight": "bold"})
                    ]
                ),
                html.Button(
                    id="pd5-button",
                    className="sensor-card",
                    style={"padding": "15px", "cursor": "pointer", "backgroundColor": "rgba(0, 255, 0, 0.3)"},
                    children=[
                        html.H3("PD5", style={"margin": "0 0 5px 0", "color": "#9eff00"}),
                        html.Div(id="pd5-value", style={"color": "#9eff00", "fontWeight": "bold"})
                    ]
                ),
            ]
        ),
        
        # Graph Section
        html.Div(
            className="sensor-card",
            style={"margin": "20px"},
            children=[
                html.H3("Photodiode Readings", style={"textAlign": "center", "color": "#9eff00", "marginBottom": "20px"}),
                dcc.Graph(
                    id="photodiode-graph",
                    config={'displayModeBar': False},
                    style={"height": "500px"},
                    figure=go.Figure(
                        layout={
                            "template": "plotly_dark",
                            "paper_bgcolor": "rgba(0,0,0,0)",
                            "plot_bgcolor": "rgba(0,0,0,0)",
                            "margin": dict(l=40, r=20, t=10, b=30),
                            "xaxis": {
                                "showgrid": True,
                                "gridcolor": "rgba(255,255,255,0.1)",
                                "title": "Time"
                            },
                            "yaxis": {
                                "showgrid": True,
                                "gridcolor": "rgba(255,255,255,0.1)",
                                "title": "Value"
                            },
                        }
                    )
                )
            ]
        ),
        
        # Store active photodiodes (hidden) - initialize with all photodiodes active
        dcc.Store(id='active-photodiodes', data=['P1', 'P2', 'P3', 'P4', 'P5']),
        
        # Refresh interval component (hidden)
        dcc.Interval(
            id='photodiodes-interval',
            interval=REFRESH_INTERVAL_SECONDS * 1000,  # in milliseconds
            n_intervals=0
        )
    ])

def data_retrieval_layout():
    """Create the Data Retrieval page layout."""
    return html.Div([
        create_header("Retrieve Data", "Download historical data for analysis"),
        
        # Data Selection Form
        html.Div(
            className="sensor-card",
            style={"maxWidth": "600px", "margin": "20px auto"},
            children=[
                # Data Type Selection
                html.Div(
                    style={"marginBottom": "20px"},
                    children=[
                        html.Label("Select Data Type:", style={"display": "block", "marginBottom": "10px"}),
                        dcc.RadioItems(
                            id="data-type-selector",
                            options=[
                                {'label': 'Temperature & Humidity', 'value': 'Temp_Humidity_data'},
                                {'label': 'Lasers', 'value': 'Lasers_data'},
                                {'label': 'Photodiode', 'value': 'Photodiode_data'}
                            ],
                            value='Temp_Humidity_data',
                            labelStyle={
                                "marginRight": "20px",
                                "cursor": "pointer",
                                "display": "block",
                                "marginBottom": "10px"
                            },
                            inputStyle={"marginRight": "5px"},
                        ),
                    ]
                ),
                
                # Date Range Selection
                html.Div(
                    style={"marginBottom": "20px"},
                    children=[
                        html.Label("Select Date Range:", style={"display": "block", "marginBottom": "10px"}),
                        html.Div(
                            style={"display": "flex", "gap": "20px"},
                            children=[
                                html.Div(
                                    style={"flex": "1"},
                                    children=[
                                        html.Label("Start Date", style={"fontSize": "0.8rem", "color": "#aaaaaa"}),
                                        dcc.DatePickerSingle(
                                            id='start-date-picker',
                                            date=datetime.now().date(),
                                            display_format='YYYY-MM-DD',
                                            style={"width": "100%"}
                                        )
                                    ]
                                ),
                                html.Div(
                                    style={"flex": "1"},
                                    children=[
                                        html.Label("End Date", style={"fontSize": "0.8rem", "color": "#aaaaaa"}),
                                        dcc.DatePickerSingle(
                                            id='end-date-picker',
                                            date=datetime.now().date(),
                                            display_format='YYYY-MM-DD',
                                            style={"width": "100%"}
                                        )
                                    ]
                                )
                            ]
                        )
                    ]
                ),
                
                # Download Button
                html.Button(
                    id="download-button",
                    children="Download CSV",
                    style={
                        "backgroundColor": "#00ffff",
                        "border": "none",
                        "color": "#000000",
                        "padding": "10px 20px",
                        "borderRadius": "5px",
                        "fontSize": "1rem",
                        "fontWeight": "bold",
                        "cursor": "pointer",
                        "width": "100%",
                        "transition": "all 0.3s",
                        "boxShadow": "0 0 10px rgba(0,255,255,0.5)"
                    }
                ),
                dcc.Download(id="download-data")
            ]
        )
    ])

# Define the main layout with URL routing
app.layout = html.Div([
    # Store current page
    dcc.Store(id='current-page', data='temp-humidity'),
    
    # Main components
    create_sidebar(),
    
    html.Div(
        id="main-content",
        className="main-content",
        children=[temp_humidity_layout()]
    )
])

# --- CALLBACKS ---

# Sidebar toggle callback
@app.callback(
    [Output('sidebar', 'className'),
     Output('main-content', 'className')],
    [Input('sidebar-toggle', 'n_clicks')],
    [State('sidebar', 'className')]
)
def toggle_sidebar(n_clicks, current_class):
    if n_clicks is None:
        return "sidebar", "main-content"
    
    if current_class == "sidebar":
        return "sidebar collapsed", "main-content expanded"
    else:
        return "sidebar", "main-content"

# Navigation callbacks
@app.callback(
    [Output('main-content', 'children'),
     Output('current-page', 'data'),
     Output('temp-humidity-link', 'className'),
     Output('laser-link', 'className'),
     Output('photodiode-link', 'className'),
     Output('data-retrieval-link', 'className')],
    [Input('temp-humidity-link', 'n_clicks'),
     Input('laser-link', 'n_clicks'),
     Input('photodiode-link', 'n_clicks'),
     Input('data-retrieval-link', 'n_clicks')],
    [State('current-page', 'data')]
)
def navigate_pages(temp_click, laser_click, photodiode_click, data_click, current_page):
    ctx = callback_context
    
    if not ctx.triggered:
        # Default page
        return temp_humidity_layout(), 'temp-humidity', 'nav-link active', 'nav-link', 'nav-link', 'nav-link'
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'temp-humidity-link':
        return temp_humidity_layout(), 'temp-humidity', 'nav-link active', 'nav-link', 'nav-link', 'nav-link'
    elif button_id == 'laser-link':
        return lasers_layout(), 'lasers', 'nav-link', 'nav-link active', 'nav-link', 'nav-link'
    elif button_id == 'photodiode-link':
        return photodiodes_layout(), 'photodiodes', 'nav-link', 'nav-link', 'nav-link active', 'nav-link'
    elif button_id == 'data-retrieval-link':
        return data_retrieval_layout(), 'data-retrieval', 'nav-link', 'nav-link', 'nav-link', 'nav-link active'
    
    # Fallback
    return temp_humidity_layout(), 'temp-humidity', 'nav-link active', 'nav-link', 'nav-link', 'nav-link'

# Temperature & Humidity callbacks
@app.callback(
    [Output('temp1-value', 'children'),
     Output('humidity1-value', 'children'),
     Output('temp2-value', 'children'),
     Output('humidity2-value', 'children'),
     Output('temperature-graph', 'figure'),
     Output('humidity-graph', 'figure'),
     Output('connection-text', 'children')],
    [Input('temp-humidity-interval', 'n_intervals'),
     Input('temp-sensor-selector', 'value'),
     Input('humidity-sensor-selector', 'value')],
    [State('current-page', 'data')]
)
def update_temp_humidity(n, temp_sensor, humidity_sensor, current_page):
    # Only update if we're on the temp humidity page
    if current_page != 'temp-humidity':
        raise PreventUpdate
    
    # Get latest data
    latest_data = get_latest_temp_humidity(os.path.join(DATASET_BASE_DIR, 'Temp_Humidity_data'))
    plot_data = get_temp_humidity_plot_data(os.path.join(DATASET_BASE_DIR, 'Temp_Humidity_data'), MAX_POINTS)
    
    # Update timestamp
    update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if latest_data and latest_data.get('timestamp'):
        update_time = latest_data['timestamp'].strftime("%H:%M:%S")
    connection_text = f"Connected | Last Update: {update_time}"
    
    # Format current values
    temp1 = f"{latest_data['temp1']:.2f}" if latest_data and latest_data.get('temp1') is not None else "--.-"
    hum1 = f"{latest_data['humidity1']:.2f}" if latest_data and latest_data.get('humidity1') is not None else "--.-"
    temp2 = f"{latest_data['temp2']:.2f}" if latest_data and latest_data.get('temp2') is not None else "--.-"
    hum2 = f"{latest_data['humidity2']:.2f}" if latest_data and latest_data.get('humidity2') is not None else "--.-"
    
    # Create temperature graph
    temp_fig = go.Figure()
    temp_fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=20, t=10, b=30),
        xaxis=dict(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.1)",
            title="Time Points"
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.1)",
            title="Temperature (°C)"
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        ),
    )
    
    # Add temperature traces based on selection
    if temp_sensor in ['both', 'sensor1']:
        temp_fig.add_trace(go.Scatter(
            x=plot_data['time_points'],
            y=plot_data['temp1'],
            mode='lines',
            name='Sensor 1',
            line=dict(color='#ff0000', width=2)
        ))
    
    if temp_sensor in ['both', 'sensor2']:
        temp_fig.add_trace(go.Scatter(
            x=plot_data['time_points'],
            y=plot_data['temp2'],
            mode='lines',
            name='Sensor 2',
            line=dict(color='#00ffff', width=2)
        ))
    
    # Create humidity graph
    hum_fig = go.Figure()
    hum_fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=20, t=10, b=30),
        xaxis=dict(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.1)",
            title="Time Points"
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.1)",
            title="Humidity (%)"
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        ),
    )
    
    # Add humidity traces based on selection
    if humidity_sensor in ['both', 'sensor1']:
        hum_fig.add_trace(go.Scatter(
            x=plot_data['time_points'],
            y=plot_data['humidity1'],
            mode='lines',
            name='Sensor 1',
            line=dict(color='#ff0000', width=2)
        ))
    
    if humidity_sensor in ['both', 'sensor2']:
        hum_fig.add_trace(go.Scatter(
            x=plot_data['time_points'],
            y=plot_data['humidity2'],
            mode='lines',
            name='Sensor 2',
            line=dict(color='#00ffff', width=2)
        ))
    
    return temp1, hum1, temp2, hum2, temp_fig, hum_fig, connection_text

# Lasers callbacks
@app.callback(
    [Output('x1-value', 'children'),
     Output('x2-value', 'children'),
     Output('y1-value', 'children'),
     Output('y2-value', 'children'),
     Output('z1-value', 'children'),
     Output('z2-value', 'children'),
     Output('d1-value', 'children'),
     Output('d2-value', 'children'),
     Output('x-axis-graph', 'figure'),
     Output('y-axis-graph', 'figure'),
     Output('z-axis-graph', 'figure'),
     Output('d-axis-graph', 'figure')],
    [Input('lasers-interval', 'n_intervals')],
    [State('current-page', 'data')]
)
def update_lasers(n, current_page):
    # Only update if we're on the lasers page
    if current_page != 'lasers':
        raise PreventUpdate
    
    # Get latest data
    latest_data = get_latest_laser(os.path.join(DATASET_BASE_DIR, 'Lasers_data'))
    plot_data = get_laser_plot_data(os.path.join(DATASET_BASE_DIR, 'Lasers_data'), MAX_POINTS)
    
    # Format current values
    x1 = f"{latest_data['X1']:.4f}" if latest_data and latest_data.get('X1') is not None else "-.----"
    x2 = f"{latest_data['X2']:.4f}" if latest_data and latest_data.get('X2') is not None else "-.----"
    y1 = f"{latest_data['Y1']:.4f}" if latest_data and latest_data.get('Y1') is not None else "-.----"
    y2 = f"{latest_data['Y2']:.4f}" if latest_data and latest_data.get('Y2') is not None else "-.----"
    z1 = f"{latest_data['Z1']:.4f}" if latest_data and latest_data.get('Z1') is not None else "-.----"
    z2 = f"{latest_data['Z2']:.4f}" if latest_data and latest_data.get('Z2') is not None else "-.----"
    d1 = f"{latest_data['D1']:.4f}" if latest_data and latest_data.get('D1') is not None else "-.----"
    d2 = f"{latest_data['D2']:.4f}" if latest_data and latest_data.get('D2') is not None else "-.----"
    
    # Base figure settings
    def create_base_figure(title, y_title):
        fig = go.Figure()
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=40, r=20, t=10, b=30),
            xaxis=dict(
                showgrid=True,
                gridcolor="rgba(255,255,255,0.1)",
                title="Time Points"
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor="rgba(255,255,255,0.1)",
                title=y_title
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5
            ),
        )
        return fig
    
    # Create X axis graph
    x_fig = create_base_figure("X-Axis Laser Readings", "Position (mm)")
    x_fig.add_trace(go.Scatter(
        x=plot_data['time_points'],
        y=plot_data['X1'],
        mode='lines',
        name='X1',
        line=dict(color='#9eff00', width=2)
    ))
    x_fig.add_trace(go.Scatter(
        x=plot_data['time_points'],
        y=plot_data['X2'],
        mode='lines',
        name='X2',
        line=dict(color='#00ffff', width=2)
    ))
    
    # Create Y axis graph
    y_fig = create_base_figure("Y-Axis Laser Readings", "Position (mm)")
    y_fig.add_trace(go.Scatter(
        x=plot_data['time_points'],
        y=plot_data['Y1'],
        mode='lines',
        name='Y1',
        line=dict(color='#9eff00', width=2)
    ))
    y_fig.add_trace(go.Scatter(
        x=plot_data['time_points'],
        y=plot_data['Y2'],
        mode='lines',
        name='Y2',
        line=dict(color='#00ffff', width=2)
    ))
    
    # Create Z axis graph
    z_fig = create_base_figure("Z-Axis Laser Readings", "Position (mm)")
    z_fig.add_trace(go.Scatter(
        x=plot_data['time_points'],
        y=plot_data['Z1'],
        mode='lines',
        name='Z1',
        line=dict(color='#9eff00', width=2)
    ))
    z_fig.add_trace(go.Scatter(
        x=plot_data['time_points'],
        y=plot_data['Z2'],
        mode='lines',
        name='Z2',
        line=dict(color='#00ffff', width=2)
    ))
    
    # Create D axis graph
    d_fig = create_base_figure("D-Axis Laser Readings", "Position (mm)")
    d_fig.add_trace(go.Scatter(
        x=plot_data['time_points'],
        y=plot_data['D1'],
        mode='lines',
        name='D1',
        line=dict(color='#9eff00', width=2)
    ))
    d_fig.add_trace(go.Scatter(
        x=plot_data['time_points'],
        y=plot_data['D2'],
        mode='lines',
        name='D2',
        line=dict(color='#00ffff', width=2)
    ))
    
    return x1, x2, y1, y2, z1, z2, d1, d2, x_fig, y_fig, z_fig, d_fig

# Photodiode button callbacks
@app.callback(
    [Output('pd1-button', 'style'),
     Output('pd2-button', 'style'),
     Output('pd3-button', 'style'),
     Output('pd4-button', 'style'),
     Output('pd5-button', 'style'),
     Output('active-photodiodes', 'data')],
    [Input('pd1-button', 'n_clicks'),
     Input('pd2-button', 'n_clicks'),
     Input('pd3-button', 'n_clicks'),
     Input('pd4-button', 'n_clicks'),
     Input('pd5-button', 'n_clicks')],
    [State('active-photodiodes', 'data')]
)
def toggle_photodiodes(pd1_clicks, pd2_clicks, pd3_clicks, pd4_clicks, pd5_clicks, active_pds):
    ctx = callback_context
    if not ctx.triggered:
        # Default active PDs - all photodiodes active
        return (
            {"padding": "15px", "cursor": "pointer", "backgroundColor": "rgba(0, 255, 0, 0.3)"},
            {"padding": "15px", "cursor": "pointer", "backgroundColor": "rgba(0, 255, 255, 0.3)"},
            {"padding": "15px", "cursor": "pointer", "backgroundColor": "rgba(0, 255, 0, 0.3)"},
            {"padding": "15px", "cursor": "pointer", "backgroundColor": "rgba(0, 255, 255, 0.3)"},
            {"padding": "15px", "cursor": "pointer", "backgroundColor": "rgba(0, 255, 0, 0.3)"},
            ['P1', 'P2', 'P3', 'P4', 'P5']
        )
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Toggle the clicked PD
    pd_mapping = {
        'pd1-button': 'P1',
        'pd2-button': 'P2',
        'pd3-button': 'P3',
        'pd4-button': 'P4',
        'pd5-button': 'P5'
    }
    
    pd_name = pd_mapping.get(button_id)
    if pd_name in active_pds:
        active_pds.remove(pd_name)
    else:
        active_pds.append(pd_name)
    
    # Update styles
    styles = {}
    for btn, pd in pd_mapping.items():
        if pd in active_pds:
            color = "rgba(0, 255, 0, 0.3)" if pd in ['P1', 'P3', 'P5'] else "rgba(0, 255, 255, 0.3)"
            styles[btn] = {"padding": "15px", "cursor": "pointer", "backgroundColor": color}
        else:
            styles[btn] = {"padding": "15px", "cursor": "pointer"}
    
    return (
        styles['pd1-button'],
        styles['pd2-button'],
        styles['pd3-button'],
        styles['pd4-button'],
        styles['pd5-button'],
        active_pds
    )

# Photodiode values update callback
@app.callback(
    [Output('pd1-value', 'children'),
     Output('pd2-value', 'children'),
     Output('pd3-value', 'children'),
     Output('pd4-value', 'children'),
     Output('pd5-value', 'children')],
    [Input('photodiodes-interval', 'n_intervals')],
    [State('current-page', 'data')]
)
def update_photodiode_values(n, current_page):
    # Only update if we're on the photodiodes page
    if current_page != 'photodiodes':
        raise PreventUpdate
    
    # Get latest data
    latest_data = get_latest_photodiode(os.path.join(DATASET_BASE_DIR, 'Photodiode_data'))
    
    if not latest_data:
        return "--", "--", "--", "--", "--"
    
    # Format values with 2 decimal places
    p1_val = f"{latest_data.get('P1', 0):.2f}" if latest_data.get('P1') is not None else "--"
    p2_val = f"{latest_data.get('P2', 0):.2f}" if latest_data.get('P2') is not None else "--"
    p3_val = f"{latest_data.get('P3', 0):.2f}" if latest_data.get('P3') is not None else "--"
    p4_val = f"{latest_data.get('P4', 0):.2f}" if latest_data.get('P4') is not None else "--"
    p5_val = f"{latest_data.get('P5', 0):.2f}" if latest_data.get('P5') is not None else "--"
    
    return p1_val, p2_val, p3_val, p4_val, p5_val

# Photodiode graph update callback
@app.callback(
    Output('photodiode-graph', 'figure'),
    [Input('photodiodes-interval', 'n_intervals'),
     Input('active-photodiodes', 'data')],
    [State('current-page', 'data')]
)
def update_photodiode_graph(n, active_pds, current_page):
    # Only update if we're on the photodiodes page
    if current_page != 'photodiodes':
        raise PreventUpdate
    
    # Get the data
    plot_data = get_photodiode_plot_data(os.path.join(DATASET_BASE_DIR, 'Photodiode_data'), MAX_POINTS)
    
    # Create figure
    fig = go.Figure()
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.05)",
        margin=dict(l=40, r=20, t=10, b=30),
        xaxis=dict(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.1)",
            title="Time Points",
            tickmode='array',
            tickvals=plot_data['time_points'][::5],
            ticktext=plot_data['time_fmt'][::5] if len(plot_data['time_fmt']) > 0 else []
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.1)",
            title="Value"
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        ),
    )
    
    # Add traces for active photodiodes
    colors = {
        'P1': '#9eff00',
        'P2': '#00ffff',
        'P3': '#ff9900',
        'P4': '#ff00ff',
        'P5': '#ffffff'
    }
    
    for pd in active_pds:
        if pd in plot_data and len(plot_data[pd]) > 0:
            fig.add_trace(go.Scatter(
                x=plot_data['time_points'],
                y=plot_data[pd],
                mode='lines',
                name=pd,
                line=dict(color=colors.get(pd, '#ffffff'), width=2)
            ))
    
    return fig

# Data download callback
@app.callback(
    Output('download-data', 'data'),
    [Input('download-button', 'n_clicks')],
    [State('data-type-selector', 'value'),
     State('start-date-picker', 'date'),
     State('end-date-picker', 'date')]
)
def download_data(n_clicks, data_type, start_date, end_date):
    if n_clicks is None:
        raise PreventUpdate
    
    try:
        # Convert string dates to datetime objects
        start_date = datetime.strptime(start_date.split('T')[0], "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date.split('T')[0], "%Y-%m-%d").date()
        
        # Get data from the specified range
        data = read_data_by_range(data_type, start_date, end_date)
        
        if not data:
            return dict(
                content=f"No data found for {data_type} from {start_date} to {end_date}",
                filename=f"{data_type}_{start_date}_to_{end_date}.txt",
                type="text/plain"
            )
        
        # Create a CSV string
        if data:
            csv_buffer = io.StringIO()
            csv_writer = csv.DictWriter(csv_buffer, fieldnames=data[0].keys())
            csv_writer.writeheader()
            csv_writer.writerows(data)
            
            filename = f"{data_type}_{start_date}_to_{end_date}.csv"
            
            return dict(
                content=csv_buffer.getvalue(),
                filename=filename,
                type="text/csv"
            )
    
    except Exception as e:
        print(f"Error in download_data: {e}")
        return dict(
            content=f"Error: {str(e)}",
            filename="error.txt",
            type="text/plain"
        )

# --- RUN THE APP ---
if __name__ == '__main__':
    app.run(host='172.16.26.53', port=8050, debug=True)
