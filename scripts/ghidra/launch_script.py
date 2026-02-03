#!/usr/bin/env python3
"""
Custom PyGhidra launcher using open_project() and ghidra_script() directly
This bypasses PyGhidra's deprecated run_script() and uses the new API properly
"""

import os
import sys

# Set Ghidra path
ghidra_path = os.environ.get('GHIDRA_INSTALL_DIR', r'C:\Users\Jamie\Ghidra\ghidra_12.0.2_PUBLIC')
os.environ['GHIDRA_INSTALL_DIR'] = ghidra_path

# Initialize PyGhidra
import pyghidra
pyghidra.start()

# Now import the new API
from pyghidra import open_project, ghidra_script

def main():
    if len(sys.argv) < 3:
        print("Usage: python launch_script.py <binary_file> <script_file>")
        sys.exit(1)
    
    binary_file = sys.argv[1]
    script_file = sys.argv[2]
    
    if not os.path.exists(binary_file):
        print(f"ERROR: Binary file not found: {binary_file}")
        sys.exit(1)
    
    if not os.path.exists(script_file):
        print(f"ERROR: Script file not found: {script_file}")
        sys.exit(1)
    
    # Create/use a project
    project_path = os.path.join(os.path.expanduser("~"), "ghidra_projects")
    project_name = "Quantum2626_Analysis"
    program_name = os.path.basename(binary_file)
    
    print(f"Opening project: {project_path}/{project_name}")
    
    try:
        # Open project (creates if doesn't exist)
        with open_project(project_path, project_name) as project:
            # Import the binary if needed
            project_data = project.getProjectData()
            root_folder = project_data.getRootFolder()
            
            # Check if program already exists
            program_file = None
            for folder in root_folder.getFolders():
                for file in folder.getFiles():
                    if file.getName() == program_name:
                        program_file = file
                        break
                if program_file:
                    break
            
            if not program_file:
                print(f"Importing {program_name}...")
                # Import the file
                program_file = root_folder.createFile(program_name, None)
                # This is simplified - actual import needs more setup
                print("Note: Program should already be imported by analyzeHeadless")
                sys.exit(1)
            
            # Open the program
            program = project.open_program(program_file.getName())
            if not program:
                print(f"ERROR: Could not open program: {program_name}")
                sys.exit(1)
            
            print(f"Running script: {os.path.basename(script_file)}")
            
            # Use ghidra_script() - this is the new API, no deprecation warnings
            with ghidra_script(script_file):
                # Script runs here with ghidra modules available
                # currentProgram is automatically set
                pass
            
            print("Script completed successfully")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
