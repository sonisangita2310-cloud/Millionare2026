"""
Pytest configuration file for proper module imports
"""

import sys
import os

# Add parent directory to path so src modules can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
