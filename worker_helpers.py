import asyncio
from rich.markdown import Markdown

from functions.get_files_info import get_file_info
from functions.get_file_content import get_file_content
from functions.write_file import write_file
from functions.edit_file import edit_file
from functions.create_directory import create_directory
from functions.run_python_file import run_python_file
from functions.web_search import web_search
from functions.install_package import install_package
from functions.run_linter import run_linter

def trim_memory(messages, max_chars, console):
    """Trims the memory to keep it within the context window limits."""
    # Helper to safely get the string length of a message
    def get_msg_length(msg):
        content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", "")
        # Also account for tool calls taking up space
        tool_calls = msg.get("tool_calls", []) if isinstance(msg, dict) else getattr(msg, "tool_calls", [])
        return len(str(content)) + len(str(tool_calls))

    total_length = sum(get_msg_length(m) for m in messages)

    if total_length > max_chars:
        console.print(f"\n[dim yellow] Worker memory reached {total_length} chars. Truncating older steps to protect context window...[/dim yellow]")
        
        # Always keep System Prompt [0] and Manager's Task [1]
        core_messages = messages[:2]
        core_length = sum(get_msg_length(m) for m in core_messages)
        
        tail = []
        tail_length = 0
        
        # Walk backwards through the rest of the messages
        for i in range(len(messages) - 1, 1, -1):
            msg = messages[i]
            msg_len = get_msg_length(msg)
            
            # If adding this message exceeds our budget (leaving a 2000 char safety buffer)
            if core_length + tail_length + msg_len > (max_chars - 2000):
                break
                
            tail.insert(0, msg) # Prepend to keep chronological order
            tail_length += msg_len
            
        # Clean up orphaned 'tool' messages at the start of the tail
        while len(tail) > 0:
            first_msg = tail[0]
            role = first_msg.get("role") if isinstance(first_msg, dict) else getattr(first_msg, "role", "")
            
            if role == "tool":
                tail.pop(0) # Drop the orphan
            else:
                break # We found a safe Assistant or User message
                
        messages = core_messages + tail
        console.print(f"[dim yellow] Memory optimized. Resuming with {sum(get_msg_length(m) for m in messages)} chars.[/dim yellow]")

    return messages

async def execute_tool(function_name, args, working_dir, auto_mode, console):
    """Executes a single tool and returns the result."""
    function_result = ""

    # --- Fast, Silent Tool Execution for Data Retrieval ---
    if function_name in ["get_files_info", "get_file_content", "create_directory", "web_search", "run_linter"]:
        with console.status(f"[bold cyan]Worker executing {function_name}...[/bold cyan]", spinner="dots"):
            if function_name == "get_files_info":
                function_result = await asyncio.to_thread(get_file_info, working_dir, args.get("directory", "."))
                console.print(f"[bold green]\u2713[/bold green] [dim]Checked directory tree[/dim]")
                
            elif function_name == "get_file_content":
                function_result = await asyncio.to_thread(get_file_content, working_dir, args.get("file_path"))
                console.print(f"[bold green]\u2713[/bold green] [dim]Read file: {args.get('file_path')}[/dim]")
                
            elif function_name == "create_directory":
                function_result = await asyncio.to_thread(create_directory, working_dir, args.get("directory_path"))
                console.print(f"[bold green]\u2713[/bold green] [dim]Created directory: {args.get('directory_path')}[/dim]")
                
            elif function_name == "web_search":
                function_result = await asyncio.to_thread(web_search, args.get("query"))
                console.print(f"[bold green]\u2713[/bold green] [dim]Searched web for: {args.get('query')}[/dim]")
                
            elif function_name == "run_linter":
                function_result = await asyncio.to_thread(run_linter, working_dir, args.get("file_path"))
                console.print(f"[bold green]\u2713[/bold green] [dim]Linted file: {args.get('file_path')}[/dim]")

    # --- Auto-Bypass Logic for Destructive/Execution Tools ---
    elif function_name == "write_file":
        file_path = args.get("file_path")
        content = args.get("content")
        
        approval = 'y' if auto_mode else ''
        if auto_mode:
            console.print(f"[dim yellow]\u26a1 Auto-approving write to '{file_path}'[/dim yellow]")
        else:
            console.print(f"\n[bold red] WARNING: Worker wants to WRITE/OVERWRITE '{file_path}'.[/bold red]")
            while approval.strip().lower() not in ['y', 'yes', 'n', 'no']:
                approval = await asyncio.to_thread(console.input, "[bold red]Approve full file write? (y/n) > [/bold red]")
        
        with console.status(f"[bold cyan]Writing {file_path}...[/bold cyan]", spinner="dots"):
            if approval.strip().lower() in ['y', 'yes']:
                function_result = await asyncio.to_thread(write_file, working_dir, file_path, content)
                console.print(f"[bold green]\u2713[/bold green] [dim]Wrote file: {file_path}[/dim]")
            else:
                function_result = "SYSTEM ERROR: User denied permission to write file." 

    elif function_name == "edit_file":
        file_path = args.get("file_path")
        search_str = args.get("search")
        replace_str = args.get("replace")
        
        approval = 'y' if auto_mode else ''
        if auto_mode:
            console.print(f"[dim yellow]\u26a1 Auto-approving edit to '{file_path}'[/dim yellow]")
        else:
            console.print(f"\n[bold red] WARNING: Worker wants to EDIT '{file_path}'.[/bold red]")
            while approval.strip().lower() not in ['y', 'yes', 'n', 'no']:
                approval = await asyncio.to_thread(console.input, "[bold red]Approve file edit? (y/n) > [/bold red]")
        
        with console.status(f"[bold cyan]Editing {file_path}...[/bold cyan]", spinner="dots"):
            if approval.strip().lower() in ['y', 'yes']:
                function_result = await asyncio.to_thread(edit_file, working_dir, file_path, search_str, replace_str)
                console.print(f"[bold green]\u2713[/bold green] [dim]Edited file: {file_path}[/dim]")
            else:
                function_result = "SYSTEM ERROR: User denied permission to edit file."

    elif function_name == "run_python_file":
        file_path = args.get("file_path")
        script_args = args.get("args", [])
        
        approval = 'y' if auto_mode else ''
        if auto_mode:
            console.print(f"[dim yellow]\u26a1 Auto-approving execution of '{file_path}'[/dim yellow]")
        else:
            console.print(f"\n[bold red] WARNING: Worker wants to EXECUTE '{file_path}'.[/bold red]")
            while approval.strip().lower() not in ['y', 'yes', 'n', 'no']:
                approval = await asyncio.to_thread(console.input, "[bold red]Approve execution? (y/n) > [/bold red]")
                
        with console.status(f"[bold cyan]Executing {file_path}...[/bold cyan]", spinner="dots"):
            if approval.strip().lower() in ['y', 'yes']:
                function_result = await asyncio.to_thread(run_python_file, working_dir, file_path, script_args)
                console.print(f"[bold green]\u2713[/bold green] [dim]Executed: {file_path}[/dim]")
            else:
                function_result = f"SYSTEM ERROR: User denied permission."
    
    elif function_name == "install_package":
        package_name = args.get("package_name")
        
        approval = 'y' if auto_mode else ''
        if auto_mode:
            console.print(f"[dim yellow]\u26a1 Auto-approving install of '{package_name}'[/dim yellow]")
        else:
            console.print(f"\n[bold red] WARNING: Worker wants to INSTALL PACKAGE: '{package_name}'.[/bold red]")
            while approval.strip().lower() not in ['y', 'yes', 'n', 'no']:
                approval = await asyncio.to_thread(console.input, "[bold red]Approve installation? (y/n) > [/bold red]")
        
        with console.status(f"[bold cyan]Installing {package_name}...[/bold cyan]", spinner="dots"):
            if approval.strip().lower() in ['y', 'yes']:
                function_result = await asyncio.to_thread(install_package, working_dir, package_name)
                console.print(f"[bold green]\u2713[/bold green] [dim]Installed: {package_name}[/dim]")
            else:
                function_result = f"SYSTEM ERROR: User denied permission."

    elif function_name == "consult_user":
        question = args.get("question_and_options", "")
        console.print("\n[bold red] WORKER IS STUCK & NEEDS YOUR INPUT:[/bold red]")
        console.print(Markdown(question))
        user_feedback = await asyncio.to_thread(console.input, "\n[bold blue]Your response (or type 'exit' to stop) > [/bold blue]")
        if user_feedback.lower() in ['exit', 'quit']:
            return "Task aborted by user during consultation."
        function_result = f"USER INSTRUCTION: {user_feedback}"

    return function_result
