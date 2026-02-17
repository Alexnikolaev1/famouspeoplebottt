"""
LLM клиент для Famous People Bot.
Использует Qwen 3.5 Plus через Alibaba DashScope (OpenAI-совместимый API).
"""

import asyncio
import logging
import os

from openai import AsyncOpenAI

from .enums import MessageRole, Extensions, ResourcePath

logger = logging.getLogger(__name__)

QWEN_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
QWEN_MODEL = "qwen3.5-plus"


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
    """Клиент для работы с Qwen 3.5 Plus (DashScope, OpenAI-совместимый API)."""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        api_key: str | None = None,
        model: str = QWEN_MODEL,
    ):
        self.api_key = (api_key or os.getenv('DASHSCOPE_API_KEY') or '').strip()
        self.model = model
        self._client: AsyncOpenAI | None = None

    def _get_client(self) -> AsyncOpenAI:
        """Ленивая инициализация клиента."""
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=QWEN_BASE_URL,
            )
        return self._client

    def _to_openai_messages(self, messages: GeminiMessage) -> list[dict[str, str]]:
        """Преобразует GeminiMessage в формат OpenAI chat (role + content)."""
        result = []
        for msg in messages.message_list:
            role = msg['role']
            content = msg['content']
            # Qwen/OpenAI использует те же роли: system, user, assistant
            result.append({'role': role, 'content': content})
        if not result:
            result = [{'role': 'user', 'content': 'Выполни инструкцию.'}]
        return result

    async def request(self, messages: GeminiMessage, max_tokens: int = 8192) -> str:
        """Отправляет запрос к Qwen API и возвращает текст ответа."""
        if not self.api_key:
            logger.error('DASHSCOPE_API_KEY не задан')
            return 'Извините, не настроен API ключ. Обратитесь к администратору.'

        retries = 3
        backoffs = [0.7, 1.5, 3.0]
        last_err: Exception | None = None

        for attempt in range(retries):
            try:
                client = self._get_client()
                openai_messages = self._to_openai_messages(messages)

                logger.info('Qwen запрос: model=%s', self.model)

                response = await client.chat.completions.create(
                    model=self.model,
                    messages=openai_messages,
                    max_tokens=max_tokens,
                    temperature=0.7,
                    extra_body={"enable_thinking": True},
                )

                if not response.choices:
                    logger.error('Пустой ответ от Qwen API')
                    return 'Извините, нейросеть вернула пустой ответ. Попробуйте позже.'

                msg = response.choices[0].message
                text = (msg.content or '').strip()
                logger.info('Qwen ответ: %s символов', len(text))
                return text or 'Извините, нейросеть не сформировала ответ. Попробуйте позже.'

            except Exception as e:
                last_err = e
                err_str = str(e).lower()

                if '429' in err_str or 'rate' in err_str:
                    if attempt < retries - 1:
                        await asyncio.sleep(60)
                        continue
                    return (
                        'Попробуйте подождать пару минут. '
                        'А если запросов было много — сделайте попытку на следующий день.'
                    )

                if attempt < retries - 1:
                    await asyncio.sleep(backoffs[attempt])
                    continue

                logger.exception('Ошибка Qwen API: %s', e)
                return f'Ошибка Qwen API. Попробуйте позже.'

        return 'Извините, технические неполадки. Попробуйте позже.' if last_err else ''


# Синглтон, инициализируется при первом импорте
gemini_client = GeminiClient()
