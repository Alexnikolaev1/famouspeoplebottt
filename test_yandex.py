"""
Тест YandexGPT API (Yandex Cloud AI).
Запуск: python test_yandex.py
Требуется в .env: YANDEX_FOLDER_ID, YANDEX_API_KEY
"""
import asyncio
import os

from dotenv import load_dotenv

load_dotenv()

from classes.gemini_client import GeminiMessage
from classes.enums import MessageRole

# Импортируем после load_dotenv, чтобы env был загружен
from classes import gemini_client


async def main():
    folder_id = os.getenv("YANDEX_FOLDER_ID", "").strip()
    api_key = os.getenv("YANDEX_API_KEY", "").strip()

    if not folder_id or not api_key:
        print("Ошибка: задайте YANDEX_FOLDER_ID и YANDEX_API_KEY в .env")
        print("См. YANDEX_SETUP.md")
        return

    print("Yandex Cloud AI (YandexGPT Lite)")
    print(f"Folder ID: {folder_id[:8]}...")
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
