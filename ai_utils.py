# ai_utils.py
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from mistralai.models import SDKError  # <-- THE FIX

# Define exactly what we want to retry on
# SDKError catches API timeouts, rate limits, and server blips
RETRY_EXCEPTIONS = (SDKError,)

@retry(
    stop=stop_after_attempt(3), 
    wait=wait_exponential(multiplier=1, min=2, max=10), 
    retry=retry_if_exception_type(RETRY_EXCEPTIONS),
    before_sleep=lambda retry_state: print(f"[dim yellow]   ⚠️ API hiccup. Retrying (attempt {retry_state.attempt_number})...[/dim yellow]")
)
def safe_mistral_stream(client, model, messages, tools=None):
    """A bulletproof wrapper for Mistral streaming calls."""
    return client.chat.stream(
        model=model,
        messages=messages,
        tools=tools
    )

@retry(
    stop=stop_after_attempt(3), 
    wait=wait_exponential(multiplier=1, min=2, max=10), 
    retry=retry_if_exception_type(RETRY_EXCEPTIONS),
    before_sleep=lambda retry_state: print(f"[dim yellow]   ⚠️ API hiccup. Retrying (attempt {retry_state.attempt_number})...[/dim yellow]")
)
async def safe_mistral_stream_async(client, model, messages, tools=None):
    """A bulletproof wrapper for Mistral async streaming calls."""
    return await client.chat.stream_async(
        model=model,
        messages=messages,
        tools=tools
    )

@retry(
    stop=stop_after_attempt(3), 
    wait=wait_exponential(multiplier=1, min=2, max=10), 
    retry=retry_if_exception_type(RETRY_EXCEPTIONS),
    before_sleep=lambda retry_state: print(f"[dim yellow]   ⚠️ API hiccup. Retrying (attempt {retry_state.attempt_number})...[/dim yellow]")
)
async def safe_mistral_complete_async(client, model, messages, tools=None):
    """A bulletproof wrapper for Mistral async complete calls."""
    # Only pass tools if provided, to avoid Mistral API complaining about empty tools lists
    kwargs = {
        "model": model,
        "messages": messages,
    }
    if tools:
        kwargs["tools"] = tools
    return await client.chat.complete_async(**kwargs)