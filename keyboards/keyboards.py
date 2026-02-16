from aiogram.utils.keyboard import ReplyKeyboardBuilder


def kb_main_menu():
    """Главное меню — 2×2 сетка с красивыми кнопками."""
    keyboard = ReplyKeyboardBuilder()
    keyboard.button(text='🌟 Интересный факт')
    keyboard.button(text='❓ Задать вопрос')
    keyboard.button(text='🗣 Философы')
    keyboard.button(text='🧠 Викторина')
    keyboard.adjust(2)
    return keyboard.as_markup(
        resize_keyboard=True,
        input_field_placeholder='Выберите действие...',
    )


def kb_fact():
    """Кнопки после получения факта."""
    keyboard = ReplyKeyboardBuilder()
    keyboard.button(text='🔄 Ещё факт')
    keyboard.button(text='🏠 Главное меню')
    keyboard.adjust(2)
    return keyboard.as_markup(
        resize_keyboard=True,
        input_field_placeholder='Хотите ещё?',
    )


def kb_back():
    """Одна кнопка возврата в меню."""
    keyboard = ReplyKeyboardBuilder()
    keyboard.button(text='🏠 Главное меню')
    keyboard.adjust(1)
    return keyboard.as_markup(
        resize_keyboard=True,
        input_field_placeholder='Напишите свой вопрос...',
    )


def kb_end_talk():
    """Кнопка завершения диалога с философом."""
    keyboard = ReplyKeyboardBuilder()
    keyboard.button(text='🏠 Закончить диалог')
    keyboard.adjust(1)
    return keyboard.as_markup(
        resize_keyboard=True,
        input_field_placeholder='Задайте свой вопрос...',
    )
