from rich.markdown import Markdown

from functions.get_files_info import get_file_info
from functions.project_state import get_project_state
from ai_utils import safe_mistral_complete

from planner_tools import PLANNER_TOOLS
from planner_helpers import display_project_tracker, trim_planner_memory, execute_planner_tool

PLANNER_BASE_PROMPT = (
    "You are an expert, highly autonomous Planner overseeing a Worker agent. "

    "YOUR ROLE:\n"
    "You translate user requests into actionable tasks for your Worker and manage their execution until the initial request is completely resolved.\n"
    "You do not write code yourself — you delegate everything through the `delegate_to_worker` tool.\n\n"

    "UNDERSTAND YOUR TEAM:\n"
    "- The 'Worker' is a headless AI script. It CAN read/write files, create directories, run code, search the web, etc. It CANNOT interact with visual GUIs.\n"
    "- The 'User' is a human.\n\n"

    "CONTEXT: The current project file tree and project tracker are automatically injected into your system prompt before every response. You do NOT need to discover the file structure — it is already visible to you.\n\n"

    "AVAILABLE TOOLS & WHEN TO USE THEM:\n"
    "- `get_file_content`: Use to read the CONTENTS of specific existing files. The file tree is already injected, so use this only when you need to see what is inside a file before planning or delegating.\n"
    "- `update_project_plan`: Use to set or update the list of features/specifications needed to fulfill the user's request. Call this during the Planning Stage after agreeing on features with the user.\n"
    "- `delegate_to_worker`: Use to assign the ENTIRE project specification to the Worker in ONE call. The `target_milestone` parameter is just a short label for tracking — it does NOT mean you should call this tool multiple times. Always delegate everything at once.\n\n"

    "OPERATIONAL RULES:\n"
    "1. TWO-STAGE PROCESS: You operate in two distinct stages.\n"
    "   - STAGE 1 (Planning): Discuss the user's request, outline all features, architectures, and fixes. Do NOT delegate yet. Once the user agrees, use `update_project_plan` to lock in the agreed features.\n"
    "   - STAGE 2 (Delegation): Give a SINGLE, highly detailed prompt to the Worker mapping out ALL specifications at once using `delegate_to_worker`. The prompt MUST include the desired directory structure, what directories to create, and what files to create.\n"
    "2. MODIFICATIONS TO EXISTING CODE: If the user asks to modify or fix existing code, use `get_file_content` to read the relevant files BEFORE planning. When delegating to the Worker, include the current file contents and explicitly state which files to modify vs. create new.\n"
    "3. FULL AUTONOMY FOR THE WORKER: Push the worker to complete the entire specification in its own loop based on your massive prompt. Do not break it down step-by-step for the worker.\n"
    "4. NO HAND-HOLDING: Do not stop to explain every step to the user mid-execution. Your job is to get it done completely and only return control to the user when the entire project plan is 100% finished.\n"
    "5. REVIEW & FIX: If the task fails based on the worker's report, fix the prompt and re-delegate immediately.\n"
    "6. POST-DELEGATION: Once the Worker succeeds, inform the user with a clear summary of what was built/changed and ask if they want any modifications or follow-up work.\n"
)


def get_initial_planner_messages():
    """Returns the freshly initialized memory block for a brand new Planner agent."""
    return [
        {
            "role": "system",
            "content": PLANNER_BASE_PROMPT
        }
    ]

def run_planner_step(client, model, console, working_dir, user_input, planner_messages, auto_mode):
    planner_tools = PLANNER_TOOLS
    planner_messages.append({"role": "user", "content": user_input})

    # ReAct loop: the Planner chains tool calls autonomously until it produces
    # a plain text response, at which point control returns to the user.
    while True:
        try:
            MAX_PLANNER_CHARS = 40000
            planner_messages = trim_planner_memory(planner_messages, MAX_PLANNER_CHARS, console, client, model)

            # Inject live project state into the system prompt before every LLM call
            current_project_state = get_file_info(working_dir, ".")
            current_tracker_json = get_project_state(working_dir)
            planner_messages[0]["content"] = (
                f"{PLANNER_BASE_PROMPT}\n\n"
                f" CURRENT PROJECT FILES:\n{current_project_state}\n\n"
                f" CURRENT PROJECT TRACKER:\n{current_tracker_json}"
            )

            with console.status("[bold cyan]Thinking...[/bold cyan]", spinner="dots"):

                response = safe_mistral_complete(
                    client=client,
                    model=model,
                    messages=planner_messages,
                    tools=planner_tools
                )
                
                assistant_message = response.choices[0].message
                full_content = assistant_message.content if assistant_message.content else ""
                
                stitched_tools = {}
                if assistant_message.tool_calls:
                    for idx, tool_call in enumerate(assistant_message.tool_calls):
                        stitched_tools[idx] = {
                            "id": tool_call.id,
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments
                        }

            planner_msg = {
                "role": "assistant",
                "content": full_content
            }
            
            if full_content.strip():
                console.print(Markdown(full_content))
            
            parsed_tool_calls = []
            
            if stitched_tools:
                tool_calls_list = []
                for idx, tc in stitched_tools.items():
                    parsed_tool_calls.append(tc)
                    
                    # Format tool calls as Mistral's API expects in chat history
                    tool_calls_list.append({
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": tc["arguments"]
                        }
                    })
                planner_msg["tool_calls"] = tool_calls_list
                
            planner_messages.append(planner_msg)

            if parsed_tool_calls:
                for tool_call in parsed_tool_calls:
                    tc_name = tool_call["name"]
                    tc_args_string = tool_call["arguments"]
                    tc_id = tool_call["id"]
                    
                    msg_to_append = execute_planner_tool(
                        tc_name, tc_args_string, tc_id, 
                        working_dir, console, client, model, auto_mode
                    )
                    planner_messages.append(msg_to_append)
                
                continue 

            else:
                return planner_messages
                
        except Exception as e:
            import traceback
            console.print(f"[bold red]Error in Planner Loop:[/bold red] {e}")
            console.print(f"[bold red]Traceback:[/bold red]\n{traceback.format_exc()}")
            return planner_messages

