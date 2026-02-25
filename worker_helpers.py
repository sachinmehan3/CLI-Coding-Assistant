
from rich.markdown import Markdown

from functions.get_files_info import get_file_info
from functions.get_file_content import get_file_content
from functions.write_file import write_file
from functions.delete_file import delete_file

from functions.create_directory import create_directory
from functions.run_python_file import run_python_file
from functions.web_search import web_search
from functions.install_package import install_package
from functions.run_compiler import run_compiler

def trim_memory(messages, max_chars, console):
    """Trims the worker's memory to stay within context window limits."""
    def get_msg_length(msg):
        content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", "")
        tool_calls = msg.get("tool_calls", []) if isinstance(msg, dict) else getattr(msg, "tool_calls", [])
        return len(str(content)) + len(str(tool_calls))

    total_length = sum(get_msg_length(m) for m in messages)

    if total_length > max_chars:
        console.print(f"\n[dim yellow] Memory reached {total_length} chars. Truncating older steps to protect context window...[/dim yellow]")
        
        # Always keep System Prompt [0] and Planner's Task [1]
        core_messages = messages[:2]
        core_length = sum(get_msg_length(m) for m in core_messages)
        
        tail = []
        tail_length = 0
        
        # Walk backwards, keeping as many recent messages as fit within the budget
        for i in range(len(messages) - 1, 1, -1):
            msg = messages[i]
            msg_len = get_msg_length(msg)
            
            if core_length + tail_length + msg_len > (max_chars - 2000):
                break
                
            tail.insert(0, msg)
            tail_length += msg_len
            
        # Drop orphaned 'tool' messages that lost their parent 'assistant' message
        while len(tail) > 0:
            first_msg = tail[0]
            role = first_msg.get("role") if isinstance(first_msg, dict) else getattr(first_msg, "role", "")
            
            if role == "tool":
                tail.pop(0)
            else:
                break
                
        messages = core_messages + tail
        console.print(f"[dim yellow] Memory optimized. Resuming with {sum(get_msg_length(m) for m in messages)} chars.[/dim yellow]")

    return messages

def execute_tool(function_name, args, working_dir, auto_mode, console):
    """Executes a single tool and returns the result string."""
    function_result = ""

    if function_name in ["get_files_info", "get_file_content", "create_directory", "web_search", "run_compiler"]:
        with console.status(f"[bold cyan]Executing {function_name}...[/bold cyan]", spinner="dots"):
            if function_name == "get_files_info":
                function_result = get_file_info(working_dir, args.get("directory", "."))
                console.print(f"[dim]Checked directory tree[/dim]")
                
            elif function_name == "get_file_content":
                function_result = get_file_content(working_dir, args.get("file_path"))
                console.print(f"[dim]Read file: {args.get('file_path')}[/dim]")
                
            elif function_name == "create_directory":
                function_result = create_directory(working_dir, args.get("directory_path"))
                console.print(f"[dim]Created directory: {args.get('directory_path')}[/dim]")
                
            elif function_name == "web_search":
                function_result = web_search(args.get("query"))
                console.print(f"[dim]Searched web for: {args.get('query')}[/dim]")
                
            elif function_name == "run_compiler":
                function_result = run_compiler(working_dir, args.get("file_path"))
                console.print(f"[dim]Compiled file: {args.get('file_path')}[/dim]")

    elif function_name == "write_file":
        file_path = args.get("file_path")
        content = args.get("content")
        
        approval = 'y' if auto_mode else ''
        if auto_mode:
            console.print(f"[dim yellow]Auto-approving write to '{file_path}'[/dim yellow]")
        else:
            console.print(f"\n[bold red] WARNING: Worker wants to WRITE '{file_path}'.[/bold red]")
            while approval.strip().lower() not in ['y', 'yes', 'n', 'no']:
                approval = console.input("[bold red]Approve full file write? (y/n) > [/bold red]")
        
        with console.status(f"[bold cyan]Writing {file_path}...[/bold cyan]", spinner="dots"):
            if approval.strip().lower() in ['y', 'yes']:
                function_result = write_file(working_dir, file_path, content)
                console.print(f"[dim]Wrote file: {file_path}[/dim]")
            else:
                function_result = "SYSTEM ERROR: User denied permission to write file." 

    elif function_name == "delete_file":
        file_path = args.get("file_path")
        
        approval = 'y' if auto_mode else ''
        if auto_mode:
            console.print(f"[dim yellow]Auto-approving deletion of '{file_path}'[/dim yellow]")
        else:
            console.print(f"\n[bold red] WARNING: Worker wants to DELETE '{file_path}'.[/bold red]")
            while approval.strip().lower() not in ['y', 'yes', 'n', 'no']:
                approval = console.input("[bold red]Approve file deletion? (y/n) > [/bold red]")
        
        with console.status(f"[bold cyan]Deleting {file_path}...[/bold cyan]", spinner="dots"):
            if approval.strip().lower() in ['y', 'yes']:
                function_result = delete_file(working_dir, file_path)
                console.print(f"[dim]Deleted file: {file_path}[/dim]")
            else:
                function_result = "SYSTEM ERROR: User denied permission to delete file."

    elif function_name == "run_python_file":
        file_path = args.get("file_path")
        script_args = args.get("args", [])
        
        approval = 'y' if auto_mode else ''
        if auto_mode:
            console.print(f"[dim yellow] Auto-approving execution of '{file_path}'[/dim yellow]")
        else:
            console.print(f"\n[bold red] WARNING: Worker wants to EXECUTE '{file_path}'.[/bold red]")
            while approval.strip().lower() not in ['y', 'yes', 'n', 'no']:
                approval = console.input("[bold red]Approve execution? (y/n) > [/bold red]")
                
        with console.status(f"[bold cyan]Executing {file_path}...[/bold cyan]", spinner="dots"):
            if approval.strip().lower() in ['y', 'yes']:
                function_result = run_python_file(working_dir, file_path, script_args)
                console.print(f"[dim]Executed: {file_path}[/dim]")
            else:
                function_result = f"SYSTEM ERROR: User denied permission."
    
    elif function_name == "install_package":
        package_name = args.get("package_name")
        
        approval = 'y' if auto_mode else ''
        if auto_mode:
            console.print(f"[dim yellow]Auto-approving install of '{package_name}'[/dim yellow]")
        else:
            console.print(f"\n[bold red] WARNING: Worker wants to INSTALL PACKAGE: '{package_name}'.[/bold red]")
            while approval.strip().lower() not in ['y', 'yes', 'n', 'no']:
                approval = console.input("[bold red]Approve installation? (y/n) > [/bold red]")
        
        with console.status(f"[bold cyan]Installing {package_name}...[/bold cyan]", spinner="dots"):
            if approval.strip().lower() in ['y', 'yes']:
                function_result = install_package(working_dir, package_name)
                console.print(f"[dim]Installed: {package_name}[/dim]")
            else:
                function_result = f"SYSTEM ERROR: User denied permission."

    elif function_name == "consult_user":
        question = args.get("question_and_options", "")
        console.print("\n[bold red] WORKER IS STUCK & NEEDS YOUR INPUT:[/bold red]")
        console.print(Markdown(question))
        user_feedback = console.input("\n[bold blue]Your response (or type 'exit' to stop) > [/bold blue]")
        if user_feedback.lower() in ['exit', 'quit']:
            return "Task aborted by user during consultation."
        function_result = f"USER INSTRUCTION: {user_feedback}"

    else:
        function_result = f"SYSTEM ERROR: Unknown tool '{function_name}' was called. This tool does not exist. Please use only the tools listed in your system prompt."

    return function_result
