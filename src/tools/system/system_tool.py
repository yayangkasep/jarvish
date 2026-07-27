import subprocess


class SystemCommandTool:
    def __init__(self):
        self.ToolName = "SystemCommand"
        self.Schema = {
            "type": "function",
            "function": {
                "name": self.ToolName,
                "description": "Executes terminal commands on the operating system (e.g., apt update, df -h, ls). Warning: Use only if explicitly requested by the user.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The bash/terminal command to execute.",
                        }
                    },
                    "required": ["command"],
                },
            },
        }

    def Execute(self, Arguments):
        command = Arguments.get("command")
        if not command:
            return "Error: The 'command' argument is empty."

        import re
        import uuid
        
        risk_pattern = r'^(sudo|rm|passwd|usermod|userdel|chown|chmod|iptables|ufw|kill|mkfs|dd)\b'
        is_risky = re.match(risk_pattern, command.strip()) or ".jarvish/config" in command

        if is_risky:
            try:
                from core.database import get_session, PendingCommand
                code = "CONF-" + uuid.uuid4().hex[:4].upper()
                db = get_session()
                pending = PendingCommand(
                    code=code,
                    command=command,
                    telegram_id="ANY",
                    status="pending"
                )
                db.add(pending)
                db.commit()
                db.close()
                return f"SECURITY ALERT: The command `{command}` is classified as HIGH RISK. Execution has been paused. Please ask the user to explicitly confirm by sending `/confirm {code}` or deny it by sending `/deny {code}` in Telegram."
            except Exception as e:
                return f"Error creating confirmation gate: {e}"

        try:
            # Gunakan timeout agar tidak hang
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=30
            )

            output = result.stdout + result.stderr

            if not output.strip():
                return f"Command `{command}` executed successfully but produced no output."

            # Batasi panjang output agar tidak over-limit di Telegram/AI Token
            if len(output) > 2000:
                output = (
                    output[:2000] + "\n...[Output truncated due to excessive length]..."
                )

            return f"Output from `{command}`:\n{output}"

        except subprocess.TimeoutExpired:
            return (
                f"Error: Command `{command}` exceeded execution time limit (timeout)."
            )
        except Exception as e:
            return f"Error executing command: {str(e)}"

class UpdateJarvishTool:
    def __init__(self):
        self.ToolName = "UpdateJarvish"
        self.Schema = {
            "type": "function",
            "function": {
                "name": self.ToolName,
                "description": "Automatically updates J.A.R.V.I.S code from the Git repository and restarts the J.A.R.V.I.S service.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        }

    def Execute(self, Arguments):
        try:
            # Jalankan git pull origin master
            pull_result = subprocess.run(
                "git pull origin master", shell=True, capture_output=True, text=True, timeout=30
            )
            output = pull_result.stdout + pull_result.stderr
            
            if pull_result.returncode != 0:
                return f"Failed to perform Git update:\n{output}"
                
            # If pull succeeds, trigger suicide to let systemd restart it
            import threading
            import time
            import os
            
            def kill_self():
                time.sleep(3)
                os._exit(1)
                
            threading.Thread(target=kill_self, daemon=True).start()
            
            return f"Successfully updated code from Git:\n{output}\nSystem will automatically restart in a few seconds."
        except Exception as e:
            return f"Error during update: {str(e)}"

class TestPythonTool:
    def __init__(self):
        self.ToolName = "TestPythonTool"
        self.Schema = {
            "type": "function",
            "function": {
                "name": self.ToolName,
                "description": "Compiles and tests the viability of a Python file (especially for new tools) before deployment. Use this to ensure your code is free of syntax errors and the class structure is correct.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Absolute or relative path to the Python file to be tested (e.g., src/tools/math_tool.py).",
                        }
                    },
                    "required": ["file_path"],
                },
            },
        }

    def Execute(self, Arguments):
        import py_compile
        import importlib.util
        import sys
        import inspect
        import os

        file_path = Arguments.get("file_path")
        if not file_path or not os.path.exists(file_path):
            return f"Error: File '{file_path}' not found."

        try:
            # 1. Syntax Check
            py_compile.compile(file_path, doraise=True)
            
            # 2. Dynamic Import Check
            module_name = os.path.basename(file_path)[:-3]
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # 3. Validation Check
            tool_classes = []
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if obj.__module__ == module.__name__ and name.endswith("Tool"):
                    tool_classes.append(obj)
            
            if not tool_classes:
                return "Syntax OK, but no class ending with 'Tool' was found in this file."
                
            report = ["Syntax OK. Found the following Tool classes:"]
            for cls in tool_classes:
                try:
                    instance = cls()
                    missing = []
                    if not hasattr(instance, "ToolName"): missing.append("ToolName")
                    if not hasattr(instance, "Schema"): missing.append("Schema")
                    if not hasattr(instance, "Execute"): missing.append("Execute() function")
                    
                    if missing:
                        report.append(f"- Class {cls.__name__} is missing required properties: {', '.join(missing)}")
                    else:
                        report.append(f"- Class {cls.__name__} is valid and ready to deploy!")
                except Exception as e:
                    report.append(f"- Error during instantiation of class {cls.__name__}: {str(e)}")
                    
            return "\n".join(report)

        except py_compile.PyCompileError as e:
            return f"Syntax Error in your code:\n{str(e)}"
        except Exception as e:
            return f"Runtime Error while testing your code:\n{str(e)}"

class RestartJarvishTool:
    def __init__(self):
        self.ToolName = "RestartJarvish"
        self.Schema = {
            "type": "function",
            "function": {
                "name": self.ToolName,
                "description": "Gracefully restarts the J.A.R.V.I.S background service. MUST be used AFTER you create/modify source code and it passes testing with TestPythonTool.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        }

    def Execute(self, Arguments):
        import threading
        import time
        import os
        
        def kill_self():
            time.sleep(3)
            os._exit(1)
            
        threading.Thread(target=kill_self, daemon=True).start()
        
        return "System will automatically restart in a few seconds (suicide trigger activated) to apply all your newly created code changes!"
