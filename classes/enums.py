import os
from pathlib import Path
from enum import Enum

# Корень проекта (папка с main.py) — для надёжного поиска resources при любом cwd
_PROJECT_ROOT = Path(__file__).resolve().parent.parent


class ResourcePath(Enum):
    RESOURCES = str(_PROJECT_ROOT / 'resources')
    IMAGES = str(_PROJECT_ROOT / 'resources' / 'images')
    MESSAGES = str(_PROJECT_ROOT / 'resources' / 'messages')
    PROMPTS = str(_PROJECT_ROOT / 'resources' / 'prompts')


class MessageRole(Enum):
    SYSTEM = 'system'
    USER = 'user'
    ASSISTANT = 'assistant'


class Extensions(Enum):
    JPG = '.jpg'
    TXT = '.txt'
