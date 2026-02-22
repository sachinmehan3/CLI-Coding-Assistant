from ai_utils import safe_mistral_complete_async

async def summarize_manager_history(client, model, messages_to_summarize):
    """
    Uses Mistral to compress older conversation history into a dense summary.
    This prevents the AI context window from getting too large and crashing.
    """
    conversation_text = ""
    # Loop through each message to build a readable string format of the history
    for msg in messages_to_summarize:
        # Extract the role (e.g., user, assistant, tool) safely
        raw_role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", "")
        # Extract the actual text content safely
        raw_content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", "")
        # Extract the name of the tool if applicable
        raw_name = msg.get("name") if isinstance(msg, dict) else getattr(msg, "name", "")
        
        role = str(raw_role) if raw_role is not None else ""
        content = str(raw_content) if raw_content is not None else ""
        name = str(raw_name) if raw_name is not None else ""
        
        # --- Extract tool calls so the summarizer can see what actions were taken ---
        tool_calls = msg.get("tool_calls", []) if isinstance(msg, dict) else getattr(msg, "tool_calls", [])
        if tool_calls:
            # Loop through tools the AI decided to use in this message
            for tc in tool_calls:
                # Handle both dictionary formats and raw object formats depending on how it was saved
                func = tc.get("function", {}) if isinstance(tc, dict) else getattr(tc, "function", None)
                func_name = func.get("name", "") if isinstance(func, dict) else getattr(func, "name", "")
                func_args = func.get("arguments", "") if isinstance(func, dict) else getattr(func, "arguments", "")
                
                # Append a readable note about what tool was called and with what arguments
                content = content + f"\\n[ACTION TAKEN: Called tool '{func_name}' with instructions: {func_args}]"
        # --------------------------------------------------------------

        # Format the prefix to include the name if one exists (e.g., TOOL (read_file))
        prefix = f"{role} ({name})" if name else role
        
        # Truncate content to 2000 characters to keep things somewhat bounded
        safe_content = str(content)[:2000] + ("..." if len(str(content)) > 2000 else "")
        # Add this message's formatted text to the full history string
        conversation_text += f"[{prefix.upper()}]: {safe_content}\\n"

    # Define instructions for the Mistral model on how to summarize this text
    prompt = (
        "You are a project manager's memory module. Summarize the following project history. "
        "Focus strictly on: 1) What tasks have been successfully completed. 2) What decisions were made. "
        "3) The current state of the codebase. "
        "Be highly concise, technical, and accurate. Do not add fluff.\\n\\n"
        f"HISTORY TO SUMMARIZE:\\n{conversation_text}"
    )

    # Make the API call to Mistral to get the actual summary text
    response = await safe_mistral_complete_async(
        client=client,
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )
    # Return the generated summary content
    return response.choices[0].message.content
