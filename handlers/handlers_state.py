from aiogram.fsm.state import State, StatesGroup


class GeminiRequests(StatesGroup):
    wait_for_request = State()


class CelebrityTalk(StatesGroup):
    wait_for_answer = State()


class Quiz(StatesGroup):
    wait_for_answer = State()
