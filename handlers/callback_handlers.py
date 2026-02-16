from aiogram import Bot, Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from classes import gemini_client
from classes.resource import Resource, Button
from classes.gemini_client import GeminiMessage
from classes.enums import MessageRole
from keyboards.callback_data import CelebrityData, QuizData
from keyboards.inline_keyboards import ikb_quiz_select_topic, TOPIC_DISPLAY_NAMES
from keyboards import kb_end_talk
from .handlers_state import CelebrityTalk, Quiz
from .command import com_start, _send_resource
from misc import safe_answer

callback_router = Router()


@callback_router.callback_query(CelebrityData.filter(F.button == 'select_celebrity'))
async def celebrity_callbacks(callback: CallbackQuery, callback_data: CelebrityData, bot: Bot, state: FSMContext):
    try:
        button_name = Button(callback_data.file_name).name
    except FileNotFoundError:
        await callback.answer(text='Ошибка загрузки данных.', show_alert=True)
        return

    await callback.answer(text=f'С тобой говорит {button_name}')
    try:
        resource = Resource(callback_data.file_name)
        photo = resource.photo
        markup = kb_end_talk()
        if photo:
            await callback.message.answer_photo(
                photo=photo,
                caption=f'С тобой говорит {button_name}. Задайте свой вопрос:',
                reply_markup=markup,
            )
        else:
            await callback.message.answer(
                text=f'С тобой говорит {button_name}. Задайте свой вопрос:',
                reply_markup=markup,
            )
        request_message = GeminiMessage(callback_data.file_name)
        await state.set_state(CelebrityTalk.wait_for_answer)
        await state.set_data({
            'messages': request_message.to_dict(),
            'resource_name': callback_data.file_name,
        })
    except (FileNotFoundError, ValueError):
        await callback.message.answer('Извините, произошла ошибка. Попробуйте другую персоналию.')
    except Exception as e:
        await callback.message.answer(f'Ошибка: {str(e)[:200]}')


@callback_router.callback_query(QuizData.filter(F.button == 'select_topic'))
async def quiz_select_topic_handler(callback: CallbackQuery, callback_data: QuizData, state: FSMContext):
    topic_label = TOPIC_DISPLAY_NAMES.get(callback_data.topic_name, callback_data.topic_name)
    await callback.answer(text=f'Тема: {topic_label}')
    try:
        request_message = GeminiMessage('quiz')
        request_message.update(MessageRole.USER, callback_data.topic)
        response = await gemini_client.request(request_message)
        resource = Resource('quiz')
        await _send_resource(callback.message, resource, caption=response)
        await state.set_state(Quiz.wait_for_answer)
        await state.set_data({
            'messages': request_message.to_dict(),
            'resource_name': 'quiz',
            'score': 0,
            'callback': {
                'button': callback_data.button,
                'topic': callback_data.topic,
                'topic_name': callback_data.topic_name,
            },
        })
    except Exception as e:
        await callback.message.answer(
            f'Ошибка: {str(e)[:200]}. Проверьте GEMINI_WORKER_URL и сеть.'
        )


@callback_router.callback_query(QuizData.filter(F.button == 'next_question'))
async def quiz_next_question(callback: CallbackQuery, callback_data: QuizData, state: FSMContext):
    data: dict = await state.get_data()
    if 'messages' not in data or 'callback' not in data:
        await callback.answer(text='Сессия викторины устарела. Начните заново.', show_alert=True)
        await state.clear()
        return
    cb = data['callback']
    topic_label = TOPIC_DISPLAY_NAMES.get(cb['topic_name'], cb['topic_name'])
    await callback.answer(text=f'Продолжаем: {topic_label}')
    try:
        messages = GeminiMessage.from_dict(data['messages'])
        messages.update(MessageRole.USER, 'quiz_more')
        response = await gemini_client.request(messages)
        messages.update(MessageRole.ASSISTANT, response)
        resource_name = data.get('resource_name')
        photo = Resource(resource_name).photo if resource_name else None
        await safe_answer(callback.message, response, photo=photo)
        await state.update_data({'messages': messages.to_dict()})
    except Exception as e:
        await callback.message.answer(f'Ошибка: {str(e)[:200]}')


@callback_router.callback_query(QuizData.filter(F.button == 'change_topic'))
async def quiz_change_topic(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer(text='Выберите новую тему')
    try:
        resource = Resource('quiz')
        await _send_resource(callback.message, resource, reply_markup=ikb_quiz_select_topic())
    except Exception as e:
        await callback.message.answer(f'Ошибка: {str(e)[:200]}')


@callback_router.callback_query(QuizData.filter(F.button == 'finish_quiz'))
async def quiz_finish(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer(text='Викторина завершена')
    try:
        await com_start(callback.message)
    except Exception as e:
        await callback.message.answer(f'Ошибка: {str(e)[:200]}')
