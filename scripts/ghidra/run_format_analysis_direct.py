#!/usr/bin/env python3
"""
Direct PyGhidra script runner for format register analysis
This bypasses command-line issues and uses PyGhidra API directly
"""

import os
import sys

# Set Ghidra path
ghidra_path = os.environ.get('GHIDRA_INSTALL_DIR', r'C:\Users\Jamie\ghidra\ghidra_12.0.2_PUBLIC')
os.environ['GHIDRA_INSTALL_DIR'] = ghidra_path

# Initialize PyGhidra
import pyghidra
pyghidra.start()

from pyghidra import open_project

def main():
    if len(sys.argv) < 3:
        print("Usage: python run_format_analysis_direct.py <binary_file> <script_file>")
        sys.exit(1)
    
    binary_file = os.path.abspath(sys.argv[1])
    script_file = os.path.abspath(sys.argv[2])
    
    if not os.path.exists(binary_file):
        print(f"ERROR: Binary file not found: {binary_file}")
        sys.exit(1)
    
    if not os.path.exists(script_file):
        print(f"ERROR: Script file not found: {script_file}")
        sys.exit(1)
    
    # Project settings
    project_path = os.path.join(os.path.expanduser("~"), "ghidra_projects")
    project_name = "Quantum2626_Analysis"
    program_name = os.path.basename(binary_file)
    
    print(f"Opening project: {project_path}/{project_name}")
    print(f"Binary: {binary_file}")
    print(f"Script: {script_file}")
    print("")
    
    try:
        # Open project and run script using ghidra_script context manager
        from pyghidra import ghidra_script
        
        with open_project(project_path, project_name) as project:
            # Use ghidra_script context manager - this is the proper way
            # It automatically handles program loading and provides currentProgram
            print("Using ghidra_script context manager...")
            
            # ghidra_script needs the script file and will handle program loading
            with ghidra_script(script_file, binary_file):
                # Script executes here with currentProgram available
                # The script file is executed in this context
                pass
            
            print("\nScript execution complete!")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
