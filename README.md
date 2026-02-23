# CLI Coding Assistant

An autonomous, multi-agent programming framework powered by **Mistral AI**. This project creates a virtual software development agency right in your terminal, consisting of a **Tech Lead** (Manager) who plans and delegates, and a **Developer** (Worker) who writes, tests, and refines the code.

![Python Version](https://img.shields.io/badge/python-3.x-blue.svg)
![Mistral AI](https://img.shields.io/badge/Powered%20By-Mistral%20AI-orange.svg)

---

## Demo
<!-- Add your demo video link here, e.g. YouTube or mp4 URL -->
[Watch the Demo Video](https://github.com/user-attachments/assets/bb34bc14-28a1-4f5d-969c-51513674e6fe)





---

## Key Features

*   **Two-Agent Architecture**: 
    *   **Manager (Tech Lead)**: Translates your requests into actionable milestones, updates the project tracker, and orchestrates the Worker.
    *   **Worker (Developer)**: A headless agent that reads/writes files, creates directories, installs packages, runs linters, and executes Python code iteratively until it passes.
*   **Intelligent Project Tracking**: Maintains a persistent `project_state.json` to track completed, current, and pending milestones.
*   **Robust Autonomous Tooling**: 
    *   **Fast Package Management**: Uses `uv` to automatically install missing dependencies on the fly.
    *   **Self-Healing Code**: Automatically runs `ruff` (for linting) and standard Python syntax checks before execution.
    *   **Web Search Integration**: Uses `duckduckgo-search` to find up-to-date documentation when stuck.
*   **Multi-Tiered Safety Mode**: Run in interactive mode (where the AI asks permission before writing or executing code) or toggle `/auto` mode for blazing fast, hands-off execution.
*   **Beautiful Terminal UI**: Uses the `rich` library for live-streaming markdown, smooth spinners, and color-coded status tracking.

---

## Architecture

<img width="1907" height="1335" alt="Untitled-2026-02-22-1548" src="https://github.com/user-attachments/assets/921f6ff7-f8d1-430a-81f7-aae47ee25981" />

---


## Project Structure

```text
coder-agent/
│
├──  main.py               # Application entry point
├──  manager.py            # The Tech Lead Agent loop and tools
├──  worker.py             # The Developer Agent loop and tools
├──  memory.py             # Conversation summarization logic to prevent context bloat
├──  config.py             # Global configurations (e.g., character limits)
│
├── functions/            # Core agent capabilities (Tools)
│   ├── create_directory.py
│   ├── get_file_content.py
│   ├── get_files_info.py
│   ├── install_package.py
│   ├── project_state.py
│   ├── run_linter.py
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
4.  **ruff** (Optional but recommended for advanced linting).

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

While talking to the Tech Lead, you can use the following quick commands:

*   `/status` or `/plan`: Displays the beautiful UI card showing current project goals, completed milestones, and pending tasks.
*   `/auto`: Toggles Auto Mode. When ON, the worker will automatically write and execute files without asking for standard `(y/n)` confirmations.
*   `/clear`: Clears the terminal screen.

---

## How It Works (The Loop)

1.  **You** chat with the **Tech Lead**, describing what you want built.
2.  The **Tech Lead** explores the codebase, creates a step-by-step milestone plan, and saves it.
3.  The **Tech Lead** delegates the first milestone to the **Developer**.
4.  The **Developer** loops continuously:
    *   Scanning directories.
    *   Writing code.
    *   Linting and fixing syntax errors.
    *   Executing code and fixing tracebacks.
    *   Installing packages if hit with `ModuleNotFoundError`.
5.  Once the feature works perfectly, the **Developer** reports back to the **Tech Lead**.
6.  The **Tech Lead** marks the milestone as complete and immediately delegates the next one, repeating until the project is finished!

---

### For the Tech Lead (Manager)
*   **Milestone-Driven Context**: The Manager doesn't need to know every line of code written. Its memory is focused on high-level planning and the current milestone.
*   **Active Summarization**: The `memory.py` module actively monitors the length of the Manager's context. When the history becomes too long, the system compresses older conversations into a dense summary, preserving key decisions and context without the bloat.
*   **State Tracking**: By relying on the persistent `project_state.json` file, the Manager maintains an accurate absolute truth of the overall goal and next steps, even after its chat history is summarized.

### For the Developer (Worker)
*   **Sliding Window Conservation**: The Worker actively tracking the character length of its coding iterations. When the context exceeds a safe limit, older steps (like early failed linting or execution attempts) are systematically truncated to protect the context window.
*   **Context & Tool Call Preservation**: During truncation, the Worker anchors the core instructions and the Manager's initial task objective. It perfectly preserves the most recent tool calls and execution results, ensuring it never loses its vital short-term memory of the exact code or error it is currently fixing.
*   **Truncation Safeguards**: Reading large files or executing scripts that dump massive amounts of logs to the terminal are automatically truncated. This prevents a single errant print statement from instantly blowing up the context window.

---

## 🛡️ License
This project is open-source and available under the MIT License.
