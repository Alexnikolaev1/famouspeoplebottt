from aiogram import Router

from .command import command_router
from .callback_handlers import callback_router
from .message_handler import message_router

routers = [
    message_router,
    command_router,
    callback_router,
]

__all__ = [
    'routers',
]
