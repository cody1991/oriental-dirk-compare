#!/usr/bin/env python3
"""Compatibility wrapper. The repeatable entry point is scripts/refresh-offers.py."""

import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).with_name("refresh-offers.py")), run_name="__main__")
