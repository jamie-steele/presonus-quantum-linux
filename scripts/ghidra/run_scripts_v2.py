#!/usr/bin/env python3
"""
Run Ghidra scripts using the new PyGhidra API (open_project + ghidra_script)
This avoids deprecation warnings
"""

import os
import sys
from pathlib import Path

# Set Ghidra path
ghidra_path = os.environ.get('GHIDRA_INSTALL_DIR', r'C:\Users\Jamie\Ghidra\ghidra_12.0.2_PUBLIC')
os.environ['GHIDRA_INSTALL_DIR'] = ghidra_path

try:
    from pyghidra import open_project, ghidra_script
except ImportError:
    print("ERROR: PyGhidra not installed. Run: pip install pyghidra")
    sys.exit(1)

def run_script_on_binary(driver_file, script_file):
    """Run a Ghidra script on an analyzed binary using the new API"""
    script_name = os.path.basename(script_file)
    print(f"Running {script_name}...")
    
    # Use the existing analyzed project
    project_path = os.path.join(os.path.expanduser("~"), "ghidra_projects", "Quantum2626_Analysis")
    project_name = "Quantum2626_Analysis"
    program_name = os.path.basename(driver_file)
    
    try:
        # Open the existing project (created by analyzeHeadless)
        with open_project(project_path, project_name) as project:
            # Get the program from the project
            program = project.open_program(program_name)
            if not program:
                print(f"  ERROR: Program {program_name} not found in project")
                print(f"  Available programs: {[p.name for p in project.list_programs()]}")
                return False
            
            # Run the script using the new API
            # ghidra_script() makes the ghidra modules available and executes the script
            print(f"  Executing script on analyzed binary...")
            with ghidra_script(script_file):
                # The script runs in this context with ghidra modules available
                # We need to set currentProgram in the script's namespace
                import __main__
                __main__.currentProgram = program
            
            print(f"  {script_name} completed successfully")
            return True
            
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python run_scripts_v2.py <driver_file> <script_file>")
        sys.exit(1)
    
    driver_file = sys.argv[1]
    script_file = sys.argv[2]
    
    if not os.path.exists(script_file):
        print(f"ERROR: Script file not found: {script_file}")
        sys.exit(1)
    
    success = run_script_on_binary(driver_file, script_file)
    sys.exit(0 if success else 1)
