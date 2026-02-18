"""
LLM клиент для Famous People Bot.
Использует Scitely API — бесплатно, без карты, 60 запросов/мин, 15+ моделей.
Документация: https://platform.scitely.com/docs
"""

import logging
import os

from openai import AsyncOpenAI

from .enums import MessageRole, Extensions, ResourcePath

logger = logging.getLogger(__name__)

# https://platform.scitely.com/docs — Community tier бесплатно
SCITELY_BASE_URL = "https://api.scitely.com/v1"
SCITELY_MODEL = "deepseek-v3.2"
SCITELY_FALLBACK_MODELS = ["qwen3-max", "qwen3-32b", "deepseek-r1", "kimi-k2-0905"]


class GeminiMessage:
    def __init__(self, prompt: str):
        self.prompt_file = prompt + Extensions.TXT.value
        self.message_list = self._init_message()

    def _init_message(self) -> list[dict[str, str]]:
        message = {
            'role': MessageRole.SYSTEM.value,
            'content': self._load_prompt(),
        }
        return [message]

    def _load_prompt(self) -> str:
        if '..' in self.prompt_file or os.path.sep in self.prompt_file:
            raise ValueError(f'Недопустимый путь к промпту: {self.prompt_file}')
        prompt_path = os.path.join(ResourcePath.PROMPTS.value, self.prompt_file)
        if not os.path.exists(prompt_path):
            raise FileNotFoundError(f'Файл промпта не найден: {prompt_path}')
        with open(prompt_path, 'r', encoding='UTF-8') as file:
            prompt = file.read()

        prompt = self._append_orthodox_filter(prompt)
        return prompt

    def _append_orthodox_filter(self, base_prompt: str) -> str:
        filter_path = os.path.join(ResourcePath.PROMPTS.value, 'orthodox_filter.txt')
        if os.path.exists(filter_path):
            with open(filter_path, 'r', encoding='UTF-8') as f:
                filter_text = f.read()
            return f"{base_prompt}\n\n{filter_text}"
        return base_prompt

    def update(self, role: MessageRole, message: str):
        message = {
            'role': role.value,
            'content': message,
        }
        self.message_list.append(message)

    def to_dict(self) -> dict:
        """Сериализация в JSON-совместимый dict (для RedisStorage)."""
        return {
            'prompt_file': self.prompt_file,
            'message_list': self.message_list,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'GeminiMessage':
        """Восстановление из dict (после чтения из Redis)."""
        obj = object.__new__(cls)
        obj.prompt_file = data['prompt_file']
        obj.message_list = data['message_list']
        return obj


class GeminiClient:
    """Клиент для работы с Scitely API (бесплатный Community tier)."""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, api_key: str | None = None):
        self.api_key = (api_key or os.getenv('SCITELY_API_KEY') or '').strip()
        self.model = os.getenv('SCITELY_MODEL') or SCITELY_MODEL
        self.models = [self.model] + [
            m for m in SCITELY_FALLBACK_MODELS if m != self.model
        ]
        self.base_url = (
            os.getenv('SCITELY_BASE_URL') or SCITELY_BASE_URL
        ).strip().rstrip('/')
        self._client: AsyncOpenAI | None = None

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
        return self._client

    def _to_openai_messages(self, messages: GeminiMessage) -> list[dict[str, str]]:
        result = []
        for msg in messages.message_list:
            result.append({'role': msg['role'], 'content': msg['content']})
        return result or [{'role': 'user', 'content': 'Выполни инструкцию.'}]

    async def request(self, messages: GeminiMessage, max_tokens: int = 8192) -> str:
        """Отправляет запрос к Scitely API и возвращает текст ответа."""
        if not self.api_key:
            logger.error('SCITELY_API_KEY не задан')
            return 'Извините, не настроен API ключ. Обратитесь к администратору.'

        client = self._get_client()
        openai_messages = self._to_openai_messages(messages)

        for model in self.models:
            try:
                logger.info('Scitely запрос: model=%s', model)
                response = await client.chat.completions.create(
                    model=model,
                    messages=openai_messages,
                    max_tokens=min(max_tokens, 8192),
                    temperature=0.7,
                )
                if not response.choices:
                    return 'Извините, нейросеть вернула пустой ответ. Попробуйте позже.'
                text = (response.choices[0].message.content or '').strip()
                logger.info('Scitely ответ: %s символов', len(text))
                return text or 'Извините, нейросеть не сформировала ответ. Попробуйте позже.'

            except Exception as e:
                err_str = str(e).lower()
                logger.warning('Scitely (model=%s): %s', model, e)
                if '429' in err_str or 'rate' in err_str:
                    continue
                if '401' in err_str or 'unauthorized' in err_str:
                    return (
                        'Ошибка авторизации Scitely (401). Проверьте SCITELY_API_KEY: '
                        'получить ключ: https://console.scitely.com'
                    )
                return f'Ошибка Scitely API: {str(e)[:200]}. Попробуйте позже.'

        return 'Все модели временно перегружены. Попробуйте через пару минут.'


# Синглтон, инициализируется при первом импорте
gemini_client = GeminiClient()
