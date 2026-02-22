import asyncio

# main.py
# This is the entry point for the AI Tech Lead and Developer Agency application.
import os
import argparse
from dotenv import load_dotenv
from mistralai import Mistral
from rich.console import Console
from manager import run_tech_lead

async def main():
    # --- Command Line Arguments ---
    # Parse command line arguments to allow setting the working directory
    parser = argparse.ArgumentParser(description="AI Tech Lead and Developer Agency")
    parser.add_argument("--dir", type=str, default="workspace", help="The directory the agent will work in.")
    args = parser.parse_args()
    
    working_dir = args.dir
    
    # Auto-create the workspace folder on disk if it doesn't exist
    if not os.path.exists(working_dir):
        os.makedirs(working_dir)

    # --- Setup API and Console ---
    # Load environment variables (like API keys) from the .env file
    load_dotenv()
    
    # Check if we have the Mistral API key required to run the agents
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        print("ERROR: MISTRAL_API_KEY not found in .env file.")
        return

    # Initialize the Mistral client to make LLM requests
    client = Mistral(api_key=api_key)
    # Define the specific Mistral model being used
    model = "mistral-large-latest"
    # Create a Rich console object for nice terminal output
    console = Console()
    
    # Inform the user where the agent is operating
    console.print(f"[bold green] Workspace set to: {working_dir}[/bold green]")

    # --- Boot up the Agency ---
    # Start the manager (Tech Lead) which will then coordinate the worker
    await run_tech_lead(client, model, console, working_dir)

if __name__ == "__main__":
    # Start the asynchronous event loop for the main function
    asyncio.run(main())