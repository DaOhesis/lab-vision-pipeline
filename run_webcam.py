#!/usr/bin/env python3
"""
Quick launcher for Laptop Webcam streaming into the Lab Vision Pipeline.
Usage:
    python run_webcam.py
    python run_webcam.py --fps 10
    python run_webcam.py --device-index 1
"""

import sys
import os

# Add backend directory to path
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from scripts.webcam_streamer import main

if __name__ == "__main__":
    main()
