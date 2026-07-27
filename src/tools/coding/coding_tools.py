import os
import glob
import re
import shutil
import json

class ListDirectoryTool:
    def __init__(self):
        self.ToolName = "ListDirectory"
        self.Schema = {
            "name": self.ToolName,
            "description": "Lists the contents of a directory (similar to 'ls -la').",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the directory (default is current directory '.')"}
                }
            }
        }

    def Execute(self, args):
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except:
                args = {"path": args}
                
        path = args.get("path", ".")
        if not os.path.isdir(path):
            return f"Error: Directory '{path}' not found."
            
        try:
            items = []
            for item in os.listdir(path):
                full_path = os.path.join(path, item)
                is_dir = os.path.isdir(full_path)
                size = os.path.getsize(full_path) if not is_dir else 0
                items.append({
                    "name": item,
                    "type": "directory" if is_dir else "file",
                    "size": size
                })
            return json.dumps(items, indent=2)
        except Exception as e:
            return f"Error listing directory: {str(e)}"

class ReadFileTool:
    def __init__(self):
        self.ToolName = "ReadFile"
        self.Schema = {
            "name": self.ToolName,
            "description": "Reads the contents of a file. Supports line pagination.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to the file."},
                    "start_line": {"type": "integer", "description": "Starting line number (1-indexed). Optional."},
                    "end_line": {"type": "integer", "description": "Ending line number. Optional."}
                },
                "required": ["file_path"]
            }
        }

    def Execute(self, args):
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except:
                pass
                
        file_path = args.get("file_path")
        if not file_path:
            return "Error: file_path is required."
            
        if not os.path.isfile(file_path):
            return f"Error: File '{file_path}' not found."
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                
            start = max(1, args.get("start_line", 1))
            end = args.get("end_line", len(lines))
            end = min(end, len(lines))
            
            output = f"--- {file_path} (Lines {start}-{end} of {len(lines)}) ---\n"
            for i in range(start-1, end):
                output += f"{i+1}: {lines[i]}"
            return output
        except Exception as e:
            return f"Error reading file: {str(e)}"

class GrepSearchTool:
    def __init__(self):
        self.ToolName = "GrepSearch"
        self.Schema = {
            "name": self.ToolName,
            "description": "Searches for a string or regex pattern in files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Search pattern (regex supported)."},
                    "path": {"type": "string", "description": "File or directory path to search in."},
                    "file_extension": {"type": "string", "description": "Filter by extension, e.g. '.py'"}
                },
                "required": ["pattern", "path"]
            }
        }

    def Execute(self, args):
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except:
                pass
                
        pattern = args.get("pattern")
        path = args.get("path")
        ext = args.get("file_extension", "")
        
        if not pattern or not path:
            return "Error: pattern and path are required."
            
        results = []
        try:
            compiled = re.compile(pattern)
            
            if os.path.isfile(path):
                files_to_search = [path]
            elif os.path.isdir(path):
                files_to_search = []
                for root, _, files in os.walk(path):
                    for f in files:
                        if ext and not f.endswith(ext):
                            continue
                        files_to_search.append(os.path.join(root, f))
            else:
                return f"Error: Path '{path}' not found."
                
            for file_path in files_to_search:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        for i, line in enumerate(f):
                            if compiled.search(line):
                                results.append(f"{file_path}:{i+1}:{line.strip()}")
                except:
                    continue # Skip binary or unreadable files
                    
            if not results:
                return "No matches found."
            return "\n".join(results[:100]) # Limit output
        except Exception as e:
            return f"Error executing search: {str(e)}"

class WriteFileTool:
    def __init__(self):
        self.ToolName = "WriteFile"
        self.Schema = {
            "name": self.ToolName,
            "description": "Creates a new file or overwrites an existing one with content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to the file to create/overwrite."},
                    "content": {"type": "string", "description": "The full text content to write."}
                },
                "required": ["file_path", "content"]
            }
        }

    def Execute(self, args):
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except:
                pass
                
        file_path = args.get("file_path")
        content = args.get("content")
        
        if not file_path or content is None:
            return "Error: file_path and content are required."
            
        try:
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully wrote to {file_path}"
        except Exception as e:
            return f"Error writing file: {str(e)}"

class ReplaceContentTool:
    def __init__(self):
        self.ToolName = "ReplaceContent"
        self.Schema = {
            "name": self.ToolName,
            "description": "Replaces a specific block of text in a file with new text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to the file."},
                    "old_text": {"type": "string", "description": "The exact old text block to be replaced (must match exactly)."},
                    "new_text": {"type": "string", "description": "The new text block."}
                },
                "required": ["file_path", "old_text", "new_text"]
            }
        }

    def Execute(self, args):
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except:
                pass
                
        file_path = args.get("file_path")
        old_text = args.get("old_text")
        new_text = args.get("new_text")
        
        if not file_path or not old_text or new_text is None:
            return "Error: file_path, old_text, and new_text are required."
            
        if not os.path.isfile(file_path):
            return f"Error: File '{file_path}' not found."
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            if old_text not in content:
                return "Error: The specified 'old_text' was not found exactly in the file. Use ReadFile to get the exact indentation and text."
                
            new_content = content.replace(old_text, new_text)
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            return f"Successfully replaced content in {file_path}"
        except Exception as e:
            return f"Error replacing content: {str(e)}"

class MakeDirectoryTool:
    def __init__(self):
        self.ToolName = "MakeDirectory"
        self.Schema = {
            "name": self.ToolName,
            "description": "Creates a new directory (mkdir -p).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path to create."}
                },
                "required": ["path"]
            }
        }

    def Execute(self, args):
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except:
                args = {"path": args}
                
        path = args.get("path")
        if not path:
            return "Error: path is required."
            
        try:
            os.makedirs(path, exist_ok=True)
            return f"Successfully created directory {path}"
        except Exception as e:
            return f"Error creating directory: {str(e)}"

class RemoveFileTool:
    def __init__(self):
        self.ToolName = "RemoveFile"
        self.Schema = {
            "name": self.ToolName,
            "description": "Removes a file or directory (rm -rf).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to remove."}
                },
                "required": ["path"]
            }
        }

    def Execute(self, args):
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except:
                args = {"path": args}
                
        path = args.get("path")
        if not path:
            return "Error: path is required."
            
        if not os.path.exists(path):
            return f"Error: Path '{path}' not found."
            
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            return f"Successfully removed {path}"
        except Exception as e:
            return f"Error removing path: {str(e)}"

class MoveFileTool:
    def __init__(self):
        self.ToolName = "MoveFile"
        self.Schema = {
            "name": self.ToolName,
            "description": "Moves or renames a file/directory (mv).",
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Source path."},
                    "destination": {"type": "string", "description": "Destination path."}
                },
                "required": ["source", "destination"]
            }
        }

    def Execute(self, args):
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except:
                pass
                
        src = args.get("source")
        dst = args.get("destination")
        
        if not src or not dst:
            return "Error: source and destination are required."
            
        if not os.path.exists(src):
            return f"Error: Source '{src}' not found."
            
        try:
            shutil.move(src, dst)
            return f"Successfully moved {src} to {dst}"
        except Exception as e:
            return f"Error moving: {str(e)}"

class CopyFileTool:
    def __init__(self):
        self.ToolName = "CopyFile"
        self.Schema = {
            "name": self.ToolName,
            "description": "Copies a file or directory (cp -r).",
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Source path."},
                    "destination": {"type": "string", "description": "Destination path."}
                },
                "required": ["source", "destination"]
            }
        }

    def Execute(self, args):
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except:
                pass
                
        src = args.get("source")
        dst = args.get("destination")
        
        if not src or not dst:
            return "Error: source and destination are required."
            
        if not os.path.exists(src):
            return f"Error: Source '{src}' not found."
            
        try:
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
            return f"Successfully copied {src} to {dst}"
        except Exception as e:
            return f"Error copying: {str(e)}"
