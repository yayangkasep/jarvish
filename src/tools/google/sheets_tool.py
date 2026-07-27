import importlib
import json
from googleapiclient.discovery import build

auth_mod = importlib.import_module("core.google_auth")
GoogleAuthManager = auth_mod.GoogleAuthManager

class SheetsTool:
    def __init__(self):
        self.ToolName = "SheetsTool"
        self.auth = GoogleAuthManager()
        self.Schema = {
            "name": self.ToolName,
            "description": "Read, update, and append data in Google Sheets.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["get_values", "update_values", "append_values", "get_sheet_names"],
                        "description": "The action to perform.",
                    },
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The ID of the spreadsheet (found in the URL).",
                    },
                    "range": {
                        "type": "string",
                        "description": "The A1 notation of the range to read or write (e.g., 'Sheet1!A1:D5'). Required for read/update/append.",
                    },
                    "values": {
                        "type": "string",
                        "description": "A JSON string representing a 2D array of values for update_values or append_values (e.g., '[[\"A\", \"B\"]]').",
                    },
                },
                "required": ["action", "spreadsheet_id"],
            },
        }

    def Execute(self, kwargs):
        creds = self.auth.GetCredentials()
        if not creds:
            return "Error: Could not obtain Google credentials."

        try:
            service = build("sheets", "v4", credentials=creds)
            sheet = service.spreadsheets()
            
            action = kwargs.get("action")
            spreadsheet_id = kwargs.get("spreadsheet_id")
            range_name = kwargs.get("range")

            if action == "get_sheet_names":
                result = sheet.get(spreadsheetId=spreadsheet_id).execute()
                sheets = result.get('sheets', '')
                sheet_names = [s.get("properties", {}).get("title", "") for s in sheets]
                return f"Sheets found: {json.dumps(sheet_names)}"

            if not range_name:
                return "Error: 'range' parameter is required for this action."

            if action == "get_values":
                result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
                values = result.get("values", [])
                if not values:
                    return "No data found."
                return f"Data from {range_name}:\n{json.dumps(values, indent=2)}"

            elif action in ["update_values", "append_values"]:
                values_str = kwargs.get("values", "[]")
                try:
                    values = json.loads(values_str)
                except json.JSONDecodeError:
                    return "Error: 'values' must be a valid JSON string representing a 2D array."
                
                body = {"values": values}
                
                if action == "update_values":
                    result = sheet.values().update(
                        spreadsheetId=spreadsheet_id,
                        range=range_name,
                        valueInputOption="USER_ENTERED",
                        body=body
                    ).execute()
                    return f"{result.get('updatedCells')} cells updated."
                
                elif action == "append_values":
                    result = sheet.values().append(
                        spreadsheetId=spreadsheet_id,
                        range=range_name,
                        valueInputOption="USER_ENTERED",
                        body=body
                    ).execute()
                    updates = result.get("updates", {})
                    return f"{updates.get('updatedCells')} cells appended in range {updates.get('updatedRange')}."

            else:
                return f"Unknown action: {action}"

        except Exception as e:
            return f"Error interacting with Google Sheets API: {e}"
