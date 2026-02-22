# functions/web_search.py
from ddgs import DDGS

def web_search(query: str, max_results: int = 5):
    """Searches the web and returns a formatted string of results."""
    try:
        # Initialize the DuckDuckGo search client
        results = DDGS().text(query, max_results=max_results)
        
        if not results:
            return f"No results found for '{query}'."
        
        formatted_results = f"--- Search Results for '{query}' ---\n\n"
        
        # Loop through dictionary items returned by DuckDuckGo and format them for readability
        for i, res in enumerate(results):
            formatted_results += f"{i+1}. {res.get('title', 'No Title')}\n"
            formatted_results += f"   URL: {res.get('href', 'No URL')}\n"
            formatted_results += f"   Snippet: {res.get('body', 'No Snippet')}\n\n"
        
        return formatted_results
        
    except Exception as e:
        return f"Error performing web search: {e}"