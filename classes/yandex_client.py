"""
Клиент YandexGPT (Yandex Cloud AI) для Famous People Bot.
Оплата картой РФ, без VPN. Тариф: YandexGPT Lite ~200 ₽/1M токенов.
Документация: https://yandex.cloud/ru/docs/ai-studio/
"""

import asyncio
import json
import logging
import os

import httpx

from .enums import MessageRole
from .gemini_client import GeminiMessage

logger = logging.getLogger(__name__)

YANDEX_API_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"


class YandexClient:
    """Клиент для YandexGPT API."""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.folder_id = (os.getenv("YANDEX_FOLDER_ID") or "").strip()
        self.api_key = (os.getenv("YANDEX_API_KEY") or "").strip()
        self.model = (os.getenv("YANDEX_MODEL") or "yandexgpt-lite").strip()

    def _build_payload(self, messages: GeminiMessage, max_tokens: int = 2048) -> dict:
        """Преобразует GeminiMessage в формат YandexGPT API."""
        model_uri = f"gpt://{self.folder_id}/{self.model}"

        # Ограничиваем историю (как в Gemini)
        max_pairs = int(os.getenv("GEMINI_MAX_HISTORY_PAIRS", "3"))
        msg_list = messages.message_list
        dialogue = []
        for msg in msg_list:
            role = msg["role"]
            content = msg["content"]
            if role != MessageRole.SYSTEM.value:
                dialogue.append(msg)
        keep = max_pairs * 2
        if len(dialogue) > keep:
            dialogue = dialogue[-keep:]

        yandex_messages = []
        for msg in dialogue:
            role = msg["role"]
            text = msg["content"]
            if role in (MessageRole.USER.value, MessageRole.ASSISTANT.value):
                yandex_messages.append({"role": role, "text": text})

        # System instruction — первый system из message_list
        for msg in msg_list:
            if msg["role"] == MessageRole.SYSTEM.value:
                yandex_messages.insert(0, {"role": "system", "text": msg["content"]})
                break

        if not yandex_messages or all(m["role"] == "system" for m in yandex_messages):
            yandex_messages.append({"role": "user", "text": "Выполни инструкцию."})

        return {
            "modelUri": model_uri,
            "completionOptions": {
                "stream": False,
                "temperature": 0.7,
                "maxTokens": str(max_tokens),
            },
            "messages": yandex_messages,
        }

    async def request(self, messages: GeminiMessage, max_tokens: int = 2048) -> str:
        """Отправляет запрос к YandexGPT API и возвращает текст ответа."""
        if not self.folder_id or not self.api_key:
            logger.error("YANDEX_FOLDER_ID или YANDEX_API_KEY не заданы")
            return "Извините, не настроен Yandex Cloud AI. Обратитесь к администратору."

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Api-Key {self.api_key}",
        }
        payload = self._build_payload(messages, max_tokens=max_tokens)

        try:
            logger.info("YandexGPT запрос: %s", self.model)
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(YANDEX_API_URL, json=payload, headers=headers)

            if response.status_code == 429:
                logger.warning("YandexGPT 429 rate limit")
                return (
                    "Попробуйте подождать пару минут. "
                    "А если запросов было много — сделайте попытку позже."
                )

            response.raise_for_status()
            data = response.json()

            result = data.get("result", {})
            alternatives = result.get("alternatives", [])
            if not alternatives:
                logger.error("YandexGPT: пустой ответ")
                return "Извините, нейросеть вернула пустой ответ. Попробуйте позже."

            text = alternatives[0].get("message", {}).get("text", "")
            usage = result.get("usage", {})
            logger.info("YandexGPT ответ: %s символов, токенов: %s", len(text), usage)
            return text or ""

        except httpx.HTTPStatusError as e:
            logger.warning("YandexGPT API ошибка: %s - %s", e.response.status_code, e.response.text[:200])
            if e.response.status_code == 429:
                return (
                    "Попробуйте подождать пару минут. "
                    "А если запросов было много — сделайте попытку позже."
                )
            return f"Ошибка YandexGPT API: {e.response.status_code}. Попробуйте позже."

        except Exception as e:
            logger.exception("YandexGPT ошибка: %s", e)
            return "Извините, произошла ошибка. Попробуйте позже."


yandex_client = YandexClient()
