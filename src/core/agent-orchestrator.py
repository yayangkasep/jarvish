from config.logger import logger
import json
import re


class AgentOrchestrator:
    def __init__(self, ai_provider, session_manager, tool_registry, memory_manager):
        self.provider = ai_provider
        self.sessions = session_manager
        self.registry = tool_registry
        self.memory = memory_manager
        self.schemas = self.registry.GetToolSchemas()

    def process_message(self, user_id, text, image_base64=None, progress_callback=None):
        try:
            # Cleanup any incomplete tool turns from previous crashes
            self.sessions.CleanupIncompleteTurns(user_id)
            
            # Add user message to session
            if image_base64:
                content_payload = [
                    {
                        "type": "text",
                        "text": text if text else "Tolong jelaskan gambar ini.",
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"},
                    },
                ]
                self.sessions.AddMessage(user_id, "user", content_payload)
            else:
                self.sessions.AddMessage(user_id, "user", text)

            # Call memory compaction to summarize very old messages
            self.sessions.CompactHistory(user_id, self.provider)

            # Fetch full history
            raw_history = self.sessions.GetHistory(user_id)

            # Inject System Context
            system_text = f"Identitas Pengguna (User ID): {user_id}\n"
            
            # Inject Summaries
            if hasattr(self.sessions, 'GetSummaries'):
                summaries = self.sessions.GetSummaries(user_id)
                if summaries:
                    system_text += "\n--- RINGKASAN PERCAKAPAN SEBELUMNYA (ARCHIVED) ---\n"
                    system_text += "\n".join(f"- {s}" for s in summaries)
                    system_text += "\n------------------------------------------------\n\n"
            
            facts = self.memory.GetFacts(user_id)
            if facts:
                system_text += "FAKTA PENTING TENTANG PENGGUNA YANG HARUS DIINGAT:\n"
                system_text += "\n".join(f"- {f}" for f in facts)
                
            history = [{"role": "system", "content": system_text}] + raw_history

            response = ""

            # Tool Execution Loop
            while True:
                response_msg = self.provider.ExecutePrompt(
                    Messages=history, RequiredTools=self.schemas
                )
                content = response_msg.get("content") or ""
                tool_calls = response_msg.get("tool_calls")

                # Support manual JSON format
                json_match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
                raw_json = json_match.group(1) if json_match else None
                
                if not raw_json:
                    fallback = re.search(r"(\{.*\"tool_call\".*\})", content, re.DOTALL)
                    if fallback:
                        raw_json = fallback.group(1)
                        
                if not tool_calls and raw_json:
                    try:
                        parsed = json.loads(raw_json)
                        if "tool_call" in parsed:
                            func_obj = parsed["tool_call"]
                            if isinstance(func_obj.get("arguments"), dict):
                                func_obj["arguments"] = json.dumps(
                                    func_obj["arguments"]
                                )
                            tool_calls = [
                                {
                                    "id": "call_" + func_obj["name"],
                                    "type": "function",
                                    "function": func_obj,
                                }
                            ]
                    except Exception as e:
                        logger.error(f"Error parsing manual tool call: {e}")

                # Support legacy function_call format
                if not tool_calls and response_msg.get("function_call"):
                    tool_calls = [
                        {
                            "id": "call_" + response_msg["function_call"]["name"],
                            "function": response_msg["function_call"],
                        }
                    ]

                if tool_calls:
                    # Save AI request for tool call
                    self.sessions.AddMessage(
                        user_id, "assistant", content, tool_calls=tool_calls
                    )

                    for tc in tool_calls:
                        tool_name = tc.get("function", {}).get("name")
                        try:
                            args_str = tc.get("function", {}).get("arguments", "{}")
                            args = (
                                json.loads(args_str)
                                if isinstance(args_str, str)
                                else args_str
                            )
                        except Exception as e:
                            logger.error(f"Error parsing args: {e}")
                            args = {}

                        # Execute the tool
                        logger.info(f"Executing tool {tool_name} with args {args}")
                        if progress_callback:
                            progress_callback(f"Accessing system resource: {tool_name}...")

                        result = self.registry.ExecuteTool(tool_name, args)

                        # Add tool response to history
                        self.sessions.AddMessage(
                            user_id,
                            "tool",
                            str(result),
                            name=tool_name,
                            tool_call_id=tc.get("id"),
                        )

                    # Refresh history and loop again
                    raw_history = self.sessions.GetHistory(user_id)
                    system_text = f"Identitas Pengguna (User ID): {user_id}\n"
                    facts = self.memory.GetFacts(user_id)
                    if facts:
                        system_text += "FAKTA PENTING TENTANG PENGGUNA YANG HARUS DIINGAT:\n"
                        system_text += "\n".join(f"- {f}" for f in facts)
                    history = [{"role": "system", "content": system_text}] + raw_history
                else:
                    # Final response
                    self.sessions.AddMessage(user_id, "assistant", content)
                    response = content
                    break

            return response
        except Exception as e:
            logger.error(f"Error processing prompt: {e}")
            raise
