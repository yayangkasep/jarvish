import json
from core.database import get_session, User, ChatHistory

class SearchHistoryTool:
    def __init__(self):
        self.ToolName = "SearchHistoryTool"
        self.Schema = {
            "name": self.ToolName,
            "description": "Search the user's entire past chat history for specific keywords to remember past conversations, preferences, or context. (RAG Engine)",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "The specific keyword or phrase to search for in past chats."
                    },
                    "user_id": {
                        "type": "string",
                        "description": "The unique ID of the user. Automatically filled by system."
                    }
                },
                "required": ["keyword", "user_id"]
            }
        }

    def Execute(self, kwargs):
        keyword = kwargs.get("keyword")
        user_id = str(kwargs.get("user_id"))

        if not keyword or not user_id or user_id == "None":
            return "Error: 'keyword' and 'user_id' are required."

        db = get_session()
        try:
            user = db.query(User).filter(User.telegram_id == user_id).first()
            if not user:
                return "No chat history found for this user."

            # Case-insensitive search using LIKE
            search_pattern = f"%{keyword}%"
            
            # Search archived summaries first
            from core.database import ChatSummary
            summary_results = db.query(ChatSummary).filter(
                ChatSummary.user_id == user.id,
                ChatSummary.summary_text.ilike(search_pattern)
            ).order_by(ChatSummary.created_at.desc()).limit(5).all()
            
            # Then search raw history
            results = db.query(ChatHistory).filter(
                ChatHistory.user_id == user.id,
                ChatHistory.message_json.ilike(search_pattern)
            ).order_by(ChatHistory.timestamp.desc()).limit(10).all()

            if not results and not summary_results:
                return f"No past conversations found containing '{keyword}'."

            # Format results
            formatted_results = []
            
            # Format summaries first
            if summary_results:
                formatted_results.append("=== ARCHIVED SUMMARIES ===")
                for s in summary_results:
                    formatted_results.append(f"[{s.created_at.strftime('%Y-%m-%d')}] SUMMARY: {s.summary_text}")
                formatted_results.append("==========================")
                
            for r in results:
                try:
                    msg = json.loads(r.message_json)
                    content = msg.get("content", "")
                    if content and isinstance(content, str):
                        # truncate long messages for context efficiency
                        if len(content) > 300:
                            content = content[:300] + "..."
                        formatted_results.append(f"[{r.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {msg.get('role').upper()}: {content}")
                except:
                    pass

            # Reverse to chronological order (oldest first in the matched set)
            formatted_results.reverse()
            
            return f"Search Results for '{keyword}':\n" + "\n".join(formatted_results)
            
        finally:
            db.close()
