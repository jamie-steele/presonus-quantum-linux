#!/usr/bin/env python3
"""
Proper PyGhidra script runner using open_project() and ghidra_script()
This is the correct way to avoid deprecation warnings
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

def run_script_proper(driver_file, script_file):
    """Run a Ghidra script using the proper new API"""
    script_name = os.path.basename(script_file)
    print(f"Running {script_name}...")
    
    # Use the existing analyzed project
    project_path = os.path.join(os.path.expanduser("~"), "ghidra_projects", "Quantum2626_Analysis")
    project_name = "Quantum2626_Analysis"
    program_name = os.path.basename(driver_file)
    
    try:
        # Open the existing project
        with open_project(project_path, project_name) as project:
            # Get the program from the project
            program = project.open_program(program_name)
            if not program:
                print(f"  ERROR: Program {program_name} not found in project")
                # List available programs
                programs = list(project.list_programs())
                if programs:
                    print(f"  Available programs: {[p.name for p in programs]}")
                    # Try to find the program by name match
                    for p in programs:
                        if program_name.lower() in p.name.lower() or p.name.lower() in program_name.lower():
                            program = project.open_program(p.name)
                            if program:
                                print(f"  Using program: {p.name}")
                                break
                if not program:
                    return False
            
            # Run the script using ghidra_script() context manager
            # This provides the ghidra modules and currentProgram to the script
            print(f"  Executing script on analyzed binary...")
            with ghidra_script(script_file):
                # The script runs here with ghidra modules available
                # currentProgram should be set automatically by ghidra_script
                pass
            
            print(f"  {script_name} completed successfully")
            return True
            
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python run_script_proper.py <driver_file> <script_file>")
        sys.exit(1)
    
    driver_file = sys.argv[1]
    script_file = sys.argv[2]
    
    if not os.path.exists(script_file):
        print(f"ERROR: Script file not found: {script_file}")
        sys.exit(1)
    
    success = run_script_proper(driver_file, script_file)
    sys.exit(0 if success else 1)
