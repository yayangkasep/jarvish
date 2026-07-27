import importlib
from googleapiclient.discovery import build

auth_mod = importlib.import_module("core.google_auth")
GoogleAuthManager = auth_mod.GoogleAuthManager


class DriveTool:
    def __init__(self):
        self.ToolName = "DriveTool"
        self.auth = GoogleAuthManager()
        self.Schema = {
            "name": self.ToolName,
            "description": "Search and retrieve files from Google Drive.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["search_files", "list_recent"],
                        "description": "The action to perform.",
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query for 'search_files' (e.g. 'name contains \"proposal\"'). Refer to Google Drive search query syntax.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of files to return. Default is 10.",
                    },
                },
                "required": ["action"],
            },
        }

    def Execute(self, kwargs):
        creds = self.auth.GetCredentials()
        if not creds:
            return "Error: Could not obtain Google credentials. Please run login_google.py to authenticate."

        try:
            service = build("drive", "v3", credentials=creds)
            action = kwargs.get("action")
            max_results = kwargs.get("max_results", 10)

            if action == "search_files":
                query = kwargs.get("query", "")
                results = (
                    service.files()
                    .list(
                        q=query,
                        pageSize=max_results,
                        fields="nextPageToken, files(id, name, mimeType, webViewLink, createdTime, modifiedTime)",
                    )
                    .execute()
                )

                items = results.get("files", [])
                if not items:
                    return f"No files found for query: '{query}'"

                result_str = f"Found files for query '{query}':\n"
                for item in items:
                    result_str += f"- {item['name']} ({item.get('modifiedTime')})\n  Link: {item.get('webViewLink')}\n"
                return result_str

            elif action == "list_recent":
                results = (
                    service.files()
                    .list(
                        pageSize=max_results,
                        orderBy="modifiedTime desc",
                        fields="nextPageToken, files(id, name, mimeType, webViewLink, modifiedTime)",
                    )
                    .execute()
                )

                items = results.get("files", [])
                if not items:
                    return "No recent files found."

                result_str = "Recent Files:\n"
                for item in items:
                    result_str += f"- {item['name']} (Modified: {item.get('modifiedTime')})\n  Link: {item.get('webViewLink')}\n"
                return result_str

            else:
                return f"Unknown action: {action}"

        except Exception as e:
            return f"Error interacting with Google Drive API: {e}"
