import os

class WriteFileTool:
    def __init__(self):
        self.ToolName = "WriteFile"
        self.Schema = {
            "name": "WriteFile",
            "description": "Writes content to a file in the scratchpad directory. Overwrites if file exists.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "The name of the file (e.g., data.csv)"},
                    "content": {"type": "string", "description": "The content to write to the file"}
                },
                "required": ["filename", "content"]
            }
        }
        self.base_dir = os.path.expanduser("~/.jarvish/scratchpad")
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)

    def Execute(self, arguments):
        filename = arguments.get("filename")
        content = arguments.get("content")
        path = os.path.join(self.base_dir, os.path.basename(filename))
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully wrote to {filename}."
        except Exception as e:
            return f"Error writing to file: {e}"

class AppendFileTool:
    def __init__(self):
        self.ToolName = "AppendFile"
        self.Schema = {
            "name": "AppendFile",
            "description": "Appends content to a file in the scratchpad directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "The name of the file (e.g., data.csv)"},
                    "content": {"type": "string", "description": "The content to append"}
                },
                "required": ["filename", "content"]
            }
        }
        self.base_dir = os.path.expanduser("~/.jarvish/scratchpad")

    def Execute(self, arguments):
        filename = arguments.get("filename")
        content = arguments.get("content")
        path = os.path.join(self.base_dir, os.path.basename(filename))
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully appended to {filename}."
        except Exception as e:
            return f"Error appending to file: {e}"

class ReadFileTool:
    def __init__(self):
        self.ToolName = "ReadFile"
        self.Schema = {
            "name": "ReadFile",
            "description": "Reads content from a file in the scratchpad directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "The name of the file to read"}
                },
                "required": ["filename"]
            }
        }
        self.base_dir = os.path.expanduser("~/.jarvish/scratchpad")

    def Execute(self, arguments):
        filename = arguments.get("filename")
        path = os.path.join(self.base_dir, os.path.basename(filename))
        if not os.path.exists(path):
            return f"Error: File {filename} does not exist."
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {e}"
