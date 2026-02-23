import json
from rich.markdown import Markdown
from rich.panel import Panel

from functions.project_state import get_project_state, update_project_state
from functions.get_file_content import get_file_content
from memory import summarize_manager_history
from worker import run_worker_agent

def display_project_tracker(working_dir, console):
    """Displays the current state of the project tracker via a Rich Panel."""
    try:
        state_str = get_project_state(working_dir)
        current_state = json.loads(state_str)
        goal = current_state.get("project_goal", "Not set")
        status = current_state.get("status", "Not started")
        curr = current_state.get("current_milestone", "None")
        
        status_markdown = f"**Goal:** {goal}\n\n**Status:** {status.upper()} | **Current:** {curr}\n\n**Completed:**\n"
        for m in current_state.get("completed_milestones", []):
            status_markdown += f"- {m}\n"
        if not current_state.get("completed_milestones"):
            status_markdown += "- *None yet*\n"
            
        status_markdown += "\n**Pending:**\n"
        for m in current_state.get("pending_milestones", []):
            status_markdown += f"- {m}\n"
        if not current_state.get("pending_milestones"):
            status_markdown += "- *None*\n"
            
        console.print("\n")
        console.print(Panel(Markdown(status_markdown), title="[bold blue]🚀 Project Tracker[/bold blue]", border_style="blue", expand=False))
        console.print("\n")
    except Exception as e:
        console.print(f"[bold red]Could not read project tracker: {e}[/bold red]")

async def trim_manager_memory(manager_messages, max_chars, console, client, model):
    """Trims the Tech Lead's memory by summarizing older parts of the conversation."""
    def get_msg_length(msg):
        content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", "")
        tool_calls = msg.get("tool_calls", []) if isinstance(msg, dict) else getattr(msg, "tool_calls", [])
        return len(str(content)) + len(str(tool_calls))

    total_manager_length = sum(get_msg_length(m) for m in manager_messages)

    if total_manager_length > max_chars:
        console.print(f"\n[dim yellow] Tech Lead memory reached {total_manager_length} chars. Summarizing older tasks...[/dim yellow]")
        
        system_prompt = manager_messages[0]
        
        # Keep the last 8 messages so the Manager doesn't lose immediate context
        tail = manager_messages[-8:]
        
        # Ensure we don't orphan a 'tool' message from its 'assistant' call
        while len(tail) > 0:
            first_msg = tail[0]
            role = first_msg.get("role") if isinstance(first_msg, dict) else getattr(first_msg, "role", "")
            if role == "tool":
                tail.pop(0)
            else:
                break
                
        # The "middle" is everything between the system prompt and our protected tail
        middle_messages = manager_messages[1 : len(manager_messages) - len(tail)]
        
        # Generate the summary using the secondary Mistral call
        summary_text = await summarize_manager_history(client, model, middle_messages)
        
        # Package the summary as a persistent system context block
        summary_message = {
            "role": "system", 
            "content": f"PREVIOUS TASKS SUMMARY:\n{summary_text}"
        }
        
        # Rebuild the Manager's brain!
        manager_messages = [system_prompt, summary_message] + tail
    
    return manager_messages

async def execute_manager_tool(tc_name, tc_args_string, tc_id, working_dir, console, client, model, auto_mode):
    """Handles parsing and executing tools for the Manager Agent."""
    try:
        args = json.loads(tc_args_string)
    except json.JSONDecodeError:
        return {
            "role": "tool",
            "name": tc_name,
            "content": f"SYSTEM ERROR: Failed to parse tool arguments as JSON: {tc_args_string}",
            "tool_call_id": tc_id 
        }
    
    # --- PLAN UPDATING ---
    if tc_name == "update_project_plan":
        try:
            current_state = json.loads(get_project_state(working_dir))
        except Exception:
            current_state = {
                "status": "in_progress",
                "completed_milestones": [],
                "current_milestone": None
            }
        
        # Update the goal and pending milestones
        current_state["project_goal"] = args.get("project_goal", current_state.get("project_goal"))
        current_state["pending_milestones"] = args.get("milestones", [])
        if "status" not in current_state:
            current_state["status"] = "in_progress"
        if "completed_milestones" not in current_state:
            current_state["completed_milestones"] = []
        
        console.print("\n[dim cyan] Tech Lead is updating the project plan...[/dim cyan]")
        update_project_state(working_dir, current_state)
        
        # Automatically display status tracker
        display_project_tracker(working_dir, console)

        return {
            "role": "tool",
            "name": tc_name,
            "content": "Plan successfully updated. You may now proceed.",
            "tool_call_id": tc_id 
        }

    # --- DELEGATION LOGIC ---
    elif tc_name == "delegate_to_worker":
        target_milestone = args.get("target_milestone")
        task = args.get("task_description")
        
        # 1. Update state to show what is currently happening
        current_state = json.loads(get_project_state(working_dir))
        current_state["current_milestone"] = target_milestone
        update_project_state(working_dir, current_state)

        # 2. Run the Worker
        worker_report = await run_worker_agent(client, model, console, task, working_dir, auto_mode)

        # 3. DETERMINISTIC STATE UPDATE (The Worker Finished!)
        current_state = json.loads(get_project_state(working_dir))
        
        if target_milestone in current_state["pending_milestones"]:
            current_state["pending_milestones"].remove(target_milestone)
        
        if target_milestone not in current_state["completed_milestones"]:
            current_state["completed_milestones"].append(target_milestone)
            
        current_state["current_milestone"] = None
        
        # Save the truth to disk
        update_project_state(working_dir, current_state)

        return {
            "role": "tool",
            "name": "delegate_to_worker",
            "content": f"WORKER REPORT:\n{worker_report}\n\nSYSTEM: Milestone '{target_milestone}' has been automatically marked as complete in the tracker.",
            "tool_call_id": tc_id 
        }

    elif tc_name == "get_file_content":
        file_path = args.get("file_path")

        # --- Clean spinner for Tech Lead ---
        with console.status(f"[bold cyan]Tech Lead reading '{file_path}'...[/bold cyan]", spinner="dots"):
            result = get_file_content(working_dir, file_path)
            console.print(f"[bold green]✓[/bold green] [dim]Tech Lead analyzed: {file_path}[/dim]")
        
        return {
            "role": "tool",
            "name": "get_file_content",
            "content": str(result),
            "tool_call_id": tc_id 
        }
    
    return {
        "role": "tool",
        "name": tc_name,
        "content": f"SYSTEM ERROR: Unknown tool {tc_name} called by Tech Lead.",
        "tool_call_id": tc_id
    }
