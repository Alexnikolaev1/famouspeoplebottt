# Как отправить проект на GitHub

Выполните команды **по порядку** в PowerShell в папке проекта `Famouspeoplebot`.

## 1. Исправить URL репозитория

Сейчас `origin` указывает на плейсхолдер. Замените на ваш репозиторий:

```powershell
git remote set-url origin https://github.com/Alexnikolaev1/Famouspeoplebot.git
```

Проверка: `git remote -v` — должно быть `Alexnikolaev1/Famouspeoplebot`.

## 2. Переименовать ветку в main (опционально, но удобно для Vercel)

По умолчанию Git создал ветку `master`. Vercel часто ожидает `main`:

```powershell
git branch -M main
```

## 3. Отправить код на GitHub

```powershell
git push -u origin main
```

Если оставили ветку `master`, тогда:

```powershell
git push -u origin master
```

---

**Если снова будет ошибка «src refspec main does not match any»** — значит ветка всё ещё называется `master`. Тогда просто:

```powershell
git push -u origin master
```

После успешного `git push` подключайте репозиторий в Vercel Dashboard и добавляйте переменные окружения (BOT_TOKEN, GEMINI_API_KEY, UPSTASH_REDIS_URL).
