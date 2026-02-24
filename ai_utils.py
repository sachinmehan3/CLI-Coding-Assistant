# ai_utils.py
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from mistralai.models import SDKError  # <-- THE FIX

# Define exactly what we want to retry on
# SDKError catches API timeouts, rate limits, and server blips
RETRY_EXCEPTIONS = (SDKError,)

@retry(
    stop=stop_after_attempt(5), 
    wait=wait_exponential(multiplier=2, min=5, max=60), 
    retry=retry_if_exception_type(RETRY_EXCEPTIONS),
    before_sleep=lambda retry_state: print(f"[dim yellow] API rate limit or timeout. Retrying in {retry_state.next_action.sleep}s (attempt {retry_state.attempt_number}/5)...[/dim yellow]")
)
def safe_mistral_complete(client, model, messages, tools=None):
    """A bulletproof wrapper for Mistral synchronous complete calls."""
    # Only pass tools if provided, to avoid Mistral API complaining about empty tools lists
    kwargs = {
        "model": model,
        "messages": messages,
    }
    if tools:
        kwargs["tools"] = tools
    return client.chat.complete(**kwargs)