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

from http.server import BaseHTTPRequestHandler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
)
logger = logging.getLogger(__name__)
logger.info('=== Модуль webhook.py загружен ===')

# Корень проекта — на один уровень выше api/
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

# Ленивая инициализация — создаём bot и dp при первом запросе
_bot = None
_dp = None


def _init_bot():
    """Инициализирует bot и dispatcher при первом запросе."""
    global _bot, _dp
    if _bot is not None:
        return _bot, _dp
    
    logger.info('Инициализация bot и dispatcher...')
    
    try:
        from aiogram import Bot, Dispatcher
        from aiogram.enums import ParseMode
        from aiogram.client.default import DefaultBotProperties
        from aiogram.types import Update
        
        BOT_TOKEN = os.getenv('BOT_TOKEN', '')
        UPSTASH_REDIS_URL = os.getenv('UPSTASH_REDIS_URL', '')
        
        if not BOT_TOKEN:
            raise RuntimeError('BOT_TOKEN не задан в переменных окружения Vercel')
        
        _bot = Bot(
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
        
        _dp = Dispatcher(storage=storage)
        
        from handlers import routers  # noqa: E402
        _dp.include_routers(*routers)
        
        logger.info('Bot и dispatcher инициализированы успешно')
    except Exception as e:
        logger.exception('Ошибка при инициализации: %s', e)
        raise
    
    return _bot, _dp


async def _process_update(body: bytes) -> None:
    """Обрабатывает Update от Telegram."""
    try:
        bot, dp = _init_bot()
        from aiogram.types import Update
        
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
            logger.info('=== POST запрос получен ===')
            logger.info('Path: %s', self.path)
            
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
            error_msg = json.dumps({'error': str(e)[:200]}).encode('utf-8')
            self.wfile.write(error_msg)

    def do_GET(self):
        """Health check endpoint."""
        try:
            logger.info('=== GET запрос получен ===')
            logger.info('Path: %s', self.path)
            
            # Пробуем инициализировать bot для проверки
            try:
                bot, dp = _init_bot()
                bot_status = 'initialized'
            except Exception as e:
                bot_status = f'error: {str(e)[:100]}'
                logger.exception('Ошибка при инициализации bot в GET: %s', e)
            
            response_data = {
                'status': 'ok',
                'message': 'Bot webhook is active',
                'bot_status': bot_status,
                'path': self.path
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
            logger.info('GET ответ отправлен: %s', response_data)
        except Exception as e:
            logger.exception('Ошибка в do_GET: %s', e)
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            error_msg = json.dumps({'error': str(e)[:200]}).encode('utf-8')
            self.wfile.write(error_msg)

    def log_message(self, format, *args):
        """Перенаправляет логи в logger вместо stderr."""
        logger.info(format % args)
