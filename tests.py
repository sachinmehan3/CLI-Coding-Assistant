# Simple testing script to verify the 'run_python_file' functionality
# from functions.get_files_info import get_file_info
# from functions.get_file_content import get_file_content
# from functions.write_file import write_file
from functions.run_python_file import run_python_file 

def main():
    # Define the working directory where the test script lives
    working_dir = "calculator"

    # Execute main.py inside the calculator folder with argument "6 + 2" and print output
    print(run_python_file(working_dir, "main.py", ["6 + 2"]))
    
# Run the test
main()