#!/usr/bin/env python3
"""voice_home.py: compatibility shim. The resolver lives in yapcut_home.py (2026-09-09)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from yapcut_home import radar_home, voice_dir  # noqa: F401,E402
