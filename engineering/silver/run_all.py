#!/usr/bin/env python3
import subprocess,sys
from pathlib import Path
raise SystemExit(subprocess.call([sys.executable,str(Path(__file__).with_name('verifier.py'))]))
