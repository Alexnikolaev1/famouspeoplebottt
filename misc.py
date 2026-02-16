from aiogram import Bot
from aiogram.types import Message
from aiogram.enums import ChatAction
from datetime import datetime

CAPTION_LIMIT = 1024
TEXT_LIMIT = 4096


async def on_start():
    time_now = datetime.now().strftime('%H:%M:%S %d/%m/%Y')
    print(f'Бот запущен: {time_now}')


async def on_shutdown():
    time_now = datetime.now().strftime('%H:%M:%S %d/%m/%Y')
    print(f'Бот остановлен: {time_now}')


async def bot_thinking(message: Message):
    await message.bot.send_chat_action(
        chat_id=message.from_user.id,
        action=ChatAction.TYPING,
    )


async def safe_answer(message: Message, text: str, photo=None, **kwargs):
    """Отправляет ответ, учитывая лимиты Telegram на длину caption (1024) и text (4096)."""
    if photo:
        if len(text) > CAPTION_LIMIT:
            # Caption слишком длинный — фото отдельно, текст отдельно
            await message.answer_photo(photo=photo)
            if len(text) > TEXT_LIMIT:
                text = text[:TEXT_LIMIT - 3] + '...'
            await message.answer(text=text, **kwargs)
        else:
            await message.answer_photo(photo=photo, caption=text, **kwargs)
    else:
        if len(text) > TEXT_LIMIT:
            text = text[:TEXT_LIMIT - 3] + '...'
        await message.answer(text=text, **kwargs)
