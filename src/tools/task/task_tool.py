import importlib
from googleapiclient.discovery import build


auth_mod = importlib.import_module("core.google_auth")
GoogleAuthManager = auth_mod.GoogleAuthManager


class TaskTool:
    def __init__(self):
        self.ToolName = "TaskTool"
        self.auth = GoogleAuthManager()
        self.Schema = {
            "name": self.ToolName,
            "description": "Manage Google Tasks. Use this to check tasks or 'to-do' lists created by the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["list_tasks", "create_task"],
                        "description": "The action to perform.",
                    },
                    "title": {
                        "type": "string",
                        "description": "Task title (required for create_task).",
                    },
                    "notes": {
                        "type": "string",
                        "description": "Task notes/description (optional).",
                    },
                    "due": {
                        "type": "string",
                        "description": "Task due date (RFC3339 format, optional).",
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
            service = build("tasks", "v1", credentials=creds)
            action = kwargs.get("action")

            # Use @default tasklist
            tasklist_id = "@default"

            if action == "list_tasks":
                results = service.tasks().list(tasklist=tasklist_id).execute()
                items = results.get("items", [])

                if not items:
                    return "No tasks found in the default list."

                result_str = "Google Tasks:\n"
                for item in items:
                    status = "[x]" if item.get("status") == "completed" else "[ ]"
                    title = item.get("title", "Untitled")
                    due = item.get("due", "")
                    if due:
                        try:
                            # Format nicely
                            due_date = due[:10]
                            due = f" (Due: {due_date})"
                        except:
                            pass
                    result_str += f"{status} {title}{due}\n"
                return result_str

            elif action == "create_task":
                title = kwargs.get("title")
                if not title:
                    return "Error: 'title' is required to create a task."

                body = {"title": title, "notes": kwargs.get("notes", "")}

                due = kwargs.get("due")
                if due:
                    body["due"] = due

                result = (
                    service.tasks().insert(tasklist=tasklist_id, body=body).execute()
                )
                return f"Task created successfully: {result.get('title')}"

            else:
                return f"Unknown action: {action}"

        except Exception as e:
            return f"Error interacting with Google Tasks API: {e}"
