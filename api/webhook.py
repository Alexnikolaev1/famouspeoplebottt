"""
Serverless entry point для Vercel.

Telegram отправляет POST-запрос с Update на /api/webhook.
Функция парсит Update, передаёт его в aiogram Dispatcher и возвращает 200 OK.

FSM-состояния хранятся в Redis Cloud (или в MemoryStorage при локальном запуске).
"""

import asyncio
import json
import logging
import os
import sys

# Корень проекта — на один уровень выше api/
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

from http.server import BaseHTTPRequestHandler

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Update

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN', '')
UPSTASH_REDIS_URL = os.getenv('UPSTASH_REDIS_URL', '')

if not BOT_TOKEN:
    raise RuntimeError('BOT_TOKEN не задан в переменных окружения Vercel')

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
)

if UPSTASH_REDIS_URL:
    from aiogram.fsm.storage.redis import RedisStorage
    storage = RedisStorage.from_url(UPSTASH_REDIS_URL)
    logger.info('FSM storage: Redis')
else:
    from aiogram.fsm.storage.memory import MemoryStorage
    storage = MemoryStorage()
    logger.warning('FSM storage: MemoryStorage (состояния не сохраняются между вызовами!)')

dp = Dispatcher(storage=storage)

from handlers import routers  # noqa: E402
dp.include_routers(*routers)


async def _process_update(body: bytes) -> None:
    """Обрабатывает Update от Telegram."""
    try:
        update_data = json.loads(body)
        update = Update.model_validate(update_data, context={'bot': bot})
        await dp.feed_update(bot, update)
        logger.info('Update обработан успешно')
    except Exception as e:
        logger.exception('Ошибка при обработке update: %s', e)
        raise


class handler(BaseHTTPRequestHandler):
    """Vercel serverless handler — принимает webhook от Telegram."""

    def do_POST(self):
        """Обрабатывает POST-запрос от Telegram."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                logger.warning('Пустое тело запроса')
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"error": "Empty body"}')
                return
            
            body = self.rfile.read(content_length)
            logger.info('Получен update, размер: %d байт', len(body))
            
            # Создаём event loop для каждого запроса (serverless окружение)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(_process_update(body))
            finally:
                loop.close()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"ok": true}')
            logger.info('Ответ отправлен успешно')
        except Exception as e:
            logger.exception('Ошибка в do_POST: %s', e)
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)[:200]}).encode('utf-8'))

    def do_GET(self):
        """Health check endpoint."""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"status": "ok", "message": "Bot webhook is active"}')

    def log_message(self, format, *args):
        """Перенаправляет логи в logger вместо stderr."""
        logger.info(format % args)
