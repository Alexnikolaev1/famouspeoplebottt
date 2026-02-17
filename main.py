from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer

import asyncio
import logging
import os

from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
)

load_dotenv()

import misc

from handlers import routers

BOT_TOKEN = os.getenv('BOT_TOKEN')
DASHSCOPE_API_KEY = os.getenv('DASHSCOPE_API_KEY')
PROXY = os.getenv('PROXY') or os.getenv('HTTP_PROXY') or os.getenv('HTTPS_PROXY')
TELEGRAM_API_URL = os.getenv('TELEGRAM_API_URL')

if not BOT_TOKEN:
    raise SystemExit('Ошибка: не задан BOT_TOKEN в переменных окружения (.env)')
if not DASHSCOPE_API_KEY:
    raise SystemExit('Ошибка: не задан DASHSCOPE_API_KEY в переменных окружения (.env)')

bot_kwargs = dict(
    token=BOT_TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.MARKDOWN,
    ),
)

if TELEGRAM_API_URL or PROXY:
    session_kwargs = {
        # Увеличенный таймаут — помогает при медленном соединении через воркер/VPN
        'timeout': 120.0,
    }
    if TELEGRAM_API_URL:
        session_kwargs['api'] = TelegramAPIServer.from_base(TELEGRAM_API_URL.rstrip('/'))
    if PROXY:
        session_kwargs['proxy'] = PROXY
    bot_kwargs['session'] = AiohttpSession(**session_kwargs)

bot = Bot(**bot_kwargs)
dp = Dispatcher()


async def start_bot():
    dp.startup.register(misc.on_start)
    dp.shutdown.register(misc.on_shutdown)
    dp.include_routers(*routers)
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        pass
