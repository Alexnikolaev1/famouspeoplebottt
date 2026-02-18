from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from classes import gemini_client
from classes.resource import Resource
from classes.gemini_client import GeminiMessage
from classes.enums import MessageRole
from .handlers_state import GeminiRequests
from misc import bot_thinking

from keyboards import kb_main_menu, kb_fact, kb_back, ikb_celebrity, ikb_quiz_select_topic

command_router = Router()


CAPTION_LIMIT = 1024
TEXT_LIMIT = 4096


async def _send_resource(message: Message, resource: Resource, caption: str | None = None, **extra):
    """Отправляет сообщение с фото или только текст, если изображения нет.

    Если caption длиннее лимита Telegram (1024 для фото), отправляет фото
    отдельно, а текст — следующим сообщением.
    """
    use_photo, kwargs = resource.as_message_kwargs()
    if caption is not None:
        kwargs['caption' if use_photo else 'text'] = caption
    kwargs.update(extra)

    if use_photo:
        cap = kwargs.get('caption', '')
        if len(cap) > CAPTION_LIMIT:
            photo = kwargs.pop('photo')
            reply_markup = kwargs.pop('reply_markup', None)
            kwargs.pop('caption', None)
            await message.answer_photo(photo=photo)
            text = cap[:TEXT_LIMIT - 3] + '...' if len(cap) > TEXT_LIMIT else cap
            await message.answer(text=text, reply_markup=reply_markup)
        else:
            await message.answer_photo(**kwargs)
    else:
        text = kwargs.get('text', '')
        if len(text) > TEXT_LIMIT:
            kwargs['text'] = text[:TEXT_LIMIT - 3] + '...'
        await message.answer(**kwargs)


@command_router.message(F.text == '🏠 Главное меню')
@command_router.message(Command('start'))
async def com_start(message: Message):
    resource = Resource('main')
    await _send_resource(message, resource, reply_markup=kb_main_menu())


@command_router.message(F.text == '🔄 Ещё факт')
@command_router.message(F.text == '🌟 Интересный факт')
@command_router.message(Command('fact'))
async def com_fact(message: Message):
    await bot_thinking(message)
    resource = Resource('random')
    gemini_message = GeminiMessage('random')
    gemini_message.update(MessageRole.USER, 'Расскажи один интересный православный факт.')
    msg_text = await gemini_client.request(gemini_message)
    await _send_resource(message, resource, caption=msg_text, reply_markup=kb_fact())


@command_router.message(F.text == '❓ Задать вопрос')
@command_router.message(Command('tell'))
async def com_tell(message: Message, state: FSMContext):
    await state.set_state(GeminiRequests.wait_for_request)
    resource = Resource('ask')
    await _send_resource(message, resource, reply_markup=kb_back())


@command_router.message(F.text == '🗣 Философы')
@command_router.message(Command('speak'))
async def com_speak(message: Message):
    await bot_thinking(message)
    resource = Resource('talk')
    await _send_resource(message, resource, reply_markup=ikb_celebrity())


@command_router.message(F.text == '🧠 Викторина')
@command_router.message(Command('check'))
async def com_check(message: Message):
    await bot_thinking(message)
    resource = Resource('quiz')
    await _send_resource(message, resource, reply_markup=ikb_quiz_select_topic())
