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

# Import modules from fe.csv_reader
from fe.csv_reader import (
    get_latest_temp_humidity, get_temp_humidity_plot_data,
    get_latest_laser, get_laser_plot_data,
    get_latest_photodiode, get_photodiode_plot_data,
    read_data_by_range, DATASET_BASE_DIR
)

# Import the design string from fe.design
from fe.design import design_string

# Constants
REFRESH_INTERVAL_SECONDS = 10
MAX_POINTS = 50
CURRENT_DATETIME = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# --- COLOR PALETTE DEFINITION ---
COLOR_PRIMARY = "#00ADB5"  # Teal (Cool) - Used for Series 2
COLOR_SECONDARY = "#00B582" # Green (New) - Used for Series 1

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
                    html.H2("CsF1", style={"margin": "10px 0", "color": "#00ffff"}),
                ],
                style={"display": "flex", "alignItems": "center", "justifyContent": "center", "padding": "20px"}
            ),
            html.Button(
                id="sidebar-toggle",
                className="sidebar-toggle",
                children=[
                    html.Img(
                        id="toggle-icon", 
                        src="assets/left.svg", 
                        style={"width": "12px", "height": "12px", "filter": "invert(1)"}
                    )
                ]
            ),
            html.Div(
                className="nav-links",
                children=[
                    # --- 1. OVERVIEW (HOME) ---
                    html.A(
                        className="nav-link active", # Default active
                        id="home-link",
                        href="#",
                        children=[
                            html.Img(src="assets/Home.svg", alt="Home"), 
                            html.Span("Overview")
                        ]
                    ),
                    
                    # --- NEW SEPARATOR LINE ---
                    html.Hr(style={'borderColor': 'rgba(255, 255, 255, 0.1)', 'margin': '5px 15px 15px 15px'}),
                    
                    # --- 2. TEMP & HUMIDITY ---
                    html.A(
                        className="nav-link",
                        id="temp-humidity-link",
                        href="#",
                        children=[
                            html.Img(src="assets/Temperature.svg", alt="Temp"),
                            html.Span("Temperature & Humidity")
                        ]
                    ),
                    
                    # --- 3. LASERS ---
                    html.A(
                        className="nav-link",
                        id="laser-link",
                        href="#",
                        children=[
                            html.Img(src="assets/Laser.svg", alt="Laser"),
                            html.Span("Lasers")
                        ]
                    ),
                    
                    # --- 4. PHOTODIODES ---
                    html.A(
                        className="nav-link",
                        id="photodiode-link",
                        href="#",
                        children=[
                            html.Img(src="assets/Photodiode.svg", alt="PD"),
                            html.Span("Photodiodes")
                        ]
                    ),
                    
                    html.Hr(style={'borderColor': 'rgba(255, 255, 255, 0.1)', 'margin': '15px 10px'}),
                    
                    # --- 5. RETRIEVE DATA ---
                    html.A(
                        className="nav-link",
                        id="data-retrieval-link",
                        href="#",
                        children=[
                            html.Img(src="assets/Download.svg", alt="Download"),
                            html.Span("Retrieve Data")
                        ]
                    ),
                ],
                style={"marginTop": "10px"}
            ),
        ]
    )

# --- UPDATED HEADER FUNCTION ---
def create_header(title, subtitle, status_id="connection-text", show_status=True):
    """
    Create a header component with title and subtitle.
    Added 'show_status' parameter to optionally hide the connection text.
    """
    header_children = [
        html.H1(title, className="header-title"),
        html.P(subtitle, className="header-subtitle"),
    ]
    
    # Only append the status div if show_status is True
    if show_status:
        header_children.append(
            html.Div(
                id="connection-status",
                className="connection-status",
                children=[
                    html.Span(className="status-indicator status-connected"),
                    html.Span(id=status_id, children=f"Connected | Last Update: {CURRENT_DATETIME}")
                ],
                style={"textAlign": "right", "fontSize": "0.8rem"}
            )
        )

    return html.Div(
        className="dashboard-header",
        children=header_children
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

# Define the layout for each page
def temp_humidity_layout():
    """Create the Temperature & Humidity page layout."""
    return html.Div([
        create_header("Temperature & Humidity", "Real Time Fluke1620A Data"),
        
        # Current Values Section
        html.Div(
            className="row",
            style={"display": "flex", "justifyContent": "space-around", "gap": "20px"},
            children=[
                # AMBIENT SENSOR CARD
                html.Div(
                    className="col",
                    style={"flex": "1"},
                    children=[
                        html.Div(
                            className="sensor-card",
                            children=[
                                html.H3("Ambient", style={"textAlign": "center", "color": "#ffffff", "marginBottom": "20px"}),
                                
                                # Horizontal Container
                                html.Div(
                                    style={"display": "flex", "justifyContent": "space-around", "alignItems": "center"},
                                    children=[
                                        # LEFT SIDE: Temperature
                                        html.Div(
                                            style={"textAlign": "center"},
                                            children=[
                                                html.Div(
                                                    className="value-display temp-value",
                                                    id="temp1-value",
                                                    children="--.-"
                                                ),
                                                html.Div(
                                                    style={"color": "#aaaaaa", "fontSize": "0.9rem"},
                                                    children="Temperature (°C)"
                                                )
                                            ]
                                        ),
                                        
                                        # Vertical Divider Line
                                        html.Div(style={"width": "1px", "height": "50px", "backgroundColor": "rgba(255,255,255,0.1)"}),

                                        # RIGHT SIDE: Humidity
                                        html.Div(
                                            style={"textAlign": "center"},
                                            children=[
                                                html.Div(
                                                    className="value-display humidity-value",
                                                    id="humidity1-value",
                                                    children="--.-"
                                                ),
                                                html.Div(
                                                    style={"color": "#aaaaaa", "fontSize": "0.9rem"},
                                                    children="Humidity (%)"
                                                )
                                            ]
                                        )
                                    ]
                                )
                            ]
                        )
                    ]
                ),
                
                # OPTICAL BENCH SENSOR CARD
                html.Div(
                    className="col",
                    style={"flex": "1"},
                    children=[
                        html.Div(
                            className="sensor-card",
                            children=[
                                html.H3("Optical Bench", style={"textAlign": "center", "color": "#ffffff", "marginBottom": "20px"}),
                                
                                # Horizontal Container
                                html.Div(
                                    style={"display": "flex", "justifyContent": "space-around", "alignItems": "center"},
                                    children=[
                                        # LEFT SIDE: Temperature
                                        html.Div(
                                            style={"textAlign": "center"},
                                            children=[
                                                html.Div(
                                                    className="value-display temp-value",
                                                    id="temp2-value",
                                                    children="--.-"
                                                ),
                                                html.Div(
                                                    style={"color": "#aaaaaa", "fontSize": "0.9rem"},
                                                    children="Temperature (°C)"
                                                )
                                            ]
                                        ),
                                        
                                        # Vertical Divider Line
                                        html.Div(style={"width": "1px", "height": "50px", "backgroundColor": "rgba(255,255,255,0.1)"}),

                                        # RIGHT SIDE: Humidity
                                        html.Div(
                                            style={"textAlign": "center"},
                                            children=[
                                                html.Div(
                                                    className="value-display humidity-value",
                                                    id="humidity2-value",
                                                    children="--.-"
                                                ),
                                                html.Div(
                                                    style={"color": "#aaaaaa", "fontSize": "0.9rem"},
                                                    children="Humidity (%)"
                                                )
                                            ]
                                        )
                                    ]
                                )
                            ]
                        )
                    ]
                ),
            ]
        ),
        
        # Graphs Section (Selectors Removed)
        html.Div(
            style={"display": "flex", "flexWrap": "wrap"},
            children=[
                html.Div(
                    style={"flex": "1 1 50%", "minWidth": "400px"},
                    children=[
                        create_graph_card("temperature-graph", "Temperature (°C)")
                    ]
                ),
                html.Div(
                    style={"flex": "1 1 50%", "minWidth": "400px"},
                    children=[
                        create_graph_card("humidity-graph", "Humidity (%)")
                    ]
                )
            ]
        ),
        
        # Refresh interval component (hidden)
        dcc.Interval(
            id='temp-humidity-interval',
            interval=REFRESH_INTERVAL_SECONDS * 1000,
            n_intervals=0
        )
    ])

def lasers_layout():
    """Create the Lasers page layout with Integrated Instrument Clusters."""
    
    # Helper to generate the card structure to keep code clean
    def create_axis_card(axis_name, label1, id1, color1, label2, id2, color2, graph_id):
        return html.Div(
            className="integrated-axis-card",
            children=[
                # 1. Header Row
                html.Div(
                    className="axis-header",
                    children=[
                        html.H3(f"{axis_name} Axis", className="axis-title"),
                    ]
                ),
                
                # 2. Big Data Row
                html.Div(
                    className="axis-values-container",
                    children=[
                        # Metric 1
                        html.Div(
                            className="single-metric",
                            children=[
                                html.Div(label1, className="metric-label", style={"color": color1}), # Colored Label
                                html.Div(
                                    id=id1, 
                                    className="metric-value-large",
                                    style={"color": color1}, # Colored Value
                                    children="-.--"
                                )
                            ]
                        ),
                        
                        # Vertical Divider
                        html.Div(style={"width": "1px", "height": "40px", "background": "rgba(255,255,255,0.1)"}),
                        
                        # Metric 2
                        html.Div(
                            className="single-metric",
                            children=[
                                html.Div(label2, className="metric-label", style={"color": color2}), # Colored Label
                                html.Div(
                                    id=id2, 
                                    className="metric-value-large", 
                                    style={"color": color2}, # Colored Value
                                    children="-.--"
                                )
                            ]
                        )
                    ]
                ),
                
                # 3. The Graph (Integrated)
                html.Div(
                    className="integrated-graph-container",
                    children=[
                        dcc.Graph(
                            id=graph_id,
                            config={'displayModeBar': False},
                            style={"height": "250px", "width": "100%"}
                        )
                    ]
                )
            ]
        )

    # --- MAIN LAYOUT ---
    return html.Div([
        create_header("Lasers", "Real-time Laser Monitoring"),
        
        # Grid Container (2 Columns on large screens)
        html.Div(
            style={
                "display": "grid", 
                "gridTemplateColumns": "repeat(auto-fit, minmax(500px, 1fr))", # Auto-fit ensures responsiveness
                "gap": "25px",
                "padding": "0 20px"
            },
            children=[
                # X Axis Card - Using COLOR_SECONDARY (New Green)
                create_axis_card("X", "X1", "x1-value", COLOR_SECONDARY, "X2", "x2-value", COLOR_PRIMARY, "x-axis-graph"),
                
                # Y Axis Card
                create_axis_card("Y", "Y1", "y1-value", COLOR_SECONDARY, "Y2", "y2-value", COLOR_PRIMARY, "y-axis-graph"),
                
                # Z Axis Card
                create_axis_card("Z", "Z1", "z1-value", COLOR_SECONDARY, "Z2", "z2-value", COLOR_PRIMARY, "z-axis-graph"),
                
                # D Axis Card
                create_axis_card("D", "D1", "d1-value", COLOR_SECONDARY, "D2", "d2-value", COLOR_PRIMARY, "d-axis-graph"),
            ]
        ),
        
        # Keep interval hidden
        dcc.Interval(
            id='lasers-interval',
            interval=REFRESH_INTERVAL_SECONDS * 1000,
            n_intervals=0
        )
    ])

def home_layout():
    """
    The Executive Summary Page.
    Updated: Removed green dots, Standardized Header, New Date Format.
    """
    return html.Div([
        
        # 1. Standard Header (Replaces the old 'System Nominal' bar)
        create_header("System Status", "Overview of all laboratory subsystems", status_id="home-status-text"),

        # 2. Environmental Section (Tier 1)
        html.Div("Environmental Conditions", className="section-label"),
        html.Div(
            className="env-grid",
            children=[
                # Ambient Card (Dots removed)
                html.Div(
                    className="home-stat-card",
                    children=[
                        html.Div(className="card-header-row", children=[
                            html.Div("Ambient Lab", className="card-title"),
                            # Dot removed here
                        ]),
                        html.Div([
                            html.Span(id="home-temp1", className="card-value", children="--.-"),
                            html.Span(" °C", className="card-unit")
                        ]),
                        html.Div(className="sub-metric-row", children=[
                            html.Span("Humidity", className="sub-label"),
                            html.Span(id="home-hum1", className="sub-val", children="--.- %")
                        ])
                    ]
                ),
                # Optical Bench Card
                html.Div(
                    className="home-stat-card",
                    children=[
                        html.Div(className="card-header-row", children=[
                            html.Div("Optical Bench", className="card-title"),
                        ]),
                        html.Div([
                            html.Span(id="home-temp2", className="card-value", children="--.-"),
                            html.Span(" °C", className="card-unit")
                        ]),
                        html.Div(className="sub-metric-row", children=[
                            html.Span("Humidity", className="sub-label"),
                            html.Span(id="home-hum2", className="sub-val", children="--.- %")
                        ])
                    ]
                )
            ]
        ),

        # 3. Lasers Section (Tier 2)
        html.Div("Laser Position System", className="section-label"),
        html.Div(
            className="laser-grid",
            children=[
                # X Axis
                html.Div(className="home-stat-card", children=[
                    html.Div(className="card-header-row", children=[
                        html.Div("X Axis", className="card-title"),
                    ]),
                    # Using COLOR_SECONDARY (New Green)
                    html.Div(className="sub-metric-row", style={"borderTop": "none", "marginTop": "0"}, children=[
                        html.Span("X1", className="sub-label", style={"color": COLOR_SECONDARY}),
                        html.Span(id="home-x1", className="sub-val", children="-.--")
                    ]),
                    html.Div(className="sub-metric-row", children=[
                        html.Span("X2", className="sub-label", style={"color": COLOR_PRIMARY}),
                        html.Span(id="home-x2", className="sub-val", children="-.--")
                    ])
                ]),
                # Y Axis
                html.Div(className="home-stat-card", children=[
                    html.Div(className="card-header-row", children=[
                        html.Div("Y Axis", className="card-title"),
                    ]),
                    html.Div(className="sub-metric-row", style={"borderTop": "none", "marginTop": "0"}, children=[
                        html.Span("Y1", className="sub-label", style={"color": COLOR_SECONDARY}),
                        html.Span(id="home-y1", className="sub-val", children="-.--")
                    ]),
                    html.Div(className="sub-metric-row", children=[
                        html.Span("Y2", className="sub-label", style={"color": COLOR_PRIMARY}),
                        html.Span(id="home-y2", className="sub-val", children="-.--")
                    ])
                ]),
                # Z Axis
                html.Div(className="home-stat-card", children=[
                    html.Div(className="card-header-row", children=[
                        html.Div("Z Axis", className="card-title"),
                    ]),
                    html.Div(className="sub-metric-row", style={"borderTop": "none", "marginTop": "0"}, children=[
                        html.Span("Z1", className="sub-label", style={"color": COLOR_SECONDARY}),
                        html.Span(id="home-z1", className="sub-val", children="-.--")
                    ]),
                    html.Div(className="sub-metric-row", children=[
                        html.Span("Z2", className="sub-label", style={"color": COLOR_PRIMARY}),
                        html.Span(id="home-z2", className="sub-val", children="-.--")
                    ])
                ]),
                # D Axis
                html.Div(className="home-stat-card", children=[
                    html.Div(className="card-header-row", children=[
                        html.Div("D Axis", className="card-title"),
                    ]),
                    html.Div(className="sub-metric-row", style={"borderTop": "none", "marginTop": "0"}, children=[
                        html.Span("D1", className="sub-label", style={"color": COLOR_SECONDARY}),
                        html.Span(id="home-d1", className="sub-val", children="-.--")
                    ]),
                    html.Div(className="sub-metric-row", children=[
                        html.Span("D2", className="sub-label", style={"color": COLOR_PRIMARY}),
                        html.Span(id="home-d2", className="sub-val", children="-.--")
                    ])
                ])
            ]
        ),

        # 4. Photodiodes Section (Tier 3)
        html.Div("Optical Output (Photodiodes)", className="section-label"),
        html.Div(
            className="pd-home-grid",
            children=[
                html.Div(className="home-stat-card", style={"padding": "15px"}, children=[
                    html.Div("Fiber Output", className="card-title", style={"fontSize": "0.75rem", "marginBottom": "5px", "color": COLOR_SECONDARY}),
                    html.Div(id="home-p1", className="card-value", style={"fontSize": "1.4rem"}, children="--"),
                ]),
                html.Div(className="home-stat-card", style={"padding": "15px"}, children=[
                    html.Div("Grand Detection", className="card-title", style={"fontSize": "0.75rem", "marginBottom": "5px", "color": COLOR_PRIMARY}),
                    html.Div(id="home-p2", className="card-value", style={"fontSize": "1.4rem"}, children="--"),
                ]),
                html.Div(className="home-stat-card", style={"padding": "15px"}, children=[
                    html.Div("AOM 5", className="card-title", style={"fontSize": "0.75rem", "marginBottom": "5px", "color": "#ff9900"}),
                    html.Div(id="home-p3", className="card-value", style={"fontSize": "1.4rem"}, children="--"),
                ]),
                html.Div(className="home-stat-card", style={"padding": "15px"}, children=[
                    html.Div("AOM 3", className="card-title", style={"fontSize": "0.75rem", "marginBottom": "5px", "color": "#CE93D8"}),
                    html.Div(id="home-p4", className="card-value", style={"fontSize": "1.4rem"}, children="--"),
                ]),
                html.Div(className="home-stat-card", style={"padding": "15px"}, children=[
                    html.Div("AOM 2", className="card-title", style={"fontSize": "0.75rem", "marginBottom": "5px", "color": "#90CAF9"}),
                    html.Div(id="home-p5", className="card-value", style={"fontSize": "1.4rem"}, children="--"),
                ]),
            ]
        ),
        
        # Universal Interval for Home Page
        dcc.Interval(
            id='home-interval',
            interval=REFRESH_INTERVAL_SECONDS * 1000,
            n_intervals=0
        )
    ])

def photodiodes_layout():
    """Create the Photodiodes page layout."""
    return html.Div([
        create_header("Photodiodes", "Real-time Photodiode Monitoring"),
        
        # Photodiode Selection Section
        html.Div(
            # Added style margin to match the graph card below
            style={"margin": "0 20px 20px 20px"},
            children=[
                html.Div(
                    className="pd-grid-container", 
                    children=[
                        html.Div(
                            id="pd1-button",
                            className="pd-stat-button",
                            children=[
                                html.Div("Fiber Output", className="pd-label"),
                                html.Div(id="pd1-value", className="pd-value", children="--")
                            ]
                        ),
                        html.Div(
                            id="pd2-button",
                            className="pd-stat-button",
                            children=[
                                html.Div("Grand Detection", className="pd-label"),
                                html.Div(id="pd2-value", className="pd-value", children="--")
                            ]
                        ),
                        html.Div(
                            id="pd3-button",
                            className="pd-stat-button",
                            children=[
                                html.Div("AOM 5", className="pd-label"),
                                html.Div(id="pd3-value", className="pd-value", children="--")
                            ]
                        ),
                        html.Div(
                            id="pd4-button",
                            className="pd-stat-button",
                            children=[
                                html.Div("AOM 3", className="pd-label"),
                                html.Div(id="pd4-value", className="pd-value", children="--")
                            ]
                        ),
                        html.Div(
                            id="pd5-button",
                            className="pd-stat-button",
                            children=[
                                html.Div("AOM 2", className="pd-label"),
                                html.Div(id="pd5-value", className="pd-value", children="--")
                            ]
                        ),
                    ]
                )
            ]
        ),
        
        # Graph Section
        html.Div(
            className="sensor-card",
            style={"margin": "20px"},
            children=[
                html.H3("Photodiode Readings", style={"textAlign": "center", "color": "#ffffff", "marginBottom": "20px"}),
                dcc.Graph(
                    id="photodiode-graph",
                    config={'displayModeBar': False},
                    style={"height": "500px"}
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
        # HIDDEN STATUS: show_status=False
        create_header("Retrieve Data", "Download or plot historical data for analysis", show_status=False),
        
        # Main Card
        html.Div(
            className="sensor-card",
            style={"margin": "20px", "padding": "30px"},
            children=[
                
                # --- ROW 1: Data Type Selection (Horizontal) ---
                html.Div(
                    style={
                        "display": "flex", 
                        "alignItems": "center", 
                        "justifyContent": "space-between", # Pushes label left, buttons right
                        "marginBottom": "25px",
                        "flexWrap": "wrap", # responsive wrap
                        "gap": "15px"
                    },
                    children=[
                        # Label
                        html.Label("1. Data Source", className="control-label", style={"marginBottom": "0", "minWidth": "120px"}),
                        
                        # Radio Buttons (Now sits next to label)
                        dcc.RadioItems(
                            id="data-type-selector",
                            options=[
                                {'label': ' Temp & Humidity', 'value': 'Temp_Humidity_data'},
                                {'label': ' Lasers', 'value': 'Lasers_data'},
                                {'label': ' Photodiode', 'value': 'Photodiode_data'}
                            ],
                            value='Temp_Humidity_data',
                            style={"display": "flex", "gap": "20px"},
                            labelStyle={
                                "cursor": "pointer",
                                "display": "flex",
                                "alignItems": "center",
                                "fontWeight": "400",
                                "color": "#e0e0e0"
                            },
                            inputStyle={"marginRight": "8px", "accentColor": COLOR_PRIMARY},
                        ),
                    ]
                ),
                
                # Divider
                html.Hr(style={"borderColor": "rgba(255,255,255,0.05)", "margin": "0 0 25px 0"}),

                # --- ROW 2: Date Range Selection (Horizontal) ---
                html.Div(
                    style={
                        "display": "flex", 
                        "alignItems": "center", 
                        "justifyContent": "space-between",
                        "marginBottom": "30px",
                        "flexWrap": "wrap",
                        "gap": "15px"
                    },
                    children=[
                        # Label
                        html.Label("2. Time Period", className="control-label", style={"marginBottom": "0", "minWidth": "120px"}),
                        
                        # Date Controls Group
                        html.Div(
                            style={"display": "flex", "alignItems": "center", "gap": "10px", "flex": "1", "justifyContent": "flex-end"},
                            children=[
                                # Start Date
                                html.Span("From", style={"color": "#666", "fontSize": "0.9rem", "marginRight": "5px"}),
                                html.Div(
                                    style={"width": "140px"}, # Fixed width for consistency
                                    children=dcc.DatePickerSingle(
                                        id='start-date-picker',
                                        date=datetime.now().date(),
                                        display_format='YYYY-MM-DD',
                                        placeholder='Start Date',
                                        className="dark-date-picker",
                                        style={"width": "100%"}
                                    )
                                ),
                                
                                # Arrow Icon
                                html.I(className="fa fa-arrow-right", style={"color": "#444", "margin": "0 10px"}),

                                # End Date
                                html.Span("To", style={"color": "#666", "fontSize": "0.9rem", "marginRight": "5px"}),
                                html.Div(
                                    style={"width": "140px"}, # Fixed width for consistency
                                    children=dcc.DatePickerSingle(
                                        id='end-date-picker',
                                        date=datetime.now().date(),
                                        display_format='YYYY-MM-DD',
                                        placeholder='End Date',
                                        style={"width": "100%"}
                                    )
                                )
                            ]
                        )
                    ]
                ),
                
                # --- ROW 3: Action Buttons ---
                html.Div(
                    style={"display": "flex", "gap": "15px"},
                    children=[
                        html.Button(
                            id="plot-button",
                            className="retrieve-action-button btn-primary",
                            children=[html.Span("PLOT DATA", style={"position": "relative", "top": "1px"})],
                            style={"flex": "3", "padding": "12px", "borderRadius": "4px"} # Plot button takes 75% width
                        ),
                        html.Button(
                            id="download-button",
                            className="retrieve-action-button btn-secondary",
                            children=[html.I(className="fa fa-download", style={"marginRight": "8px"}), "CSV"],
                            style={"flex": "1", "padding": "12px", "borderRadius": "4px"} # Download takes 25% width
                        ),
                    ]
                ),
                dcc.Download(id="download-data")
            ]
        ),
        
        # Historical Plot Area (Unchanged)
        html.Div(
            id="historical-plot-container",
            className="graph-container",
            style={"marginTop": "20px"},
            children=[
                dcc.Graph(id="historical-data-graph", style={"height": "600px"})
            ]
        )
    ])


# Define the main layout with URL routing
app.layout = html.Div([
    # Store current page
    dcc.Store(id='current-page', data='home'),
    
    # Main components
    create_sidebar(),
    
    html.Div(
        id="main-content",
        className="main-content",
        children=[home_layout()]
    )
])

# --- CALLBACKS ---

# Sidebar toggle callback
@app.callback(
    [Output('sidebar', 'className'),
     Output('main-content', 'className'),
     Output('toggle-icon', 'src')],
    [Input('sidebar-toggle', 'n_clicks')],
    [State('sidebar', 'className')]
)
def toggle_sidebar(n_clicks, current_class):
    if n_clicks is None:
        return "sidebar", "main-content", "assets/left.svg"
    
    if current_class == "sidebar":
        return "sidebar collapsed", "main-content expanded", "assets/right.svg"
    else:
        return "sidebar", "main-content", "assets/left.svg"

# Navigation callbacks
@app.callback(
    [Output('main-content', 'children'),
     Output('current-page', 'data'),
     Output('home-link', 'className'),
     Output('temp-humidity-link', 'className'),
     Output('laser-link', 'className'),
     Output('photodiode-link', 'className'),
     Output('data-retrieval-link', 'className')],
    [Input('home-link', 'n_clicks'),
     Input('temp-humidity-link', 'n_clicks'),
     Input('laser-link', 'n_clicks'),
     Input('photodiode-link', 'n_clicks'),
     Input('data-retrieval-link', 'n_clicks')],
    [State('current-page', 'data')]
)
def navigate_pages(home_click, temp_click, laser_click, photodiode_click, data_click, current_page):
    ctx = callback_context
    
    # Default State (Home Page)
    default_return = (home_layout(), 'home', 'nav-link active', 'nav-link', 'nav-link', 'nav-link', 'nav-link')

    if not ctx.triggered:
        return default_return
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    inactive = 'nav-link'
    active = 'nav-link active'

    if button_id == 'home-link':
        return home_layout(), 'home', active, inactive, inactive, inactive, inactive
    elif button_id == 'temp-humidity-link':
        return temp_humidity_layout(), 'temp-humidity', inactive, active, inactive, inactive, inactive
    elif button_id == 'laser-link':
        return lasers_layout(), 'lasers', inactive, inactive, active, inactive, inactive
    elif button_id == 'photodiode-link':
        return photodiodes_layout(), 'photodiodes', inactive, inactive, inactive, active, inactive
    elif button_id == 'data-retrieval-link':
        return data_retrieval_layout(), 'data-retrieval', inactive, inactive, inactive, inactive, active
    
    return default_return

# Temperature & Humidity callbacks
@app.callback(
    [Output('temp1-value', 'children'),
     Output('humidity1-value', 'children'),
     Output('temp2-value', 'children'),
     Output('humidity2-value', 'children'),
     Output('temperature-graph', 'figure'),
     Output('humidity-graph', 'figure'),
     Output('connection-text', 'children')],
    [Input('temp-humidity-interval', 'n_intervals')],
    [State('current-page', 'data')]
)
def update_temp_humidity(n, current_page):
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
    
    # NEW COLORS: #FFB74D (Ambient) and #4DD0E1 (Optical Bench)
    temp_fig.add_trace(go.Scatter(
        x=plot_data['time_points'],
        y=plot_data['temp1'],
        mode='lines',
        name='Ambient',
        line=dict(color='#FFB74D', width=2)
    ))
    
    temp_fig.add_trace(go.Scatter(
        x=plot_data['time_points'],
        y=plot_data['temp2'],
        mode='lines',
        name='Optical Bench',
        line=dict(color='#4DD0E1', width=2)
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
    
    # NEW COLORS for Humidity Graph too
    hum_fig.add_trace(go.Scatter(
        x=plot_data['time_points'],
        y=plot_data['humidity1'],
        mode='lines',
        name='Ambient',
        line=dict(color='#FFB74D', width=2)
    ))
    
    hum_fig.add_trace(go.Scatter(
        x=plot_data['time_points'],
        y=plot_data['humidity2'],
        mode='lines',
        name='Optical Bench',
        line=dict(color='#4DD0E1', width=2)
    ))
    
    return temp1, hum1, temp2, hum2, temp_fig, hum_fig, connection_text


# --- UPDATED CALLBACK FOR HOME (WITH NEW COLOR) ---
@app.callback(
    [Output('home-temp1', 'children'), Output('home-hum1', 'children'),
     Output('home-temp2', 'children'), Output('home-hum2', 'children'),
     Output('home-x1', 'children'), Output('home-x2', 'children'),
     Output('home-y1', 'children'), Output('home-y2', 'children'),
     Output('home-z1', 'children'), Output('home-z2', 'children'),
     Output('home-d1', 'children'), Output('home-d2', 'children'),
     Output('home-p1', 'children'), Output('home-p2', 'children'),
     Output('home-p3', 'children'), Output('home-p4', 'children'),
     Output('home-p5', 'children'), 
     Output('home-status-text', 'children')],
    [Input('home-interval', 'n_intervals')],
    [State('current-page', 'data')]
)
def update_home_dashboard(n, current_page):
    if current_page != 'home':
        raise PreventUpdate

    # Date Format Logic
    now = datetime.now()
    date_str = now.strftime("%d %B, %Y").lstrip('0') 
    time_str = now.strftime("%H:%M:%S")
    header_status = f"{date_str} | {time_str}"

    # 1. Get Temp Data
    t_data = get_latest_temp_humidity(os.path.join(DATASET_BASE_DIR, 'Temp_Humidity_data'))
    t1 = f"{t_data['temp1']:.2f}" if t_data else "--"
    h1 = f"{t_data['humidity1']:.1f}%" if t_data else "--"
    t2 = f"{t_data['temp2']:.2f}" if t_data else "--"
    h2 = f"{t_data['humidity2']:.1f}%" if t_data else "--"

    # 2. Get Laser Data
    l_data = get_latest_laser(os.path.join(DATASET_BASE_DIR, 'Lasers_data'))
    x1 = f"{l_data['X1']:.2f}" if l_data else "--" # Changed to .2f
    x2 = f"{l_data['X2']:.2f}" if l_data else "--" # Changed to .2f
    y1 = f"{l_data['Y1']:.2f}" if l_data else "--" # Changed to .2f
    y2 = f"{l_data['Y2']:.2f}" if l_data else "--" # Changed to .2f
    z1 = f"{l_data['Z1']:.2f}" if l_data else "--" # Changed to .2f
    z2 = f"{l_data['Z2']:.2f}" if l_data else "--" # Changed to .2f
    d1 = f"{l_data['D1']:.2f}" if l_data else "--" # Changed to .2f
    d2 = f"{l_data['D2']:.2f}" if l_data else "--" # Changed to .2f

    # 3. Get Photodiode Data
    p_data = get_latest_photodiode(os.path.join(DATASET_BASE_DIR, 'Photodiode_data'))
    p1 = f"{p_data.get('P1', 0):.2f}" if p_data else "--"
    p2 = f"{p_data.get('P2', 0):.2f}" if p_data else "--"
    p3 = f"{p_data.get('P3', 0):.2f}" if p_data else "--"
    p4 = f"{p_data.get('P4', 0):.2f}" if p_data else "--"
    p5 = f"{p_data.get('P5', 0):.2f}" if p_data else "--"

    return (t1, h1, t2, h2, x1, x2, y1, y2, z1, z2, d1, d2, p1, p2, p3, p4, p5, header_status)



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
    
    # Format current values - Updated to .2f
    x1 = f"{latest_data['X1']:.2f}" if latest_data and latest_data.get('X1') is not None else "-.--"
    x2 = f"{latest_data['X2']:.2f}" if latest_data and latest_data.get('X2') is not None else "-.--"
    y1 = f"{latest_data['Y1']:.2f}" if latest_data and latest_data.get('Y1') is not None else "-.--"
    y2 = f"{latest_data['Y2']:.2f}" if latest_data and latest_data.get('Y2') is not None else "-.--"
    z1 = f"{latest_data['Z1']:.2f}" if latest_data and latest_data.get('Z1') is not None else "-.--"
    z2 = f"{latest_data['Z2']:.2f}" if latest_data and latest_data.get('Z2') is not None else "-.--"
    d1 = f"{latest_data['D1']:.2f}" if latest_data and latest_data.get('D1') is not None else "-.--"
    d2 = f"{latest_data['D2']:.2f}" if latest_data and latest_data.get('D2') is not None else "-.--"
    
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
        line=dict(color=COLOR_SECONDARY, width=2) # AMBER
    ))
    x_fig.add_trace(go.Scatter(
        x=plot_data['time_points'],
        y=plot_data['X2'],
        mode='lines',
        name='X2',
        line=dict(color=COLOR_PRIMARY, width=2) # TEAL
    ))
    
    # Create Y axis graph
    y_fig = create_base_figure("Y-Axis Laser Readings", "Position (mm)")
    y_fig.add_trace(go.Scatter(
        x=plot_data['time_points'],
        y=plot_data['Y1'],
        mode='lines',
        name='Y1',
        line=dict(color=COLOR_SECONDARY, width=2)
    ))
    y_fig.add_trace(go.Scatter(
        x=plot_data['time_points'],
        y=plot_data['Y2'],
        mode='lines',
        name='Y2',
        line=dict(color=COLOR_PRIMARY, width=2)
    ))
    
    # Create Z axis graph
    z_fig = create_base_figure("Z-Axis Laser Readings", "Position (mm)")
    z_fig.add_trace(go.Scatter(
        x=plot_data['time_points'],
        y=plot_data['Z1'],
        mode='lines',
        name='Z1',
        line=dict(color=COLOR_SECONDARY, width=2)
    ))
    z_fig.add_trace(go.Scatter(
        x=plot_data['time_points'],
        y=plot_data['Z2'],
        mode='lines',
        name='Z2',
        line=dict(color=COLOR_PRIMARY, width=2)
    ))
    
    # Create D axis graph
    d_fig = create_base_figure("D-Axis Laser Readings", "Position (mm)")
    d_fig.add_trace(go.Scatter(
        x=plot_data['time_points'],
        y=plot_data['D1'],
        mode='lines',
        name='D1',
        line=dict(color=COLOR_SECONDARY, width=2)
    ))
    d_fig.add_trace(go.Scatter(
        x=plot_data['time_points'],
        y=plot_data['D2'],
        mode='lines',
        name='D2',
        line=dict(color=COLOR_PRIMARY, width=2)
    ))
    
    return x1, x2, y1, y2, z1, z2, d1, d2, x_fig, y_fig, z_fig, d_fig

# Photodiode button callbacks
@app.callback(
    [Output('pd1-button', 'style'),
     Output('pd2-button', 'style'),
     Output('pd3-button', 'style'),
     Output('pd4-button', 'style'),
     Output('pd5-button', 'style'),
     Output('pd1-value', 'style'),
     Output('pd2-value', 'style'),
     Output('pd3-value', 'style'),
     Output('pd4-value', 'style'),
     Output('pd5-value', 'style'),
     Output('active-photodiodes', 'data')],
    [Input('pd1-button', 'n_clicks'),
     Input('pd2-button', 'n_clicks'),
     Input('pd3-button', 'n_clicks'),
     Input('pd4-button', 'n_clicks'),
     Input('pd5-button', 'n_clicks')],
    [State('active-photodiodes', 'data')]
)
def toggle_photodiodes(btn1, btn2, btn3, btn4, btn5, active_pds):
    ctx = callback_context
    
    # UPDATED COLORS for Photodiodes
    colors = {
        'P1': COLOR_SECONDARY, # Amber (Keep as is)
        'P2': COLOR_PRIMARY,   # Teal (Keep as is)
        'P3': '#ff9900',       # Orange (Keep as is)
        'P4': '#CE93D8',       # Soft Purple
        'P5': '#90CAF9'        # Pale Blue
    }
    
    # Handle clicks
    if ctx.triggered:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        # Map button IDs to Sensor Codes
        btn_map = {'pd1-button': 'P1', 'pd2-button': 'P2', 'pd3-button': 'P3', 'pd4-button': 'P4', 'pd5-button': 'P5'}
        clicked_pd = btn_map.get(button_id)
        
        if clicked_pd:
            if clicked_pd in active_pds:
                active_pds.remove(clicked_pd)
            else:
                active_pds.append(clicked_pd)
    elif not active_pds: # Default state if empty
         active_pds = ['P1', 'P2', 'P3', 'P4', 'P5']

    # Generate Styles
    btn_styles = []
    text_styles = []
    
    sensor_order = ['P1', 'P2', 'P3', 'P4', 'P5']
    
    for sensor in sensor_order:
        base_color = colors[sensor]
        
        if sensor in active_pds:
            # ACTIVE STATE: Colored Border + Glowing Text
            btn_style = {
                "border": f"1px solid {base_color}",
                "boxShadow": f"0 0 15px {base_color}20", # Subtle glow (20 is low opacity hex)
                "opacity": "1"
            }
            text_style = {"color": base_color}
        else:
            # INACTIVE STATE: Grey Border + Dimmed Text
            btn_style = {
                "border": "1px solid rgba(255,255,255,0.1)",
                "opacity": "0.5" # Make the whole button look "off"
            }
            text_style = {"color": "#666666"}
            
        btn_styles.append(btn_style)
        text_styles.append(text_style)

    return (*btn_styles, *text_styles, active_pds)

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
    if current_page != 'photodiodes':
        raise PreventUpdate
    
    plot_data = get_photodiode_plot_data(os.path.join(DATASET_BASE_DIR, 'Photodiode_data'), MAX_POINTS)
    
    fig = go.Figure()
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.05)",
        margin=dict(l=40, r=20, t=10, b=30),
        xaxis=dict(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.1)",
            title="Time"
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
    
    # UPDATED COLORS: Using new palette for P4 and P5
    colors = {
        'P1': COLOR_SECONDARY, # Amber
        'P2': COLOR_PRIMARY,   # Teal
        'P3': '#ff9900',       # Orange
        'P4': '#CE93D8',       # Soft Purple
        'P5': '#90CAF9'        # Pale Blue
    }
    
    pd_display_names = {
        'P1': 'Fiber Output',
        'P2': 'Grand Detection',
        'P3': 'AOM 5',
        'P4': 'AOM 3',
        'P5': 'AOM 2'
    }
    
    # Use 'pd_name' to avoid conflict with pandas alias 'pd'
    for pd_name in active_pds:
        # Check if the key exists and the list is not empty
        if pd_name in plot_data and plot_data[pd_name]:
            fig.add_trace(go.Scatter(
                x=plot_data['datetime'], # Plot against datetime objects
                y=plot_data[pd_name],
                mode='lines',
                name=pd_display_names.get(pd_name, pd_name),
                line=dict(color=colors.get(pd_name, '#ffffff'), width=2)
            ))
    
    return fig


# Keep date pickers in sync and prevent invalid ranges
@app.callback(
    Output('start-date-picker', 'max_date_allowed'),
    Output('end-date-picker', 'min_date_allowed'),
    Output('start-date-picker', 'date'),
    Output('end-date-picker', 'date'),
    [Input('start-date-picker', 'date'),
     Input('end-date-picker', 'date')]
)
def sync_date_pickers(start_date, end_date):
    today = datetime.now().date()

    def _normalize(value):
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            return datetime.strptime(value.split('T')[0], "%Y-%m-%d").date()
        if value:
            return value  # already a date object
        return today

    start = _normalize(start_date)
    end = _normalize(end_date)
    
    if start > end:
        end = start
    
    return end, start, start, end


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
        start_date_obj = datetime.strptime(start_date.split('T')[0], "%Y-%m-%d").date()
        end_date_obj = datetime.strptime(end_date.split('T')[0], "%Y-%m-%d").date()
        
        data = read_data_by_range(data_type, start_date_obj, end_date_obj)
        
        if not data:
            return dict(
                content=f"No data found for {data_type} from {start_date_obj} to {end_date_obj}",
                filename=f"{data_type}_{start_date_obj}_to_{end_date_obj}.txt",
                type="text/plain"
            )
        
        if data:
            csv_buffer = io.StringIO()
            csv_writer = csv.DictWriter(csv_buffer, fieldnames=data[0].keys())
            csv_writer.writeheader()
            csv_writer.writerows(data)
            
            filename = f"{data_type}_{start_date_obj}_to_{end_date_obj}.csv"
            
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

# --- RECTIFIED CALLBACK FOR HISTORICAL PLOTTING WITH VISUAL IMPROVEMENTS ---
@app.callback(
    Output('historical-data-graph', 'figure'),
    [Input('plot-button', 'n_clicks')],
    [State('data-type-selector', 'value'),
     State('start-date-picker', 'date'),
     State('end-date-picker', 'date')]
)
def update_historical_graph(n_clicks, data_type, start_date, end_date):
    if n_clicks is None:
        return go.Figure().update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(255,255,255,0.05)",
        )
    
    start_date_obj = datetime.strptime(start_date.split('T')[0], "%Y-%m-%d").date()
    end_date_obj = datetime.strptime(end_date.split('T')[0], "%Y-%m-%d").date()
    
    data = read_data_by_range(data_type, start_date_obj, end_date_obj)
    
    # --- VISUAL IMPROVEMENTS ARE HERE ---
    fig_layout = {
        "template": "plotly_dark",
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(255,255,255,0.05)",
        "margin": dict(l=50, r=50, t=90, b=50),  # Increased margins
        "legend": {
            "bgcolor": "rgba(26,26,26,0.8)",      # Semi-transparent background
            "bordercolor": "rgba(0, 255, 255, 0.5)",
            "borderwidth": 1
        },
        "title_x": 0.5,  # Center the main title
    }

    if not data:
        fig = go.Figure()
        fig.update_layout(
            **fig_layout,
            title_text=f"No Data Found for {data_type.replace('_', ' ')}",
            xaxis={"visible": False}, yaxis={"visible": False},
            annotations=[{"text": "Please select a different date range or data type.", "xref": "paper", "yref": "paper", "showarrow": False, "font": {"size": 16}}]
        )
        return fig
    
    df = pd.DataFrame(data)
    
    if 'MJD' in df.columns and pd.to_numeric(df['MJD'], errors='coerce').notna().any():
        x_axis_col = 'MJD'
        x_axis_title = "MJD (Modified Julian Date)"
        df[x_axis_col] = pd.to_numeric(df[x_axis_col], errors='coerce')
    else:
        x_axis_col = 'timestamp'
        x_axis_title = "Timestamp"
        df[x_axis_col] = pd.to_datetime(df[x_axis_col].str.replace(' IST', ''), errors='coerce')
    
    df = df.sort_values(x_axis_col).dropna(subset=[x_axis_col])

    if data_type == 'Temp_Humidity_data':
        # For this specific case, we use two separate legends for clarity
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, subplot_titles=('Temperature (°C)', 'Humidity (%)'))
        cols_to_convert = ['T1', 'T2', 'H1', 'H2']
        df[cols_to_convert] = df[cols_to_convert].apply(pd.to_numeric, errors='coerce')
        
        # Temperature Traces (legendgroup 'temp') - UPDATED COLORS
        fig.add_trace(go.Scatter(x=df[x_axis_col], y=df['T1'], name='Ambient Temp', line=dict(color='#FFB74D'), legendgroup='temp'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df[x_axis_col], y=df['T2'], name='Optical Bench Temp', line=dict(color='#4DD0E1'), legendgroup='temp'), row=1, col=1)
        
        # Humidity Traces (legendgroup 'hum') - UPDATED COLORS
        fig.add_trace(go.Scatter(x=df[x_axis_col], y=df['H1'], name='Ambient Humidity', line=dict(color='#FFB74D'), legendgroup='hum', showlegend=False), row=2, col=1)
        fig.add_trace(go.Scatter(x=df[x_axis_col], y=df['H2'], name='Optical Bench Humidity', line=dict(color='#4DD0E1'), legendgroup='hum', showlegend=False), row=2, col=1)
        
        fig.update_layout(**fig_layout, title_text=f"Temperature & Humidity from {start_date_obj} to {end_date_obj}")
        fig.update_xaxes(title_text=x_axis_title, row=2, col=1)

    elif data_type == 'Lasers_data':
        fig = make_subplots(rows=4, cols=1, shared_xaxes=True, subplot_titles=('X-Axis (mm)', 'Y-Axis (mm)', 'Z-Axis (mm)', 'D-Axis (mm)'))
        cols_to_convert = ['X1', 'X2', 'Y1', 'Y2', 'Z1', 'Z2', 'D1', 'D2']
        df[cols_to_convert] = df[cols_to_convert].apply(pd.to_numeric, errors='coerce')

        # Updated colors in historical plot too
        fig.add_trace(go.Scatter(x=df[x_axis_col], y=df['X1'], name='X1', line=dict(color=COLOR_SECONDARY)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df[x_axis_col], y=df['X2'], name='X2', line=dict(color=COLOR_PRIMARY)), row=1, col=1)
        
        fig.add_trace(go.Scatter(x=df[x_axis_col], y=df['Y1'], name='Y1', line=dict(color=COLOR_SECONDARY), showlegend=False), row=2, col=1)
        fig.add_trace(go.Scatter(x=df[x_axis_col], y=df['Y2'], name='Y2', line=dict(color=COLOR_PRIMARY), showlegend=False), row=2, col=1)
        
        fig.add_trace(go.Scatter(x=df[x_axis_col], y=df['Z1'], name='Z1', line=dict(color=COLOR_SECONDARY), showlegend=False), row=3, col=1)
        fig.add_trace(go.Scatter(x=df[x_axis_col], y=df['Z2'], name='Z2', line=dict(color=COLOR_PRIMARY), showlegend=False), row=3, col=1)
        
        fig.add_trace(go.Scatter(x=df[x_axis_col], y=df['D1'], name='D1', line=dict(color=COLOR_SECONDARY), showlegend=False), row=4, col=1)
        fig.add_trace(go.Scatter(x=df[x_axis_col], y=df['D2'], name='D2', line=dict(color=COLOR_PRIMARY), showlegend=False), row=4, col=1)
        
        fig.update_layout(**fig_layout, title_text=f"Laser Readings from {start_date_obj} to {end_date_obj}", height=800)
        fig.update_xaxes(title_text=x_axis_title, row=4, col=1)

    elif data_type == 'Photodiode_data':
        fig = go.Figure()
        cols_to_convert = ['P1', 'P2', 'P3', 'P4', 'P5']
        df[cols_to_convert] = df[cols_to_convert].apply(pd.to_numeric, errors='coerce')
        
        # UPDATED COLORS for Photodiodes (Historical)
        colors = {
            'P1': COLOR_SECONDARY, # Amber
            'P2': COLOR_PRIMARY,   # Teal
            'P3': '#ff9900',       # Orange
            'P4': '#CE93D8',       # Soft Purple
            'P5': '#90CAF9'        # Pale Blue
        }
        
        pd_display_names = {
            'P1': 'Fiber Output',
            'P2': 'Grand Detection',
            'P3': 'AOM 5',
            'P4': 'AOM 3',
            'P5': 'AOM 2'
        }

        for col in cols_to_convert:
            fig.add_trace(go.Scatter(x=df[x_axis_col], y=df[col], name=pd_display_names.get(col, col), line=dict(color=colors.get(col))))
        
        fig.update_layout(**fig_layout, 
                          title_text=f"Photodiode Readings from {start_date_obj} to {end_date_obj}", 
                          yaxis_title="Value",
                          xaxis_title=x_axis_title)
    
    else:
        fig = go.Figure()
        fig.update_layout(**fig_layout, title_text="Select a valid data type")

    return fig


# --- RUN THE APP ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)