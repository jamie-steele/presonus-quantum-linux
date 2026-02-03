#!/usr/bin/env python3
"""
PyGhidra script runner using the new API (open_project + ghidra_script)
This avoids the deprecation warnings
"""

import os
import sys

# Set Ghidra path
ghidra_path = os.environ.get('GHIDRA_INSTALL_DIR', r'C:\Users\Jamie\Ghidra\ghidra_12.0.2_PUBLIC')
os.environ['GHIDRA_INSTALL_DIR'] = ghidra_path

try:
    from pyghidra import open_project, ghidra_script
except ImportError:
    print("ERROR: PyGhidra not installed. Run: pip install pyghidra")
    sys.exit(1)

def run_script_headless(driver_file, script_file):
    """Run a Ghidra script using the new PyGhidra API"""
    print(f"Running {os.path.basename(script_file)} on {os.path.basename(driver_file)}...")
    
    # Create a temporary project
    project_path = os.path.join(os.path.expanduser("~"), "ghidra_projects", "Quantum2626_Temp")
    project_name = "temp_analysis"
    
    try:
        # Open project (creates if doesn't exist)
        with open_project(project_path, project_name) as project:
            # Import the binary if not already imported
            program = project.open_program(driver_file)
            if not program:
                print(f"  Importing {driver_file}...")
                program = project.import_file(driver_file)
            
            # Run the script
            print(f"  Running script: {os.path.basename(script_file)}")
            with ghidra_script(script_file, program=program):
                # Script runs automatically in this context
                pass
            
            print(f"  Script completed successfully")
            return True
            
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python run_analysis_v2.py <driver_file> <script_file>")
        sys.exit(1)
    
    driver_file = sys.argv[1]
    script_file = sys.argv[2]
    
    if not os.path.exists(driver_file):
        print(f"ERROR: Driver file not found: {driver_file}")
        sys.exit(1)
    
    if not os.path.exists(script_file):
        print(f"ERROR: Script file not found: {script_file}")
        sys.exit(1)
    
    success = run_script_headless(driver_file, script_file)
    sys.exit(0 if success else 1)
