"""
Vercel Serverless Function для Famous People Bot
FastAPI app для обработки webhook от Telegram
"""

import asyncio
import json
import logging
import os

from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Update

from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
)
logger = logging.getLogger(__name__)

load_dotenv()

import misc
from handlers import routers

BOT_TOKEN = os.getenv('BOT_TOKEN', '').strip()
UPSTASH_REDIS_URL = os.getenv('UPSTASH_REDIS_URL', '').strip()

if not BOT_TOKEN:
    raise RuntimeError('BOT_TOKEN не задан в переменных окружения Vercel')

# Инициализация FastAPI app
app = FastAPI()

# Инициализация Bot и Dispatcher
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
dp.startup.register(misc.on_start)
dp.shutdown.register(misc.on_shutdown)
dp.include_routers(*routers)


async def _process_webhook_update(update: dict) -> None:
    """Обработка одного апдейта (вызов диспетчера)."""
    update_id = update.get("update_id", "N/A")
    telegram_update = Update(**update)
    try:
        await asyncio.wait_for(dp.feed_update(bot, telegram_update), timeout=25.0)
        logger.info(f"Update {update_id} processed successfully")
    except asyncio.TimeoutError:
        logger.warning(f"Update {update_id} processing timeout (25s)")
    except Exception as e:
        logger.exception(f"Error processing update {update_id}: {type(e).__name__}: {str(e)}")


@app.get("/")
async def root():
    """Корневой endpoint."""
    return {"status": "ok", "message": "Famous People Bot is running"}


@app.get("/api/webhook")
async def telegram_webhook_get():
    """GET для прогрева (cron пингует этот URL). Отвечает 200 в любом случае."""
    return {"ok": True}


@app.post("/api/webhook")
async def telegram_webhook(request: Request):
    """Обработчик вебхуков от Telegram"""
    logger.info("=== POST /api/webhook received ===")
    try:
        # Читаем JSON напрямую
        update = await request.json()
        update_id = update.get('update_id', 'N/A')
        
        # Определяем тип обновления для логирования
        update_type = "unknown"
        if "message" in update:
            update_type = "message"
            msg_text = update.get("message", {}).get("text", "")
            logger.info(f"Webhook received: update_id={update_id}, type={update_type}, text={msg_text[:50]}")
        elif "callback_query" in update:
            update_type = "callback_query"
            callback_data = update.get("callback_query", {}).get("data", "")
            logger.info(f"Webhook received: update_id={update_id}, type={update_type}, data={callback_data}")
        else:
            logger.info(f"Webhook received: update_id={update_id}, type={update_type}, keys={list(update.keys())}")
        
        await _process_webhook_update(update)
        return {"ok": True}
    except ValueError as e:
        # Ошибки валидации данных от Telegram
        logger.error(f"Webhook validation error: {str(e)}", exc_info=True)
        return {"ok": False, "error": "invalid_update"}, 400
    except RuntimeError as e:
        # Ошибки конфигурации (нет токена и т.д.)
        logger.error(f"Webhook config error: {str(e)}", exc_info=True)
        return {"ok": False, "error": "configuration_error"}, 500
    except Exception as e:
        # Все остальные ошибки
        logger.exception(f"Webhook unexpected error: {type(e).__name__}: {str(e)}")
        return {"ok": False, "error": "internal_error"}, 500
