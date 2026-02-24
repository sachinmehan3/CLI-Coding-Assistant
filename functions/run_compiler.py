import os
import py_compile

def run_compiler(working_directory: str, file_path: str):
    abs_working_directory = os.path.abspath(working_directory)
    abs_file_path = os.path.abspath(os.path.join(working_directory, file_path))

    if not abs_file_path.startswith(abs_working_directory):
        return f'Error: "{file_path}" is not in the working directory.' 

    if not os.path.isfile(abs_file_path):
        return f'Error: "{file_path}" is not a valid file.'
    
    if not file_path.endswith(".py"):
         return f"Error: '{file_path}' is not a Python File. Compilers are for Python code."

    # Basic Syntax Check (Catches missing colons, bad indents instantly)
    # This prevents the LLM from making basic python mistakes that crash scripts immediately
    try:
        py_compile.compile(abs_file_path, doraise=True)
        return f"Compiler passed perfectly for '{file_path}'. No syntax errors found."
    except py_compile.PyCompileError as e:
        return f"FATAL SYNTAX ERROR:\n{e}"
    except Exception as e:
        return f"Error executing compiler subprocess: {e}"
