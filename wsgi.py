import sys
from pathlib import Path

path = Path(__file__).resolve().parent
if str(path) not in sys.path:
    sys.path.insert(0, str(path))

from app import app as application
