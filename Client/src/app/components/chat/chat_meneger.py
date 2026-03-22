# chat_manager.py
_chat_id = None
def set_chat_id(value):
    global _chat_id
    _chat_id = value
    return _chat_id

def get_chat_id():
    global _chat_id
    return _chat_id


_status_chat = None
def set_status_chat(value):
    global _status_chat
    _status_chat = value
    return _status_chat

def get_status_chat():
    global _status_chat
    return _status_chat