import importlib

memory_manager_mod = importlib.import_module("core.memory-manager")
MemoryManager = memory_manager_mod.MemoryManager


class MemoryTool:
    def __init__(self):
        self.ToolName = "MemoryTool"
        self.memory_manager = MemoryManager()
        self.Schema = {
            "name": self.ToolName,
            "description": "Store, retrieve, or delete long-term memory facts about the user. Use this to remember important details (e.g. preferences, schedules) across sessions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["save", "delete", "list"],
                        "description": "The action to perform: 'save' to add a fact, 'delete' to remove a fact, 'list' to view all facts.",
                    },
                    "fact": {
                        "type": "string",
                        "description": "The fact to save (only required if action is 'save').",
                    },
                    "fact_index": {
                        "type": "integer",
                        "description": "The index of the fact to delete (only required if action is 'delete'). Get the index by using the 'list' action first.",
                    },
                    "user_id": {
                        "type": "string",
                        "description": "The unique ID of the user. In Telegram, this is the Chat ID.",
                    },
                },
                "required": ["action", "user_id"],
            },
        }

    def Execute(self, kwargs):
        action = kwargs.get("action")
        user_id = str(kwargs.get("user_id"))

        if not user_id or user_id == "None":
            return "Error: user_id is required."

        if action == "save":
            fact = kwargs.get("fact")
            if not fact:
                return "Error: 'fact' is required for save action."
            self.memory_manager.AddFact(user_id, fact)
            return f"Successfully saved fact: {fact}"

        elif action == "delete":
            idx = kwargs.get("fact_index")
            if idx is None:
                return "Error: 'fact_index' is required for delete action."
            deleted = self.memory_manager.DeleteFact(user_id, idx)
            if deleted:
                return f"Successfully deleted fact: {deleted}"
            else:
                return f"Error: Fact at index {idx} not found."

        elif action == "list":
            facts = self.memory_manager.GetFacts(user_id)
            if not facts:
                return "No facts remembered yet."
            result = "Saved Facts:\n"
            for i, f in enumerate(facts):
                result += f"[{i}] {f}\n"
            return result

        else:
            return f"Error: Unknown action '{action}'"
