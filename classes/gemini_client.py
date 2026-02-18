"""
LLM клиент для Famous People Bot.
Использует Google Gemini API (generativelanguage.googleapis.com).
Бесплатный тариф: 250K TPM, 1000 запросов/день. Без карты.
Документация: https://ai.google.dev/gemini-api/docs
"""

import asyncio
import json
import logging
import os
import re

import httpx

from .enums import MessageRole, Extensions, ResourcePath

logger = logging.getLogger(__name__)


def _normalize_base_url(url: str) -> str:
    u = (url or "").strip().rstrip("/")
    if not u:
        return ""
    if not re.match(r"^https?://", u, flags=re.IGNORECASE):
        u = "https://" + u
    return u


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
    """Клиент для работы с Gemini API (REST)."""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        api_key: str | None = None,
        worker_url: str | None = None,
        model: str = 'gemini-2.0-flash',
    ):
        # Поддержка нескольких ключей: GEMINI_API_KEYS или GEMINI_API_KEY (через запятую)
        keys_str = (
            os.getenv('GEMINI_API_KEYS', '').strip()
            or (api_key or os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY') or '').strip()
        )
        self.api_keys = [k.strip() for k in keys_str.split(',') if k.strip()]
        self.api_key = self.api_keys[0] if self.api_keys else ''
        self.base_url = _normalize_base_url(
            worker_url
            or os.getenv('GEMINI_WORKER_URL')
            or os.getenv('CLOUDFLARE_WORKER_URL')
            or 'https://generativelanguage.googleapis.com'
        )
        self.model = (model or os.getenv('GEMINI_MODEL') or 'gemini-2.0-flash').strip()

    # Сколько пар user+assistant оставлять в контексте (экономия токенов)
    MAX_HISTORY_PAIRS = int(os.getenv('GEMINI_MAX_HISTORY_PAIRS', '3'))

    def _build_payload(self, messages: GeminiMessage, max_tokens: int = 4096) -> dict:
        """Преобразует GeminiMessage в формат REST API Gemini."""
        system_instruction = None
        contents = []

        # Ограничиваем историю — оставляем system + последние N пар (экономия токенов)
        msg_list = messages.message_list
        dialogue = []
        for msg in msg_list:
            role = msg['role']
            content = msg['content']
            if role == MessageRole.SYSTEM.value:
                system_instruction = content
            else:
                dialogue.append(msg)

        # Берём только последние N пар user+assistant
        keep = self.MAX_HISTORY_PAIRS * 2
        if len(dialogue) > keep:
            dialogue = dialogue[-keep:]
        for msg in dialogue:
            role = msg['role']
            content = msg['content']
            if role == MessageRole.USER.value:
                contents.append({'role': 'user', 'parts': [{'text': content}]})
            elif role == MessageRole.ASSISTANT.value:
                contents.append({'role': 'model', 'parts': [{'text': content}]})

        if not contents:
            contents = [{'parts': [{'text': 'Выполни инструкцию.'}]}]

        payload = {
            'contents': contents,
            'generationConfig': {
                'maxOutputTokens': max_tokens,
                'temperature': 0.7,
                'topP': 0.95,
            },
            'safetySettings': [
                {'category': 'HARM_CATEGORY_HARASSMENT', 'threshold': 'BLOCK_NONE'},
                {'category': 'HARM_CATEGORY_HATE_SPEECH', 'threshold': 'BLOCK_NONE'},
                {'category': 'HARM_CATEGORY_SEXUALLY_EXPLICIT', 'threshold': 'BLOCK_NONE'},
                {'category': 'HARM_CATEGORY_DANGEROUS_CONTENT', 'threshold': 'BLOCK_NONE'},
            ],
        }

        if system_instruction:
            payload['systemInstruction'] = {'parts': [{'text': system_instruction}]}

        return payload

    async def request(self, messages: GeminiMessage, max_tokens: int = 4096) -> str:
        """Отправляет запрос к Gemini API и возвращает текст ответа."""
        if not self.api_keys:
            logger.error('GEMINI_API_KEY / GEMINI_API_KEYS не задан')
            return 'Извините, не настроен API ключ. Обратитесь к администратору.'

        if not self.base_url:
            logger.error('Gemini API URL не задан')
            return 'Извините, не настроен URL Gemini API. Обратитесь к администратору.'

        url = f"{self.base_url}/v1beta/models/{self.model}:generateContent"
        max_tok = int(os.getenv('GEMINI_MAX_OUTPUT_TOKENS', str(max_tokens)))
        payload = self._build_payload(messages, max_tokens=max_tok)
        retries = 3
        backoffs = [0.7, 1.5, 3.0]
        last_err: Exception | None = None

        # Round-robin: распределяем запросы по ключам
        keys_to_try = self.api_keys
        if len(self.api_keys) > 1:
            idx = getattr(GeminiClient, '_rr_idx', 0) % len(self.api_keys)
            GeminiClient._rr_idx = idx + 1
            keys_to_try = self.api_keys[idx:] + self.api_keys[:idx]

        # Пробуем каждый ключ (при 429 — следующий)
        for key_idx, api_key in enumerate(keys_to_try):
            headers = {
                'Content-Type': 'application/json',
                'x-goog-api-key': api_key,
            }
            key_label = f'ключ {key_idx + 1}/{len(keys_to_try)}' if len(keys_to_try) > 1 else 'ключ'

            for attempt in range(retries):
                try:
                    logger.info('Gemini запрос: %s (%s)', url, key_label)
                    async with httpx.AsyncClient(timeout=60.0) as client:
                        response = await client.post(url, json=payload, headers=headers)

                    logger.debug(
                        'Gemini API response: status=%s, length=%s',
                        response.status_code,
                        len(response.content),
                    )

                    if response.status_code == 429:
                        logger.warning('429 rate limit на %s', key_label)
                        break  # переходим к следующему ключу

                    if response.status_code in {500, 502, 503, 504}:
                        if attempt < retries - 1:
                            await asyncio.sleep(backoffs[attempt])
                            continue
                        raise httpx.HTTPStatusError(
                            'retryable',
                            request=response.request,
                            response=response,
                        )

                    response.raise_for_status()

                    response_text = response.content.decode('utf-8', errors='replace')
                    if not response_text or not response_text.strip():
                        logger.error('Пустой ответ от Gemini API')
                        return 'Извините, нейросеть вернула пустой ответ. Попробуйте позже.'

                    data = json.loads(response_text)

                    if 'candidates' not in data or not data.get('candidates'):
                        logger.error('Неожиданная структура ответа: %s', list(data.keys()))
                        return 'Извините, неожиданный формат ответа от нейросети. Попробуйте позже.'

                    candidate = data['candidates'][0]
                    finish_reason = candidate.get('finishReason', '')

                    if finish_reason == 'MAX_TOKENS':
                        logger.warning('Ответ обрезан: MAX_TOKENS')

                    if 'content' not in candidate or 'parts' not in candidate['content']:
                        logger.error('Нет content/parts в candidate')
                        return 'Извините, ошибка формата ответа. Попробуйте позже.'

                    parts = candidate['content']['parts']
                    if not parts or 'text' not in parts[0]:
                        logger.error('Нет text в parts')
                        return 'Извините, ошибка формата ответа. Попробуйте позже.'

                    text = parts[0]['text']
                    logger.info('Gemini ответ: %s символов', len(text))
                    return text or ''

                except httpx.HTTPStatusError as e:
                    last_err = e
                    body = ''
                    try:
                        body = (e.response.text or '')[:1000]
                    except Exception:
                        pass

                    logger.warning('Gemini API ошибка: %s - %s', e.response.status_code, body[:200])

                    if e.response.status_code == 429:
                        break  # следующий ключ

                    if 'User location is not supported' in body:
                        return (
                            'Доступ к Gemini API ограничен в вашем регионе. '
                            'Настройте GEMINI_WORKER_URL (см. CLOUDFLARE_SETUP.md).'
                        )

                    if attempt < retries - 1:
                        await asyncio.sleep(backoffs[attempt])
                        continue

                    return f'Ошибка Gemini API: {e.response.status_code}. Попробуйте позже.'

                except json.JSONDecodeError as e:
                    last_err = e
                    logger.exception('Ошибка парсинга JSON от Gemini: %s', e)
                    return 'Извините, ошибка при обработке ответа нейросети. Попробуйте позже.'

                except Exception as e:
                    last_err = e
                    logger.exception('Неожиданная ошибка Gemini: %s', e)
                    return 'Извините, произошла ошибка. Попробуйте позже.'

        return (
            'Попробуйте подождать пару минут. '
            'А если запросов было много — сделайте попытку на следующий день.'
        )


gemini_client = GeminiClient()
