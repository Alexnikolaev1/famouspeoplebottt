from aiogram.types import FSInputFile

import os

from .enums import ResourcePath, Extensions


class Button:
    def __init__(self, path: str, callback: str | None = None):
        if callback is not None:
            self.name = path
            self.callback = callback
        else:
            self._path = os.path.join(ResourcePath.PROMPTS.value, path + Extensions.TXT.value)
            try:
                with open(self._path, 'r', encoding='UTF-8') as txt_file:
                    first_line = txt_file.readline().strip()
                    # Первая строка должна быть вида "name:Имя Персонажа"
                    if first_line.startswith('name:'):
                        self.name = first_line[5:].strip()
                    else:
                        self.name = path
            except FileNotFoundError as e:
                raise FileNotFoundError(f'Файл кнопки не найден: {self._path}') from e
            self.callback = path


class Buttons:
    """Автоматически обнаруживает файлы персонажей в resources/prompts/.

    Персонажем считается любой .txt файл, первая строка которого
    начинается с «name:» (например, «name:Vladimir Solovyov»).
    """

    def __init__(self):
        self.buttons = self._read_buttons()

    @staticmethod
    def _read_buttons() -> list[Button]:
        prompts_path = ResourcePath.PROMPTS.value
        if not os.path.isdir(prompts_path):
            return []
        result: list[Button] = []
        for fname in sorted(os.listdir(prompts_path)):
            if not fname.endswith('.txt'):
                continue
            fpath = os.path.join(prompts_path, fname)
            try:
                with open(fpath, 'r', encoding='UTF-8') as f:
                    first_line = f.readline().strip()
                if first_line.startswith('name:'):
                    result.append(Button(fname[:-4]))  # без .txt
            except (OSError, UnicodeDecodeError):
                continue
        return result

    def __iter__(self):
        return self

    def __next__(self):
        while self.buttons:
            return self.buttons.pop(0)
        raise StopIteration


# Связь кнопок/команд с изображениями: resources/images/{имя}.jpg или .png
# Команды: main, random, ask, talk, quiz
# Персоналии: определяются автоматически по строке «name:» в промптах
IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.webp')


class Resource:

    def __init__(self, file_name: str):
        self._file_name = file_name

    @property
    def photo(self):
        images_dir = ResourcePath.IMAGES.value
        for ext in IMAGE_EXTENSIONS:
            photo_path = os.path.join(images_dir, self._file_name + ext)
            if os.path.exists(photo_path):
                return FSInputFile(photo_path)

    @property
    def text(self):
        text_path = os.path.join(ResourcePath.MESSAGES.value, self._file_name + Extensions.TXT.value)
        if os.path.exists(text_path):
            with open(text_path, 'r', encoding='UTF-8') as file:
                return file.read()

    def as_kwargs(self) -> dict[str, FSInputFile | str]:
        photo = self.photo
        text = self.text or ''
        if photo is None:
            raise FileNotFoundError(f'Изображение не найдено: {self._file_name}{Extensions.JPG.value}')
        return {'photo': photo, 'caption': text}

    def as_message_kwargs(self) -> tuple[bool, dict]:
        """Возвращает (use_photo, kwargs) — use_photo=False если изображения нет."""
        photo = self.photo
        text = self.text or ''
        if photo:
            return True, {'photo': photo, 'caption': text}
        return False, {'text': text or 'Добро пожаловать!'}
