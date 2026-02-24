# CLI Coding Assistant

An autonomous, multi-agent programming framework powered by **Mistral AI**. This project orchestrates a dual-agent system directly in your terminal, consisting of a **Planner** agent that analyzes requirements and delegates tasks, and a **Worker** agent that autonomously writes, tests, and refines the code.

![Python Version](https://img.shields.io/badge/python-3.x-blue.svg)
![Mistral AI](https://img.shields.io/badge/Powered%20By-Mistral%20AI-orange.svg)

---

## Demo
<!-- Add your demo video link here, e.g. YouTube or mp4 URL -->
[Watch the Demo Video](https://github.com/user-attachments/assets/8bae0486-4366-491f-98e6-e08766f5c7a2)

---

## Key Features

*   **Two-Agent Architecture**: 
    *   **Planner**: Translates your requests into actionable milestones, updates the project tracker, and orchestrates the Worker.
    *   **Worker**: A headless agent that reads/writes files, creates directories, installs packages, and executes Python code iteratively until it passes.
*   **Intelligent Project Tracking**: Maintains a persistent `project_state.json` to track completed, current, and pending milestones.
*   **Robust Autonomous Tooling**: 
    *   **Fast Package Management**: Uses `uv` to automatically install missing dependencies on the fly.
    *   **Self-Healing Code**: Automatically runs `py_compile` (for syntax checking) and standard Python execution checks before completing tasks.
    *   **Web Search Integration**: Uses `duckduckgo-search` to find up-to-date documentation when stuck.
*   **Multi-Tiered Safety Mode**: Run in interactive mode (where the AI asks permission before writing or executing code) or toggle `/auto` mode for blazing fast, hands-off execution.
*   **Beautiful Terminal UI**: Uses the `rich` library for beautiful markdown rendering in terminal.

---

## Architecture
<img width="2874" height="1720" alt="ArchiNew" src="https://github.com/user-attachments/assets/1028dfad-000b-4bc0-b4b0-f5f312a0ff36" />



---


## Project Structure

```text
coder-agent/
│
├──  main.py               # Application entry point
├──  planner.py            # The Tech Lead Agent loop and tools
├──  planner_tools.py      # Tech Lead Agent tool definitions
├──  planner_helpers.py    # Tech Lead Agent logic helpers
├──  worker.py             # The Developer Agent loop and tools
├──  worker_tools.py       # Developer Agent tool definitions
├──  worker_helpers.py     # Developer Agent logic helpers
├──  ai_utils.py           # Resilient async wrappers for Mistral API calls
├──  memory.py             # Conversation summarization logic to prevent context bloat
│
├── functions/            # Core agent capabilities (Tools)
│   ├── create_directory.py
│   ├── edit_file.py
│   ├── get_file_content.py
│   ├── get_files_info.py
│   ├── install_package.py
│   ├── project_state.py
│   ├── run_compiler.py
│   ├── run_python_file.py
│   ├── web_search.py
│   └── write_file.py
│
└── workspace/            # Default directory where the agent builds your projects
```

---

## Getting Started

### Prerequisites

1.  **Python 3.x** installed.
2.  **Mistral API Key**. Get one from [Mistral AI](https://mistral.ai/).
3.  **uv** (Optional but highly recommended for the agent's package installation tool).

### Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/yourusername/coder-agent.git
    cd coder-agent
    ```

2.  Install the required dependencies:
    ```bash
    pip install mistralai rich python-dotenv duckduckgo-search
    ```

3.  Set up your environment variables. Create a `.env` file in the root directory:
    ```env
    MISTRAL_API_KEY=your_api_key_here
    ```

---

## Usage

Start the agency by running `main.py`. You can optionally specify a target directory for the agency to work inside (defaults to `workspace`).

```bash
python main.py --dir my_new_project
```

### Slash Commands

While talking to the Assistant, you can use the following quick commands:

*   `/status`: Displays the beautiful UI card showing current project goals, completed milestones, and pending tasks.
*   `/plan`: Switches to Plan Mode. The Tech Lead (Planner) takes over to coordinate and assign tasks.
*   `/quick`: Switches to Quick Mode. Speak directly to the Developer (Worker) for one-shot tasks without milestone tracking.
*   `/toggle_auto`: Toggles Auto Mode. When ON, the worker will automatically write and execute files without asking for standard `(y/n)` confirmations.
*   `/clear`: Clears the terminal screen.


---
## Memory Management

### For the Tech Lead (Planner)
*   **Milestone-Driven Context**: The Planner doesn't need to know every line of code written. Its memory is focused on high-level planning and the current milestone.
*   **Active Summarization**: The `memory.py` module actively monitors the length of the Planner's context. When the history becomes too long, the system compresses older conversations into a dense summary, preserving key decisions and context without the bloat.
*   **State Tracking**: By relying on the persistent `project_state.json` file, the Planner maintains an accurate absolute truth of the overall goal and next steps, even after its chat history is summarized.

### For the Developer (Worker)
*   **Sliding Window Conservation**: The Worker actively tracking the character length of its coding iterations. When the context exceeds a safe limit, older steps (like early failed linting or execution attempts) are systematically truncated to protect the context window.
*   **Context & Tool Call Preservation**: During truncation, the Worker anchors the core instructions and the Planner's initial task objective. It perfectly preserves the most recent tool calls and execution results, ensuring it never loses its vital short-term memory of the exact code or error it is currently fixing.
*   **Truncation Safeguards**: Reading large files or executing scripts that dump massive amounts of logs to the terminal are automatically truncated. This prevents a single errant print statement from instantly blowing up the context window.

---

## 🛡️ License
This project is open-source and available under the MIT License.
