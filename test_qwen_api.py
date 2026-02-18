"""
Тест Scitely API — бесплатно, 60 запросов/мин, 15+ моделей.
Получить ключ: https://console.scitely.com
Запуск: SCITELY_API_KEY=sk-scitely-xxx python test_qwen_api.py
"""
import os
from openai import OpenAI

api_key = os.getenv("SCITELY_API_KEY")
if not api_key:
    print("Ошибка: задайте SCITELY_API_KEY в переменных окружения")
    exit(1)

print("Тест Scitely API (бесплатный Community tier)...")
print("Base URL: https://api.scitely.com/v1")
print("Model: deepseek-v3.2 (128K контекст)")
print()

try:
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.scitely.com/v1",
    )
    response = client.chat.completions.create(
        model="deepseek-v3.2",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Who are you? Answer in one sentence."},
        ],
    )
    print("Успех! Ответ:", response.choices[0].message.content)
except Exception as e:
    print("Ошибка:", e)
