"""
Direct runner for VIGH-02 AI AGENT.
Run with: python run_vigh.py
"""

import sys
import os

# Ensure package is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vigh_agent.cli import main

if __name__ == "__main__":
    main()
