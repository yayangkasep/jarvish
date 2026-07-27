import requests
from bs4 import BeautifulSoup
import json


class ReadWebpageTool:
    def __init__(self):
        self.ToolName = "ReadWebpage"
        self.Schema = {
            "name": self.ToolName,
            "description": "Reads and extracts the main text content from a specific webpage URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "Url": {
                        "type": "string",
                        "description": "The URL of the webpage to read.",
                    }
                },
                "required": ["Url"],
            },
        }

    def Execute(self, args):
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except:
                args = {"Url": args}

        url = args.get("Url", args.get("url"))
        if not url:
            return "Error: URL is required."

        print(f"[{self.ToolName}] Reading webpage: {url}")
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            res = requests.get(url, headers=headers, timeout=15)
            res.raise_for_status()

            soup = BeautifulSoup(res.text, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.extract()

            text = soup.get_text(separator=" ", strip=True)

            # Truncate text to avoid token limits (e.g. 15000 characters)
            if len(text) > 15000:
                text = text[:15000] + "\n...[Content truncated]..."

            return text
        except Exception as e:
            return f"Error reading webpage: {str(e)}"
