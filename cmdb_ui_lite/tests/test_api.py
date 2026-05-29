#!/usr/bin/env python3
import json
import subprocess
import time
import sys
import os

# Start backend in background
print("Starting backend...")
os.chdir("/workspace/cmdb_server_lite")
proc = subprocess.Popen([sys.executable, "main.py"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
time.sleep(3)

# Test with simple socket
print("\nTesting with built-in urllib...")
import urllib.request

try:
    # Test health
    with urllib.request.urlopen("http://localhost:8000/health", timeout=5) as r:
        print("Health:", r.read().decode())
    
    # Test models
    with urllib.request.urlopen("http://localhost:8000/api/models", timeout=5) as r:
        models = json.load(r)
        print("Models:", len(models.get('models', [])))
    
    # Test attributes for bk_switch
    with urllib.request.urlopen("http://localhost:8000/api/models/bk_switch/attributes", timeout=5) as r:
        attrs = json.load(r)
        print("Attributes:", len(attrs.get('attributes', [])))
    
    # Test instances for bk_switch
    with urllib.request.urlopen("http://localhost:8000/api/models/bk_switch/instances", timeout=5) as r:
        insts = json.load(r)
        print("Instances:", len(insts.get('instances', [])))
        
except Exception as e:
    print(f"Error: {e}")
    if proc.poll() is not None:
        print("Backend crashed!")
        print(proc.stdout.read().decode())
finally:
    # Cleanup
    proc.terminate()
