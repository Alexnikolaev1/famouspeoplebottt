"""
Тест Gemini API (один или несколько ключей).
Запуск: python test_gemini.py
Ключи берутся из .env: GEMINI_API_KEY или GEMINI_API_KEYS
"""
import asyncio
import os

from dotenv import load_dotenv

load_dotenv()

from classes.gemini_client import GeminiMessage, gemini_client
from classes.enums import MessageRole


async def main():
    keys = os.getenv("GEMINI_API_KEYS", "").strip() or os.getenv("GEMINI_API_KEY", "")
    if not keys:
        print("Ошибка: задайте GEMINI_API_KEY или GEMINI_API_KEYS в .env")
        return

    n = len([k for k in keys.split(",") if k.strip()])
    print(f"Ключей в конфиге: {n}")
    print(f"Модель: {gemini_client.model}")
    print()

    msg = GeminiMessage("ask")
    msg.update(MessageRole.USER, "Кто такой Николай Федоров? Ответь в одном предложении.")

    print("Отправка запроса...")
    response = await gemini_client.request(msg)
    print("Ответ:", response[:300] + ("..." if len(response) > 300 else ""))
    print()
    print("OK")


if __name__ == "__main__":
    asyncio.run(main())
