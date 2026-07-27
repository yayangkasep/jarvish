from config.logger import logger
import importlib
import sys
import os
import re

# Import core modules
ai_provider_mod = importlib.import_module("core.ai-provider")
session_manager_mod = importlib.import_module("core.session-manager")
tool_registry_mod = importlib.import_module("tools.tool-registry")
app_settings_mod = importlib.import_module("config.app-settings")
telegram_mcp_mod = importlib.import_module("connectors.telegram-mcp")
agent_orchestrator_mod = importlib.import_module("core.agent-orchestrator")
from tools.memory.memory_tool import MemoryTool

try:
    from elevenlabs.client import ElevenLabs
    from pydub import AudioSegment
    import os
except ImportError:
    ElevenLabs = None
    AudioSegment = None

def strip_markdown_for_tts(text):
    import re
    # Remove code blocks
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    # Remove inline code
    text = re.sub(r'`.*?`', '', text)
    # Remove bold/italic/strikethrough markers
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'_(.*?)_', r'\1', text)
    text = re.sub(r'~~(.*?)~~', r'\1', text)
    # Remove URLs
    text = re.sub(r'http[s]?://\S+', '', text)
    # Remove image tags
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    # Remove links
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    # Remove HTML tags
    text = re.sub(r'<.*?>', '', text)
    # Fix degrees symbol for TTS
    text = text.replace("°C", " derajat Celcius")
    text = text.replace("° C", " derajat Celcius")
    text = text.replace("°", " derajat")
    return text.strip()

def send_voice_note(connector, user_id, text):
    if not ElevenLabs or not AudioSegment:
        logger.info("TTS packages not installed. Skipping voice note.")
        return
        
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        logger.info("ELEVENLABS_API_KEY not found in environment. Skipping voice note.")
        return
        
    clean_text = strip_markdown_for_tts(text)
    if not clean_text or len(clean_text) < 2:
        return
        
    # Limit voice length to prevent extremely long generation
    if len(clean_text) > 800:
        clean_text = clean_text[:800] + "... dan seterusnya."
        
    try:
        import tempfile
        client = ElevenLabs(api_key=api_key)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            mp3_path = os.path.join(tmpdir, "voice.mp3")
            ogg_path = os.path.join(tmpdir, "voice.ogg")
            
            # Generate speech using ElevenLabs (JBFqnCBsd6RMkjVDRZzb)
            audio_generator = client.text_to_speech.convert(
                text=clean_text,
                voice_id="JBFqnCBsd6RMkjVDRZzb",
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128",
            )
            
            with open(mp3_path, "wb") as f:
                for chunk in audio_generator:
                    f.write(chunk)
            
            # Convert to OGG OPUS
            audio = AudioSegment.from_mp3(mp3_path)
            audio.export(ogg_path, format="ogg", codec="libopus")
            
            # Send to Telegram
            connector.SendVoice(user_id, ogg_path)
    except Exception as e:
        logger.error(f"Error generating/sending voice note: {e}")

AiProvider = ai_provider_mod.AiProvider
SessionManager = session_manager_mod.SessionManager
ToolRegistry = tool_registry_mod.ToolRegistry
AppSettings = app_settings_mod.AppSettings
TelegramMcp = telegram_mcp_mod.TelegramMcp
AgentOrchestrator = agent_orchestrator_mod.AgentOrchestrator


def send_long_message(connector, user_id, text, msg_id=None):
    if not text:
        if msg_id:
            connector.EditMessage(user_id, msg_id, "Image processed successfully.")
        return

    if len(text) > 4000:
        first_chunk = text[:4000]
        if msg_id:
            connector.EditMessage(user_id, msg_id, first_chunk)
        else:
            connector.SendMessage(user_id, first_chunk)

        for i in range(4000, len(text), 4000):
            connector.SendMessage(user_id, text[i : i + 4000])
    else:
        if msg_id:
            connector.EditMessage(user_id, msg_id, text)
        else:
            connector.SendMessage(user_id, text)


def main():
    logger.info("--- Initializing Jarvish-Google System ---")

    # 0. Load Configuration
    Settings = AppSettings()
    logger.info(f"Server is running!")
    logger.info(f"Telegram Token Loaded: {'Yes' if Settings.GetTelegramToken() else 'No'}")

    # 1. Initialize Connectors
    logger.info("\n--- Testing Connectors ---")
    AllowedUsers = Settings.GetAllowedUsers()
    
    # SECURITY: Fail-closed if no allowed users are specified or if wildcard is used
    if not AllowedUsers or "*" in AllowedUsers:
        logger.info("CRITICAL SECURITY ERROR: TELEGRAM_ALLOWED_USERS is empty or set to '*'.")
        logger.info("You must specify a comma-separated list of allowed Telegram user IDs in your .env file.")
        logger.info("Failing safe and terminating bot.")
        sys.exit(1)
        
    TelegramConnector = TelegramMcp(
        Token=Settings.GetTelegramToken(), AllowedUsers=AllowedUsers
    )
    TelegramConnector.Connect()

    # 2. Initialize Tools
    logger.info("\n--- Initializing Tools ---")
    Registry = ToolRegistry()
    Registry.AutoDiscoverTools(os.path.join(os.path.dirname(__file__), "tools"))

    # Also discover custom AI-generated tools in the working directory
    custom_tools_dir = os.path.join(os.getcwd(), "src", "tools")
    if os.path.exists(custom_tools_dir) and custom_tools_dir != os.path.join(os.path.dirname(__file__), "tools"):
        Registry.AutoDiscoverTools(custom_tools_dir)

    # Load GitHub MCP
    try:
        from core.mcp_manager import McpManager, McpToolWrapper

        github_mcp_path = os.path.join(
            os.path.dirname(__file__), "bin", "github-mcp-server"
        )
        if os.path.exists(github_mcp_path):
            logger.info("\n--- Initializing GitHub MCP ---")
            mcp_manager = McpManager(
                command=github_mcp_path, args=["stdio", "--toolsets=all"]
            )
            mcp_schemas = mcp_manager.GetSchemas()
            for schema in mcp_schemas:
                original_name = schema["name"]
                tool_name = f"github_{original_name}"
                schema["name"] = tool_name
                wrapper = McpToolWrapper(mcp_manager, original_name)
                Registry.RegisterTool(tool_name, wrapper, schema)
            logger.info(f"Registered {len(mcp_schemas)} MCP tools.")
    except Exception as e:
        logger.error(f"Error loading MCP tools: {e}")

    Schemas = Registry.GetToolSchemas()
    logger.info(f"Registered {len(Schemas)} tool schemas.")

    # 3. Initialize AI Provider and Session Manager
    logger.info("\n--- Initializing AI Provider and Session ---")
    Provider = AiProvider()
    Sessions = SessionManager()

    # Get memory manager from memory tool instance if available
    memory_manager = None
    if "MemoryTool" in Registry.AvailableTools:
        memory_manager = Registry.AvailableTools["MemoryTool"][
            "Instance"
        ].memory_manager
    else:
        # Fallback manual init
        memory_manager = MemoryTool().memory_manager

    Orchestrator = AgentOrchestrator(Provider, Sessions, Registry, memory_manager)

    # 4. Message Handler for Telegram
    def handle_incoming_message(user_id, text, image_base64=None, is_voice=False):
        if text and text.startswith("/start"):
            TelegramConnector.SendMessage(
                user_id,
                "Welcome, Sir. The J.A.R.V.I.S system is online and ready for your commands.",
            )
            return
        elif text and text.startswith("/help"):
            TelegramConnector.SendMessage(
                user_id,
                "Help Protocol Active, Sir.\n\nYou may provide any instructions via text. To reset my memory and start a new topic, please use the /clear command.",
            )
            return
        elif text and text.startswith("/clear"):
            Sessions.ClearSession(user_id)
            TelegramConnector.SendMessage(
                user_id,
                "Session memory cleared, Sir. We are starting with a fresh system. What are your next commands?",
            )
            return
        elif text and text.startswith("/model"):
            args = text.split(maxsplit=1)
            if len(args) > 1:
                new_model = args[1].strip()
                if new_model.lower() == "list":
                    try:
                        import requests
                        endpoint_url = os.getenv("AI_PROVIDER_ENDPOINT", "http://127.0.0.1:20128/v1/chat/completions")
                        base_url = endpoint_url.split("/v1")[0] + "/v1/models"
                        resp = requests.get(base_url, timeout=5)
                        if resp.status_code == 200:
                            models = [m["id"] for m in resp.json().get("data", [])]
                            # Limit to top 50 models to avoid too long messages
                            msg = "Available Models:\n- " + "\n- ".join(models[:50])
                            if len(models) > 50:
                                msg += f"\n... and {len(models)-50} more."
                            TelegramConnector.SendMessage(user_id, msg)
                            return
                    except Exception as e:
                        TelegramConnector.SendMessage(user_id, f"Failed to fetch models: {e}")
                        return
                        
                Provider.Settings.LlmModel = new_model
                TelegramConnector.SendMessage(user_id, f"AI Model has been switched to: {new_model}")
            else:
                TelegramConnector.SendMessage(user_id, f"Current AI Model is: {Provider.Settings.LlmModel}\n\nTo change it, type: /model <model_name>\nTo view available models, type: /model list")
            return

        logger.info(f"Processing message from {user_id}...")
        msg_id = TelegramConnector.SendMessage(user_id, "Thinking...")

        def progress_cb(msg):
            TelegramConnector.EditMessage(user_id, msg_id, msg)

        try:
            Response = Orchestrator.process_message(
                user_id, text, image_base64, progress_cb
            )

            # Extract and send markdown images first
            images = re.findall(r"!\[(.*?)\]\((.*?)\)", Response)
            if images:
                for caption, url in images:
                    TelegramConnector.SendPhoto(user_id, url, caption)
                    Response = Response.replace(f"![{caption}]({url})", "").strip()

            if is_voice:
                # If user used voice, only reply with voice note and delete the "Thinking..." text
                send_voice_note(TelegramConnector, user_id, Response)
                if msg_id:
                    TelegramConnector.DeleteMessage(user_id, msg_id)
            else:
                # If user used text, only reply with text
                send_long_message(TelegramConnector, user_id, Response, msg_id)

        except Exception as e:
            logger.error(f"Error processing prompt: {e}")
            TelegramConnector.EditMessage(
                user_id,
                msg_id,
                "Sorry, I encountered an error while communicating with the AI.",
            )

    # 4.5 Start Proactive Background Scheduler
    from core.scheduler import BackgroundScheduler
    from core.database import get_session, User
    
    def get_target_users():
        db = get_session()
        try:
            users = db.query(User).all()
            return [u.telegram_id for u in users]
        finally:
            db.close()
            
    def proactive_callback(user_id, text):
        logger.info(f"Executing proactive routine for {user_id}")
        msg_id = TelegramConnector.SendMessage(user_id, "Compiling proactive report...")
        
        def progress_cb(msg):
            TelegramConnector.EditMessage(user_id, msg_id, msg)
            
        try:
            Response = Orchestrator.process_message(
                user_id, text, image_base64=None, progress_callback=progress_cb
            )
            
            # Extract and send markdown images first
            images = re.findall(r"!\[(.*?)\]\((.*?)\)", Response)
            if images:
                for caption, url in images:
                    TelegramConnector.SendPhoto(user_id, url, caption)
                    Response = Response.replace(f"![{caption}]({url})", "").strip()
            
            # Send the final response via text and voice note
            send_long_message(TelegramConnector, user_id, Response, msg_id)
            send_voice_note(TelegramConnector, user_id, Response)
            
        except Exception as e:
            logger.error(f"Error in proactive event: {e}")
            TelegramConnector.EditMessage(user_id, msg_id, f"Failed to compile proactive report: {e}")

    scheduler = BackgroundScheduler(proactive_callback, get_target_users)
    scheduler.start()

    # 5. Start Polling
    if TelegramConnector.IsConnected:
        TelegramConnector.StartPolling(handle_incoming_message)
    else:
        logger.info("Failed to start bot: Telegram connector is not connected.")


if __name__ == "__main__":
    main()
