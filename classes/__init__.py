import os

from .gemini_client import GeminiClient, GeminiMessage
from .yandex_client import yandex_client

# Приоритет: Yandex (если заданы ключи), иначе Gemini
if os.getenv("YANDEX_FOLDER_ID") and os.getenv("YANDEX_API_KEY"):
    gemini_client = yandex_client
else:
    gemini_client = GeminiClient()

__all__ = [
    "gemini_client",
    "GeminiClient",
    "GeminiMessage",
]
