import os
import subprocess
import sys 

def run_python_file(working_directory: str, file_path: str, args = []):
    abs_working_directory = os.path.abspath(working_directory)
    abs_file_path = os.path.abspath(os.path.join(working_directory, file_path))

    if not abs_file_path.startswith(abs_working_directory):
        return f'Error: "{file_path}" is not in the working directory.' 

    if not os.path.isfile(abs_file_path):
        return f'Error: "{file_path}" is not a valid file.'
    
    if not file_path.endswith(".py"):
         return f"Error: '{file_path}' is not a Python File."
    
    try:
        # Prepare the standard execution command (e.g. python script.py)
        final_args = [sys.executable, file_path]
        final_args.extend(args)
        
        # Run the constructed command
        output = subprocess.run(
            final_args, 
            timeout=30, # Hard timeout so infinite loops don't lock up the agent
            capture_output=True, # Capture both stdout and stderr for analysis
            text=True, # Decode bytes into string format
            cwd=abs_working_directory,
            stdin=subprocess.DEVNULL # Prevent commands from hanging indefinitely waiting for human input
        )
        
        # --- NEW: Truncation Logic ---
        # A helper function to prevent massive print statements from bloating context and crashing the AI
        def truncate(text, max_lines=50):
            if not text:
                return ""
            lines = text.splitlines()
            if len(lines) > max_lines:
                # Keep the bottom N lines, as tracebacks put the main error at the end!
                return f"... (truncated {len(lines) - max_lines} previous lines) ...\n" + "\n".join(lines[-max_lines:])
            return text

        safe_stdout = truncate(output.stdout)
        safe_stderr = truncate(output.stderr)
        # -----------------------------

        final_string =  f"""
STDOUT: {safe_stdout}
STDERR: {safe_stderr}
"""
        if output.stdout == "" and output.stderr == "":
            final_string += "No Output Produced.\n"

        if output.returncode != 0:
            final_string += f"Process exited with code {output.returncode}."

        return final_string

    # --- Catch infinite loops explicitly ---
    # Intercept timeout errors from our subprocess call so the AI knows to fix its loop/input code
    except subprocess.TimeoutExpired:
        return f"Error: Execution timed out after 30 seconds. The script might contain an infinite loop or require user input."
        
    except Exception as e:
        return f'Error executing Python File: {e}'