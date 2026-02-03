#!/usr/bin/env python3
"""
Proper PyGhidra script runner using open_project() and ghidra_script()
This uses the new API correctly to avoid deprecation warnings
"""

import os
import sys

# Set Ghidra path before importing pyghidra
ghidra_path = os.environ.get('GHIDRA_INSTALL_DIR', r'C:\Users\Jamie\Ghidra\ghidra_12.0.2_PUBLIC')
os.environ['GHIDRA_INSTALL_DIR'] = ghidra_path

# Initialize PyGhidra - this sets up the Java bridge
# Must be done before importing ghidra modules
import pyghidra
pyghidra.start()

# Now we can import ghidra modules
from ghidra.framework.model import ProjectLocator
from ghidra.program.model.listing import Program

# Import PyGhidra utilities
from pyghidra import open_project, ghidra_script

def run_scripts_on_project(project_path, project_name, script_files):
    """Run multiple Ghidra scripts on an analyzed project using the new API"""
    
    print(f"Opening project: {project_path}/{project_name}")
    
    # Open the project using the new API
    with open_project(project_path, project_name) as project:
        # Get the active program from the project
        # The project should have the analyzed program
        from ghidra.framework.model import DomainFolder
        
        # Find the program in the project
        project_data = project.getProjectData()
        root_folder = project_data.getRootFolder()
        
        # Look for .gpr files or program files
        program = None
        for folder in root_folder.getFolders():
            for file in folder.getFiles():
                if file.getName().endswith('.sys') or 'quantum' in file.getName().lower():
                    # Open this program
                    program = project.open_program(file.getName())
                    if program:
                        print(f"Using program: {program.name}")
                        break
            if program:
                break
        
        if not program:
            # Try to get active program
            try:
                program = project.getActiveProgram()
                if program:
                    print(f"Using active program: {program.name}")
            except:
                pass
        
        if not program:
            print("ERROR: Could not find program in project")
            print("Available files in project:")
            for folder in root_folder.getFolders():
                for file in folder.getFiles():
                    print(f"  {file.getName()}")
            return False
        
        # Run each script
        for script_file in script_files:
            if not os.path.exists(script_file):
                print(f"WARNING: Script not found: {script_file}")
                continue
            
            script_name = os.path.basename(script_file)
            print(f"\n=== Running {script_name} ===")
            
            try:
                # Use ghidra_script() context manager - this is the new API
                # It provides the ghidra modules and sets up currentProgram
                with ghidra_script(script_file):
                    # The script executes here with ghidra modules available
                    # currentProgram is automatically set by ghidra_script
                    pass
                
                print(f"SUCCESS: {script_name} completed")
                
            except Exception as e:
                print(f"ERROR running {script_name}: {e}")
                import traceback
                traceback.print_exc()
                return False
    
    return True

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python run_ghidra_scripts.py <project_path> <project_name> <script1> [script2] ...")
        sys.exit(1)
    
    project_path = sys.argv[1]
    project_name = sys.argv[2]
    script_files = sys.argv[3:]
    
    success = run_scripts_on_project(project_path, project_name, script_files)
    sys.exit(0 if success else 1)
