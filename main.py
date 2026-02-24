import os
import argparse
from dotenv import load_dotenv
from mistralai import Mistral
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

# Import agent entry points
from planner import get_initial_planner_messages, run_planner_step
from worker import run_worker_agent
from planner_helpers import display_project_tracker

def main():
    # --- Command Line Arguments ---
    parser = argparse.ArgumentParser(description="AI Tech Lead and Developer")
    parser.add_argument("--dir", type=str, default="workspace", help="The directory the agent will work in.")
    args = parser.parse_args()
    
    working_dir = args.dir
    
    # Auto-create the workspace folder on disk if it doesn't exist
    if not os.path.exists(working_dir):
        os.makedirs(working_dir)

    # --- Setup API and Console ---
    load_dotenv()
    
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        print("ERROR: MISTRAL_API_KEY not found in .env file.")
        return

    client = Mistral(api_key=api_key)
    model = "mistral-medium-latest" 
    console = Console()
    
    console.print(f"[bold green] Workspace set to: {working_dir}[/bold green]")

    # --- Agency State ---
    # mode can be "plan" (default) or "quick"
    current_mode = "plan"
    auto_mode = True
    
    # Initialize the Planner's memory since it might converse over multiple turns
    planner_messages = get_initial_planner_messages()

    console.print("[yellow]Starting the Coding Assistant Agency...[/yellow]")
    console.print("[dim]Type '/quick' to speak directly to the Coding Assistant, or '/plan' to let the Planner manage tasks.[/dim]")
    console.print("[dim]Type '/toggle_auto' to turn off automatic executions.[/dim]")

    # --- Central REPL Loop ---
    while True:
        try:
            # Change the prompt prefix based on the active mode
            if current_mode == "plan":
                prompt_text = "\n[bold blue](Plan) You > [/bold blue]"
            else:
                prompt_text = "\n[bold blue](Quick) You > [/bold blue]"

            user_input = console.input(prompt_text)
            cmd = user_input.strip().lower()
            
            # --- Global Commands ---
            if cmd in ["exit", "quit"]:
                break
                
            elif cmd == "/toggle_auto":
                auto_mode = not auto_mode
                status_text = "ON (No prompts, high speed)" if auto_mode else "OFF (Safe mode, prompts enabled)"
                console.print(f"\n[bold magenta] Auto Mode is now {status_text}[/bold magenta]")
                continue
                
            elif cmd == "/clear":
                os.system('cls' if os.name == 'nt' else 'clear')
                continue
                
            elif cmd == "/status":
                display_project_tracker(working_dir, console)
                continue
                
            # --- Mode Switching Commands ---
            elif cmd == "/plan":
                current_mode = "plan"
                console.print("\n[bold green]Switched to PLAN mode. The Planner will coordinate tasks.[/bold green]")
                continue
                
            elif cmd == "/quick":
                current_mode = "quick"
                console.print("\n[bold green]Switched to QUICK mode. Speaking directly to the Coding Assistant.[/bold green]")
                continue
            
            # Skip empty inputs
            if not cmd:
                continue

            # --- Message Routing ---
            if current_mode == "plan":
                # Route the input to the Planner's step function.
                # It returns the updated conversation trace so we persist memory across inputs.
                planner_messages = run_planner_step(
                    client, model, console, working_dir, user_input, planner_messages, auto_mode
                )
            
            elif current_mode == "quick":
                # Route the input directly to the Worker as a one-shot task.
                # The worker agent completes the task and exits its internal loop automatically.
                summary = run_worker_agent(
                    client, model, console, task_description=user_input, working_dir=working_dir, auto_mode=auto_mode
                )
                
                # Print the final summary nicely to the user
                if summary:
                    console.print("\n")
                    console.print(Panel(
                        Markdown(summary), 
                        title="[bold green]Coding Assistant Summary[/bold green]", 
                        border_style="green"
                    ))

        except Exception as e:
            from rich.markup import escape
            console.print(f"[bold red]System Error:[/bold red] {escape(str(e))}")
            break

if __name__ == "__main__":
    main()