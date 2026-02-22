import os
import subprocess

def install_package(working_directory: str, package_name: str):
    """Installs a Python package using uv."""
    abs_working_directory = os.path.abspath(working_directory)
    
    try:
        # Split by space in case the agent tries to install multiple packages at once
        packages = package_name.strip().split()
        # Use uv package manager which is extremely fast
        command = ["uv", "add"] + packages
        
        # Run the command and capture the output so the AI can verify success or read errors
        output = subprocess.run(
            command, 
            cwd=abs_working_directory,
            capture_output=True,
            text=True,
            check=False
        )
        
        if output.returncode == 0:
            return f"Successfully installed: {package_name}\nSTDOUT: {output.stdout}"
        else:
            return f"Failed to install: {package_name}\nSTDERR: {output.stderr}"
            
    except Exception as e:
        return f"Error executing uv add: {e}"