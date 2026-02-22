import os
import subprocess
import sys
import py_compile

def run_linter(working_directory: str, file_path: str):
    abs_working_directory = os.path.abspath(working_directory)
    abs_file_path = os.path.abspath(os.path.join(working_directory, file_path))

    if not abs_file_path.startswith(abs_working_directory):
        return f'Error: "{file_path}" is not in the working directory.' 

    if not os.path.isfile(abs_file_path):
        return f'Error: "{file_path}" is not a valid file.'
    
    if not file_path.endswith(".py"):
         return f"Error: '{file_path}' is not a Python File. Linters are for Python code."

    # STEP 1: Basic Syntax Check (Catches missing colons, bad indents instantly)
    # This prevents the LLM from making basic python mistakes that crash scripts immediately
    try:
        py_compile.compile(abs_file_path, doraise=True)
    except py_compile.PyCompileError as e:
        return f"❌ FATAL SYNTAX ERROR:\n{e}"

    # STEP 2: Advanced Linting with Ruff (Catches undefined variables, bad imports)
    try:
        # Run ruff as a subprocess
        final_args = [sys.executable, "-m", "ruff", "check", file_path]
        output = subprocess.run(
            final_args, 
            capture_output=True, 
            text=True, 
            cwd=abs_working_directory   
        )
        
        # If Ruff isn't installed in the environment, Python throws this specific error
        # We silently ignore this so the agent doesn't get stuck in a loop trying to "fix" ruff
        if "No module named ruff" in output.stderr:
            return f"⚠️ Basic syntax is perfectly valid! (Note: 'ruff' is not installed, so advanced variable/import checking was skipped)."
            
        if output.returncode == 0:
            return f"✅ Linter passed perfectly for '{file_path}'. No syntax or logic errors found!"
        else:
            return f"❌ Linter found logic/formatting issues in '{file_path}':\n{output.stdout}\n{output.stderr}"
            
    except Exception as e:
        return f'Error executing linter subprocess: {e}'