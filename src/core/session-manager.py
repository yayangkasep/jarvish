import json
from core.database import get_session, User, ChatHistory, init_db

class SessionManager:
    def __init__(self):
        # Ensure database tables exist
        init_db()
        # Limit active context window to 20 messages to save LLM tokens
        self.MAX_HISTORY = 200

    def _get_or_create_user(self, db, telegram_id):
        telegram_id = str(telegram_id)
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            user = User(telegram_id=telegram_id)
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    def GetHistory(self, user_id):
        db = get_session()
        try:
            user = self._get_or_create_user(db, user_id)
            # Only get active chats for context window
            chats = db.query(ChatHistory).filter(
                ChatHistory.user_id == user.id,
                ChatHistory.active == 1
            ).order_by(ChatHistory.timestamp.desc()).limit(self.MAX_HISTORY).all()
            
            # Reverse to maintain chronological order for LLM
            chats.reverse()
            
            history = []
            for chat in chats:
                try:
                    msg = json.loads(chat.message_json)
                    history.append(msg)
                except Exception as e:
                    print(f"Failed to parse chat json: {e}")
            
            # --- SANITIZE HISTORY FOR GEMINI API ---
            # Gemini strictly requires tool responses to immediately follow tool calls.
            sanitized = []
            for i, msg in enumerate(history):
                role = msg.get("role")
                
                # If it's a tool message, ensure the previous message was an assistant tool call or another tool message
                if role == "tool":
                    if not sanitized:
                        continue # Drop orphaned tool message at the start
                    
                    prev_msg = sanitized[-1]
                    if prev_msg.get("role") == "tool":
                        pass # Subsequent tool response, allowed
                    elif prev_msg.get("role") == "assistant" and prev_msg.get("tool_calls"):
                        pass # First tool response, allowed
                    else:
                        # Preceding message is not an assistant tool call, drop this tool message
                        continue
                        
                # If previous message was an assistant with tool_calls, but current is NOT a tool message
                if sanitized:
                    prev_msg = sanitized[-1]
                    if prev_msg.get("role") == "assistant" and prev_msg.get("tool_calls") and role != "tool":
                        # The assistant made a tool call but never got a response (dangling tool call)
                        # We must strip the tool_calls from the assistant message to prevent API error
                        del prev_msg["tool_calls"]
                        
                        # If stripping tool_calls makes the message empty, we must delete it entirely
                        if not prev_msg.get("content") or str(prev_msg.get("content")).strip() == "":
                            sanitized.pop()
                
                sanitized.append(msg)
                
            # Final check: if the very last message is a dangling tool_call, strip it
            if sanitized:
                last_msg = sanitized[-1]
                if last_msg.get("role") == "assistant" and last_msg.get("tool_calls"):
                    del last_msg["tool_calls"]
                    if not last_msg.get("content") or str(last_msg.get("content")).strip() == "":
                        sanitized.pop()

            # --- MERGE CONSECUTIVE ROLES ---
            # Gemini strictly forbids consecutive messages of the same role (e.g., User -> User)
            final_history = []
            for msg in sanitized:
                if not final_history:
                    final_history.append(msg)
                    continue
                
                prev_msg = final_history[-1]
                if prev_msg.get("role") == msg.get("role") and msg.get("role") in ["user", "assistant"]:
                    # Merge contents
                    prev_content = prev_msg.get("content", "")
                    curr_content = msg.get("content", "")
                    
                    if isinstance(prev_content, list) or isinstance(curr_content, list):
                        new_content = []
                        if isinstance(prev_content, list):
                            new_content.extend(prev_content)
                        elif prev_content:
                            new_content.append({"type": "text", "text": str(prev_content)})
                            
                        if isinstance(curr_content, list):
                            new_content.extend(curr_content)
                        elif curr_content:
                            new_content.append({"type": "text", "text": str(curr_content)})
                            
                        prev_msg["content"] = new_content
                    else:
                        prev_str = str(prev_content) if prev_content else ""
                        curr_str = str(curr_content) if curr_content else ""
                        
                        if prev_str and curr_str:
                            prev_msg["content"] = prev_str + "\n\n" + curr_str
                        elif curr_str:
                            prev_msg["content"] = curr_str
                        
                    # Merge tool calls if any
                    if msg.get("tool_calls"):
                        if "tool_calls" not in prev_msg:
                            prev_msg["tool_calls"] = []
                        prev_msg["tool_calls"].extend(msg["tool_calls"])
                else:
                    final_history.append(msg)
                    
            # Ensure the history starts with a valid turn (user or assistant text) to prevent API sequence errors
            while final_history:
                first_role = final_history[0].get("role")
                has_tools = bool(final_history[0].get("tool_calls"))
                
                if first_role == "user":
                    break
                elif first_role == "assistant" and not has_tools:
                    break
                else:
                    final_history.pop(0)
                    
            # --- DYNAMIC TOOL TRUNCATION ---
            # Truncate old tool responses to save tokens.
            # A tool response is "old" if there is any non-tool message after it.
            for i in range(len(final_history) - 1):
                msg = final_history[i]
                if msg.get("role") == "tool":
                    is_past = False
                    for j in range(i + 1, len(final_history)):
                        if final_history[j].get("role") != "tool":
                            is_past = True
                            break
                    
                    if is_past:
                        content = str(msg.get("content", ""))
                        if len(content) > 1000:
                            msg["content"] = '{"status": "Data diproses. Detail disembunyikan untuk hemat token."}'
                            
            return final_history
        finally:
            db.close()

    def AddMessage(self, user_id, role, content, **kwargs):
        db = get_session()
        try:
            user = self._get_or_create_user(db, user_id)
            
            msg = {"role": role, "content": content}
            msg.update(kwargs)
            
            new_chat = ChatHistory(
                user_id=user.id,
                message_json=json.dumps(msg)
            )
            db.add(new_chat)
            db.commit()
        finally:
            db.close()

    def ClearSession(self, user_id):
        db = get_session()
        try:
            user = self._get_or_create_user(db, user_id)
            # Archive chats instead of deleting to preserve long-term history
            db.query(ChatHistory).filter(
                ChatHistory.user_id == user.id,
                ChatHistory.active == 1
            ).update({"active": 0})
            db.commit()
        finally:
            db.close()

    def CleanupIncompleteTurns(self, user_id):
        # Incomplete turns cleanup can be skipped for now, 
        # or we just remove the last message if it's a tool call.
        db = get_session()
        try:
            user = self._get_or_create_user(db, user_id)
            last_chat = db.query(ChatHistory).filter(
                ChatHistory.user_id == user.id,
                ChatHistory.active == 1
            ).order_by(ChatHistory.timestamp.desc()).first()
            
            if not last_chat:
                return
                
            msg = json.loads(last_chat.message_json)
            role = msg.get("role")
            
            # If the last message in DB is a tool call or assistant tool invocation, delete it
            # This ensures we don't have dangling tool calls if it crashes
            if role == "tool" or (role == "assistant" and msg.get("tool_calls")):
                db.delete(last_chat)
                db.commit()
                # Run recursively in case there are multiple
                self.CleanupIncompleteTurns(user_id)
        except Exception as e:
            print(f"Cleanup error: {e}")
        finally:
            db.close()
