"""Production entry point for hosted Dash deployments.

Dash exposes the Flask server object as ``server``. Gunicorn imports this file
and serves ``app:server`` without running the development server block in
``fe/dash_app.py``.
"""

from fe.dash_app import app, server
