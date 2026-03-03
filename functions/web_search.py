# functions/web_search.py
import os
from tavily import TavilyClient

def web_search(query: str, max_results: int = 5):
    """Searches the web using Tavily and returns a formatted string of results."""
    try:
        client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))
        response = client.search(query=query, max_results=max_results)
        results = response.get("results", [])

        if not results:
            return f"No results found for '{query}'."

        formatted_results = f"--- Search Results for '{query}' ---\n\n"

        for i, res in enumerate(results):
            formatted_results += f"{i+1}. {res.get('title', 'No Title')}\n"
            formatted_results += f"   URL: {res.get('url', 'No URL')}\n"
            formatted_results += f"   Snippet: {res.get('content', 'No Snippet')}\n\n"

        return formatted_results

    except Exception as e:
        return f"Error performing web search: {e}"