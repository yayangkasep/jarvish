import json


class WebSearchTool:
    def __init__(self):
        self.ToolName = "WebSearch"
        self.Schema = {
            "name": self.ToolName,
            "description": "Searches the web for up-to-date factual data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "Query": {
                        "type": "string",
                        "description": "The search query to execute.",
                    }
                },
                "required": ["Query"],
            },
        }

    def Execute(self, args):
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except:
                args = {"Query": args}

        Query = args.get("Query", args.get("query"))
        if not Query:
            return "Error: Query is required."

        print(f"[{self.ToolName}] Searching web for: {Query}")
        try:
            import requests

            url = "http://localhost:8081/search"
            headers = {"X-Forwarded-For": "127.0.0.1"}  # Bypass limiter if needed
            params = {"q": Query, "format": "json"}
            res = requests.get(url, params=params, headers=headers, timeout=15)
            res.raise_for_status()
            data = res.json()

            results = data.get("results", [])

            if not results:
                return "No results found."

            # Formatting output
            output = f"Web Search Results for '{Query}':\n\n"
            for i, r in enumerate(results[:5]):
                output += f"{i + 1}. {r.get('title', '')}\n"
                output += f"URL: {r.get('url', '')}\n"
                output += f"Snippet: {r.get('content', '')}\n\n"

            return output
        except Exception as e:
            return f"Error executing web search: {str(e)}"
