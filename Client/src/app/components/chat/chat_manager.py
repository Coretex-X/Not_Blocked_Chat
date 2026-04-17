"""Глобальное состояние текущего чата (chat_id и status_chat)."""

_chat_id = None
_status_chat = None


def set_chat_id(value):
    global _chat_id
    _chat_id = value


def get_chat_id():
    return _chat_id


def set_status_chat(value):
    global _status_chat
    _status_chat = value


def get_status_chat():
    return _status_chat
