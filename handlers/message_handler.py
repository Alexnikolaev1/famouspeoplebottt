from aiogram import Bot, Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from .handlers_state import CelebrityTalk, GeminiRequests, Quiz

from classes import gemini_client
from classes.resource import Resource
from classes.gemini_client import GeminiMessage
from classes.enums import MessageRole
from keyboards import kb_end_talk, ikb_quiz_next
from keyboards.callback_data import QuizData

from .command import com_start, _send_resource
from misc import bot_thinking, safe_answer

message_router = Router()

# Все варианты текста кнопок «домой» — для надёжного перехвата
_EXIT_TEXTS = {'🏠 Закончить диалог', '🏠 Главное меню', 'Закончить диалог', 'Закончить'}


@message_router.message(CelebrityTalk.wait_for_answer, F.text.in_(_EXIT_TEXTS))
async def end_talk_handler(message: Message, state: FSMContext):
    await state.clear()
    await com_start(message)


@message_router.message(GeminiRequests.wait_for_request, F.text.in_(_EXIT_TEXTS))
async def end_ask_handler(message: Message, state: FSMContext):
    await state.clear()
    await com_start(message)


@message_router.message(Quiz.wait_for_answer, F.text.in_(_EXIT_TEXTS))
async def end_quiz_handler(message: Message, state: FSMContext):
    await state.clear()
    await com_start(message)


@message_router.message(GeminiRequests.wait_for_request, F.text)
async def wait_for_ask_handler(message: Message, state: FSMContext):
    await bot_thinking(message)
    gemini_message = GeminiMessage('ask')
    gemini_message.update(MessageRole.USER, message.text)
    gemini_response = await gemini_client.request(gemini_message)
    resource = Resource('ask')
    await _send_resource(message, resource, caption=gemini_response)
    await state.clear()


@message_router.message(CelebrityTalk.wait_for_answer, F.text)
async def talk_handler(message: Message, state: FSMContext):
    await bot_thinking(message)
    data: dict = await state.get_data()
    if 'messages' not in data:
        await message.answer('Сессия диалога устарела. Начните заново через /speak')
        await state.clear()
        return
    messages = GeminiMessage.from_dict(data['messages'])
    messages.update(MessageRole.USER, message.text)
    response = await gemini_client.request(messages)
    markup = kb_end_talk()
    resource_name = data.get('resource_name')
    photo = Resource(resource_name).photo if resource_name else None
    await safe_answer(message, response, photo=photo, reply_markup=markup)
    messages.update(MessageRole.ASSISTANT, response)
    await state.update_data({'messages': messages.to_dict()})


@message_router.message(Quiz.wait_for_answer, F.text)
async def quiz_answer(message: Message, state: FSMContext):
    data: dict = await state.get_data()
    if 'messages' not in data or 'callback' not in data:
        await message.answer('Сессия викторины устарела. Начните заново через /check')
        await state.clear()
        return
    messages = GeminiMessage.from_dict(data['messages'])
    messages.update(MessageRole.USER, message.text)
    response = await gemini_client.request(messages)
    score = data.get('score', 0)
    if response == 'Правильно!':
        score += 1
    messages.update(MessageRole.ASSISTANT, response)
    cb = data['callback']
    quiz_data = QuizData(button=cb['button'], topic=cb['topic'], topic_name=cb['topic_name'])
    text = f'Ваш счет: {score}\n{response}'
    resource_name = data.get('resource_name')
    photo = Resource(resource_name).photo if resource_name else None
    await safe_answer(message, text, photo=photo, reply_markup=ikb_quiz_next(quiz_data))
    await state.update_data({'messages': messages.to_dict(), 'score': score})


@message_router.message(GeminiRequests.wait_for_request)
@message_router.message(CelebrityTalk.wait_for_answer)
@message_router.message(Quiz.wait_for_answer)
async def non_text_message_handler(message: Message):
    await message.answer('Пожалуйста, отправьте текстовое сообщение.')
