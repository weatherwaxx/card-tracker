"""
WSGI entry point for PythonAnywhere hosting.
PythonAnywhere uses this file to serve the Flask app.
"""

import sys
import os

# Add the project directory to the Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

from app import app as application
