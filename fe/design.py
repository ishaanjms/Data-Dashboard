def design_string(): 
    return '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            /* --- GLOBAL THEME --- */
            body {
                background-color: #121212;
                background-image: linear-gradient(135deg, #121212 0%, #1a1a1a 100%);
                font-family: 'Segoe UI', 'Roboto', Helvetica, Arial, sans-serif;
                color: #e0e0e0;
                margin: 0;
            }

            /* --- SIDEBAR STYLING --- */
            .sidebar {
                background: #161616;
                border-right: 1px solid rgba(255, 255, 255, 0.05);
                box-shadow: 2px 0 10px rgba(0,0,0,0.3);
                height: 100vh;
                position: fixed;
                width: 250px;
                padding: 20px 0;
                transition: all 0.3s ease;
                z-index: 1000;
            }

            .sidebar.collapsed { width: 60px; }
            .sidebar.collapsed .nav-link span { display: none; }
            .sidebar.collapsed .sidebar-header { display: none; }
            
            .sidebar.collapsed .nav-link {
                padding: 15px;
                justify-content: center;
            }
            
            .sidebar.collapsed .nav-link i { margin: 0; font-size: 1.2rem; }

            /* --- NAVIGATION LINKS --- */
            .sidebar .nav-link {
                color: #888888;
                padding: 12px 25px;
                transition: all 0.2s ease;
                white-space: nowrap;
                overflow: hidden;
                display: flex;
                align-items: center;
                text-decoration: none;
                font-weight: 500;
                font-size: 0.95rem;
                border-left: 3px solid transparent;
            }

            .sidebar .nav-link:hover {
                color: #e0e0e0;
                background: rgba(255, 255, 255, 0.03);
            }

            .sidebar .nav-link.active {
                background: rgba(0, 173, 181, 0.1);
                color: #00ADB5;
                border-left: 3px solid #00ADB5;
            }
            
            /* --- ICON STYLING (FIXED FOR VISIBILITY) --- */
            .sidebar .nav-link img {
                width: 24px;
                height: 24px;
                margin-right: 15px;
                object-fit: contain;
                
                /* FORCE WHITE: Turns any colored/black icon into pure white */
                filter: brightness(0) invert(1);
                
                opacity: 0.7; 
                transition: all 0.2s;
            }

            .sidebar .nav-link:hover img { 
                opacity: 1; 
                /* Keep white, just max opacity */
                filter: brightness(0) invert(1);
            }
            
            /* Active State: Teal Tint */
            .sidebar .nav-link.active img {
                opacity: 1;
                /* Complex filter to turn White into Teal (#00ADB5) */
                filter: brightness(0) saturate(100%) invert(63%) sepia(60%) saturate(452%) hue-rotate(130deg) brightness(90%) contrast(93%);
            }

            /* --- HEADER --- */
            .sidebar-header h2 {
                color: #e0e0e0 !important;
                font-weight: 600;
                letter-spacing: 1px;
            }

            /* --- TOGGLE BUTTON --- */
            .sidebar-toggle {
                position: absolute;
                right: -12px;
                top: 25px;
                background: #222;
                border: 1px solid #444;
                border-radius: 50%;
                width: 24px;
                height: 24px;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                color: #aaa;
                font-size: 12px;
                transition: all 0.2s ease;
                z-index: 1001;
            }
            
            .sidebar-toggle:hover {
                background: #00ADB5;
                color: #fff;
                border-color: #00ADB5;
            }
            
            .sidebar.collapsed .sidebar-toggle i { transform: rotate(180deg); }


            /* --- MAIN CONTENT & HEADER --- */
            .main-content {
                margin-left: 250px;
                padding: 30px 50px;
                transition: all 0.3s ease;
            }
            .main-content.expanded { margin-left: 60px; }

            .dashboard-header {
                padding-bottom: 20px;
                margin-bottom: 30px;
                border-bottom: 1px solid rgba(255,255,255,0.05); 
            }

            .header-title {
                color: #ffffff;
                font-weight: 600;
                margin: 0;
                font-size: 2rem;
            }
            
            .header-subtitle {
                color: #888888;
                margin: 5px 0 0 0;
                font-weight: 400;
            }

            /* --- STANDARD CARD STYLING --- */
            .sensor-card {
                background: #1e1e1e;
                border: 1px solid #333;
                border-radius: 8px;
                padding: 25px;
                margin: 15px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.2);
                position: relative;
                z-index: 10;
            }
            
            /* --- HOME PAGE: MISSION CONTROL LAYOUT --- */
            
            /* Global Status Bar */
            .global-status-bar {
                background: #1e1e1e;
                border: 1px solid #333;
                border-left: 5px solid #00ADB5;
                border-radius: 8px;
                padding: 15px 25px;
                margin-bottom: 25px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                box-shadow: 0 4px 10px rgba(0,0,0,0.2);
            }

            .status-title {
                font-size: 1.2rem;
                font-weight: 600;
                color: #fff;
                margin: 0;
            }

            .status-summary {
                color: #888;
                font-size: 0.9rem;
            }

            /* Section Headers */
            .section-label {
                font-size: 0.9rem;
                text-transform: uppercase;
                letter-spacing: 1.5px;
                color: #666;
                margin-bottom: 15px;
                border-bottom: 1px solid #333;
                padding-bottom: 5px;
                display: flex;
                align-items: center;
            }

            /* Grids */
            .env-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin-bottom: 30px;
            }

            .laser-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }

            .pd-home-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 15px;
                margin-bottom: 30px;
            }

            /* Home Stat Card */
            .home-stat-card {
                background: #1e1e1e;
                border: 1px solid #333;
                border-radius: 8px;
                padding: 20px;
                position: relative;
                transition: transform 0.2s;
            }

            .home-stat-card:hover {
                transform: translateY(-2px);
                border-color: #555;
            }

            .card-header-row {
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                margin-bottom: 10px;
            }

            .card-title {
                font-size: 0.9rem;
                color: #aaa;
                font-weight: 500;
            }

            .card-value {
                font-size: 1.8rem;
                font-weight: 700;
                color: #e0e0e0;
                line-height: 1.1;
            }

            .card-unit {
                font-size: 0.8rem;
                color: #666;
                margin-left: 5px;
            }

            /* Status Dot */
            .status-dot-large {
                height: 12px;
                width: 12px;
                background-color: #00ADB5;
                border-radius: 50%;
                box-shadow: 0 0 8px rgba(0, 173, 181, 0.4);
            }

            .status-dot-large.warning {
                background-color: #FF8A65;
                box-shadow: 0 0 8px rgba(255, 138, 101, 0.4);
            }

            /* Sub-values */
            .sub-metric-row {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-top: 15px;
                padding-top: 10px;
                border-top: 1px solid rgba(255,255,255,0.05);
            }

            .sub-label { font-size: 0.8rem; color: #666; }
            .sub-val { font-size: 1.1rem; font-weight: 600; color: #ccc; }
            
            
            /* --- LASER PAGE: INTEGRATED MASTER CARDS --- */
            .integrated-axis-card {
                background: #1e1e1e;
                border: 1px solid #333;
                border-radius: 12px;
                padding: 0; 
                margin-bottom: 20px;
                overflow: hidden;
                box-shadow: 0 4px 10px rgba(0,0,0,0.3);
                display: flex;
                flex-direction: column;
                height: 100%;
            }

            .axis-header {
                background: rgba(255, 255, 255, 0.03);
                padding: 15px 20px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);
                display: flex;
                justify-content: space-between;
                align-items: center;
            }

            .axis-title {
                color: #e0e0e0;
                font-size: 1.1rem;
                font-weight: 600;
                letter-spacing: 0.5px;
                margin: 0;
            }

            .axis-values-container {
                padding: 20px;
                display: flex;
                justify-content: space-around;
                align-items: center;
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            }

            .single-metric {
                text-align: center;
            }

            .metric-label {
                font-size: 0.85rem;
                color: #888;
                text-transform: uppercase;
                margin-bottom: 5px;
                font-weight: 500;
            }

            /* Values use standard font now */
            .metric-value-large {
                font-size: 2.2rem;
                font-weight: 700;
            }

            .integrated-graph-container {
                padding: 10px;
                background: rgba(0,0,0,0.2);
                flex-grow: 1;
            }
            
            /* --- TYPOGRAPHY & VALUES --- */
            .sensor-card h3, .control-label, .pd-label {
                color: #aaaaaa !important; 
                font-weight: 500;
                letter-spacing: 0.5px;
            }

            .value-display {
                font-size: 2.2rem;
                font-weight: 600;
                text-align: center;
                margin: 8px 0;
            }

            .temp-value { color: #FF8A65; }
            .humidity-value { color: #4DD0E1; }
            .no-data-value { color: #666; font-style: italic; }

            /* Status Indicators */
            .status-indicator {
                width: 10px;
                height: 10px;
                border-radius: 50%;
                display: inline-block;
                margin-right: 8px;
            }
            .status-connected { background-color: #00ADB5; }
            .status-error { background-color: #E53935; }
            
            .connection-status { color: #666; font-family: monospace; }

            /* --- GRAPH CONTAINER --- */
            .graph-container {
                background: #1e1e1e;
                border-radius: 8px;
                padding: 20px;
                margin: 20px;
                border: 1px solid #333;
                position: relative;
                z-index: 1; 
            }

            /* --- PHOTODIODE PAGE: GRID --- */
            .pd-grid-container {
                display: flex;
                gap: 15px;
                width: 100%;
                margin-bottom: 20px;
            }

            .pd-stat-button {
                flex: 1;
                background: #252525;
                border: 1px solid #333;
                border-radius: 6px;
                padding: 15px 10px;
                cursor: pointer;
                transition: all 0.2s ease;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
            }

            .pd-stat-button:hover {
                background: #2a2a2a;
                border-color: #555;
            }

            .pd-label {
                font-size: 0.75rem;
                color: #888;
                margin-bottom: 5px;
                text-transform: uppercase;
            }

            .pd-value {
                font-size: 1.2rem;
                font-weight: 600;
                color: #ddd;
            }

            /* --- CUSTOM RADIO BUTTONS (Big & Teal) --- */
            #data-type-selector label {
                display: inline-flex !important;
                align-items: center;
                margin-right: 25px;
                cursor: pointer;
                font-weight: 400;
                color: #e0e0e0;
                padding: 8px 12px;
                border-radius: 8px;
                transition: background 0.2s;
            }
            
            #data-type-selector label:hover {
                background: rgba(255, 255, 255, 0.05);
            }
            
            #data-type-selector input {
                appearance: none;
                -webkit-appearance: none;
                width: 20px;
                height: 20px;
                border-radius: 50%;
                border: 2px solid #666; 
                background-color: transparent;
                margin-right: 12px;
                cursor: pointer;
                position: relative;
                transition: all 0.2s ease;
            }
            
            #data-type-selector input:hover {
                border-color: #00ADB5;
            }
            
            #data-type-selector input:checked {
                border-color: #00ADB5;
                background-color: #00ADB5;
                box-shadow: inset 0 0 0 4px #1e1e1e;
            }

            /* --- DATE PICKER REPAIR --- */
            .SingleDatePickerInput {
                background-color: #252525 !important;
                border: 1px solid #444 !important;
                border-radius: 4px;
                display: flex;
            }

            .DateInput, .DateInput_1 {
                background-color: transparent !important;
                width: 100%;
            }

            .DateInput_input, .DateInput_input_1 {
                background-color: transparent !important;
                color: #e0e0e0 !important;
                font-weight: 500;
                font-size: 0.95rem;
                border-bottom: none !important;
                text-align: center;
                padding: 10px 5px;
                line-height: normal;
            }

            .DateInput_input::placeholder {
                color: #666;
            }
            
            .SingleDatePicker_picker { 
                z-index: 10000 !important; 
                position: absolute !important; 
                margin-top: 5px; 
            }
            
            .DateInput_fang { 
                z-index: 10000 !important; 
            }

            /* --- BUTTONS --- */
            .retrieve-action-button {
                border-radius: 4px;
                font-size: 0.9rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.2s;
                padding: 12px 24px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }

            .btn-primary {
                background-color: #00ADB5;
                color: #ffffff !important;
                border: none;
            }

            .btn-primary:hover {
                background-color: #00989f;
                transform: translateY(-1px);
            }

            .btn-secondary {
                background: transparent;
                color: #e0e0e0 !important;
                border: 1px solid #555;
            }

            .btn-secondary:hover {
                border-color: #00ADB5;
                color: #00ADB5 !important;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''