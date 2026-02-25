from ai_utils import safe_mistral_complete

def summarize_planner_history(client, model, messages_to_summarize):
    """Compresses older conversation history into a dense LLM-generated summary."""
    conversation_text = ""
    for msg in messages_to_summarize:
        raw_role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", "")
        raw_content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", "")
        raw_name = msg.get("name") if isinstance(msg, dict) else getattr(msg, "name", "")
        
        role = str(raw_role) if raw_role is not None else ""
        content = str(raw_content) if raw_content is not None else ""
        name = str(raw_name) if raw_name is not None else ""
        
        # Append tool call details so the summarizer sees what actions were taken
        tool_calls = msg.get("tool_calls", []) if isinstance(msg, dict) else getattr(msg, "tool_calls", [])
        if tool_calls:
            for tc in tool_calls:
                # Handle both dict and object formats depending on how the message was stored
                func = tc.get("function", {}) if isinstance(tc, dict) else getattr(tc, "function", None)
                func_name = func.get("name", "") if isinstance(func, dict) else getattr(func, "name", "")
                func_args = func.get("arguments", "") if isinstance(func, dict) else getattr(func, "arguments", "")
                content = content + f"\n[ACTION TAKEN: Called tool '{func_name}' with instructions: {func_args}]"

        prefix = f"{role} ({name})" if name else role
        safe_content = str(content)[:2000] + ("..." if len(str(content)) > 2000 else "")
        conversation_text += f"[{prefix.upper()}]: {safe_content}\n"

    prompt = (
        "You are the planner's memory module. Summarize the following project history. "
        "Focus strictly on: 1) What tasks have been successfully completed. 2) What decisions were made. "
        "3) The current state of the codebase. "
        "Be highly concise, technical, and accurate. Do not add fluff.\n\n"
        f"HISTORY TO SUMMARIZE:\n{conversation_text}"
    )

    response = safe_mistral_complete(
        client=client,
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content
