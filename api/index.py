import sys
import os

# Add the phase3 directory to the Python path so absolute imports in phase3 work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "phase3")))

from phase3.api.main import app
