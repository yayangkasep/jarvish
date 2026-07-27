import importlib
import datetime
from googleapiclient.discovery import build

auth_mod = importlib.import_module("core.google_auth")
GoogleAuthManager = auth_mod.GoogleAuthManager


class CalendarTool:
    def __init__(self):
        self.ToolName = "CalendarTool"
        self.auth = GoogleAuthManager()
        self.Schema = {
            "name": self.ToolName,
            "description": "Manage Google Calendar. Use this to check upcoming schedules or create new events.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["list_events", "create_event"],
                        "description": "The action to perform.",
                    },
                    "time_min": {
                        "type": "string",
                        "description": "Start time for list_events (RFC3339 format, e.g. 2026-07-22T00:00:00+07:00). Default is now.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of events to return. Default is 10.",
                    },
                    "summary": {
                        "type": "string",
                        "description": "Event title (required for create_event).",
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Event start time (RFC3339 format, required for create_event).",
                    },
                    "end_time": {
                        "type": "string",
                        "description": "Event end time (RFC3339 format, required for create_event).",
                    },
                    "description": {
                        "type": "string",
                        "description": "Event description (optional).",
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
            service = build("calendar", "v3", credentials=creds)
            action = kwargs.get("action")

            if action == "list_events":
                time_min = kwargs.get(
                    "time_min", datetime.datetime.utcnow().isoformat() + "Z"
                )
                max_results = kwargs.get("max_results", 10)

                events_result = (
                    service.events()
                    .list(
                        calendarId="primary",
                        timeMin=time_min,
                        maxResults=max_results,
                        singleEvents=True,
                        orderBy="startTime",
                    )
                    .execute()
                )

                events = events_result.get("items", [])
                if not events:
                    return "No upcoming events found."

                result = "Upcoming Events:\n"
                for event in events:
                    start = event["start"].get("dateTime", event["start"].get("date"))
                    result += f"- {start}: {event.get('summary', 'No Title')}\n"
                return result

            elif action == "create_event":
                summary = kwargs.get("summary")
                start_time = kwargs.get("start_time")
                end_time = kwargs.get("end_time")
                desc = kwargs.get("description", "")

                if not summary or not start_time or not end_time:
                    return "Error: summary, start_time, and end_time are required to create an event."

                event = {
                    "summary": summary,
                    "description": desc,
                    "start": {
                        "dateTime": start_time,
                    },
                    "end": {
                        "dateTime": end_time,
                    },
                }

                event_result = (
                    service.events().insert(calendarId="primary", body=event).execute()
                )
                return (
                    f"Event created successfully! Link: {event_result.get('htmlLink')}"
                )
            else:
                return f"Unknown action: {action}"

        except Exception as e:
            return f"Error interacting with Google Calendar API: {e}"
