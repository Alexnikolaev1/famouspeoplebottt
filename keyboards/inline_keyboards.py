from aiogram.utils.keyboard import InlineKeyboardBuilder

from classes.resource import Button, Buttons
from .callback_data import CelebrityData, QuizData


def ikb_celebrity():
    keyboard = InlineKeyboardBuilder()
    buttons = Buttons()
    for button in buttons:
        keyboard.button(
            text=f'📖 {button.name}',
            callback_data=CelebrityData(
                button='select_celebrity',
                file_name=button.callback,
            ),
        )
    keyboard.adjust(1)
    return keyboard.as_markup()


# (emoji, отображаемое название, topic_id для промпта, short_key для callback_data ≤64 байт)
QUIZ_TOPICS = [
    ('📜', 'Догматическое богословие', 'quiz_dogmatic', 'dogmatic'),
    ('📖', 'Священное Предание и Писание', 'quiz_tradition', 'tradition'),
    ('⚖️', 'Каноническое право', 'quiz_canon', 'canon'),
    ('🕯', 'Богослужение и Таинства', 'quiz_liturgy', 'liturgy'),
    ('✝️', 'Аскетика и Нравственное богословие', 'quiz_ascetic', 'ascetic'),
]

TOPIC_DISPLAY_NAMES = {short: name for _, name, _, short in QUIZ_TOPICS}


def ikb_quiz_select_topic():
    keyboard = InlineKeyboardBuilder()
    for emoji, name, topic_id, short in QUIZ_TOPICS:
        keyboard.button(
            text=f'{emoji} {name}',
            callback_data=QuizData(
                button='select_topic',
                topic=topic_id,
                topic_name=short,
            )
        )
    keyboard.adjust(1)
    return keyboard.as_markup()


def ikb_quiz_next(current_topic: QuizData):
    keyboard = InlineKeyboardBuilder()
    buttons = [
        ('➡️', Button('Дальше', 'next_question')),
        ('🔄', Button('Сменить тему', 'change_topic')),
        ('🏠', Button('Завершить', 'finish_quiz')),
    ]
    for emoji, button in buttons:
        keyboard.button(
            text=f'{emoji} {button.name}',
            callback_data=QuizData(
                button=button.callback,
                topic=current_topic.topic,
                topic_name=current_topic.topic_name
            )
        )
    keyboard.adjust(2, 1)
    return keyboard.as_markup()
