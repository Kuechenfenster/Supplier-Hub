#!/usr/bin/env python3
import subprocess, sys, os
script_dir = os.path.dirname(os.path.abspath(__file__))
init_admin = os.path.join(script_dir, "init_admin.py")
if os.path.exists(init_admin):
    subprocess.run([sys.executable, init_admin])
else:
    print("init_admin.py not found!")
