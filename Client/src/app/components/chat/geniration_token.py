import random
import string
import time


class GuaranteedUniqueTokenGenerator:
    """Генератор гарантированно уникальных токенов."""

    def __init__(self):
        self._used: set = set()

    def generate_token(self, length: int = 90) -> str:
        chars = string.ascii_letters + string.digits
        while True:
            token = ''.join(random.choices(chars, k=length))
            if token not in self._used:
                self._used.add(token)
                return token
