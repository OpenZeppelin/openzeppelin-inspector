import os
import sys

# Set path one directory behind so that code files can be imported directly on test files
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
