import os

def db_path() -> str:
    """Возвращает абсолютный путь к папке с базой данных."""
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "assets", "data") + os.sep
