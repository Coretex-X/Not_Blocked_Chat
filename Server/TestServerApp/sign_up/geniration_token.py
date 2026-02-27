import secrets
import string
import time
import hashlib
from typing import Set

class GuaranteedUniqueTokenGenerator:
    def __init__(self):
        self.all_characters = string.ascii_letters + string.digits + string.punctuation
        self.used_tokens: Set[str] = set()
    def generate_token(self, length: int = 100) -> str:
        if length < 10:
            raise ValueError("Длина токена должна быть не менее 10 символов")
        max_attempts = 1000
        attempts = 0
        while attempts < max_attempts:
            attempts += 1
            unique_base = f"{time.time_ns()}_{secrets.randbelow(10**20)}_{secrets.token_hex(16)}"
            hash_obj = hashlib.sha3_256(unique_base.encode())
            hash_hex = hash_obj.hexdigest()
            token_chars = []
            for char in hash_hex:
                index = int(char, 16)
                token_chars.append(self.all_characters[index % len(self.all_characters)])
            token = ''.join(token_chars)
            while len(token) < length:
                additional = ''.join(secrets.choice(self.all_characters) 
                                   for _ in range(length - len(token)))
                token += additional
            token = token[:length]
            if token not in self.used_tokens:
                self.used_tokens.add(token)
                return token
        raise RuntimeError(f"Не удалось сгенерировать уникальный токен после {max_attempts} попыток")
    
    def is_token_used(self, token: str) -> bool:
        return token in self.used_tokens
    def clear_history(self):
        self.used_tokens.clear()
