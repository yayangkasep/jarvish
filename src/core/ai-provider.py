import os
import sys
import requests
import json

import importlib
from config import paths

app_settings_mod = importlib.import_module("config.app-settings")


class AiProvider:
    def __init__(self):
        self.Settings = app_settings_mod.AppSettings()
        # Local AI backend
        self.Endpoint = os.getenv(
            "AI_PROVIDER_ENDPOINT",
            "http://localhost:20128/v1/chat/completions",
        )
        self.ApiKey = os.getenv("AI_PROVIDER_API_KEY", "test")

    def ExecutePrompt(self, PromptText=None, RequiredTools=None, Messages=None):
        print(f"Executing prompt via Antigravity backend...")

        Headers = {
            "Authorization": f"Bearer {self.ApiKey}",
            "Content-Type": "application/json",
        }

        Payload = {
            "model": self.Settings.GetLlmModel(), 
            "temperature": self.Settings.GetLlmTemperature(),
            "stream": False
        }

        if Messages is not None:
            # Inject System Prompt as the first message
            from datetime import datetime, timedelta

            # Ensure timezone is WIB (UTC+7)
            current_time = (datetime.utcnow() + timedelta(hours=7)).strftime(
                "%Y-%m-%d %H:%M:%S WIB"
            )
            from config.prompt_builder import build_system_prompt

            SystemPrompt = {
                "role": "system",
                "content": build_system_prompt(current_time, RequiredTools, Messages),
            }
            Payload["messages"] = [SystemPrompt] + Messages
        else:
            Payload["messages"] = [{"role": "user", "content": PromptText}]

        # Add tools if provided (OpenAI tool format)
        if RequiredTools:
            # Assume RequiredTools is a list of dicts formatted for OpenAI
            Payload["tools"] = RequiredTools
            Payload["tool_choice"] = "auto"

        import time

        max_retries = 5

        for attempt in range(max_retries):
            try:
                Response = requests.post(
                    self.Endpoint, headers=Headers, json=Payload, timeout=120
                )

                if Response.status_code == 200:
                    Data = Response.json()
                    Choices = Data.get("choices", [])
                    if Choices:
                        Message = Choices[0].get("message", {})
                        print(f"RAW API MESSAGE: {json.dumps(Message)}")

                        # Return the full message object (including content and tool_calls)
                        return Message
                    return {
                        "role": "assistant",
                        "content": "Error: No choices returned from proxy.",
                    }
                elif Response.status_code == 503:
                    print(
                        f"Proxy not ready (503). Retrying in 3 seconds... ({attempt + 1}/{max_retries})"
                    )
                    time.sleep(3)
                    continue
                else:
                    return {
                        "role": "assistant",
                        "content": f"API Error from Antigravity ({Response.status_code}): {Response.text}",
                    }

            except Exception as e:
                print(
                    f"Connection failed. Retrying in 3 seconds... ({attempt + 1}/{max_retries}) - {e}"
                )
                import time

                time.sleep(3)

        return {
            "role": "assistant",
            "content": "Failed to connect to Antigravity proxy after multiple attempts.",
        }
