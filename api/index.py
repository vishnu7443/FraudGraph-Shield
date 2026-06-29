import sys
import os

# Add phase3 directory to Python path so absolute imports work
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
phase3_dir = os.path.join(root_dir, 'phase3')

if phase3_dir not in sys.path:
    sys.path.insert(0, phase3_dir)

# Import the FastAPI app instance from phase3 so Vercel can find it
from api.main import app
