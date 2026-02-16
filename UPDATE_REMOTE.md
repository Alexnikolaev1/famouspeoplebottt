# Обновление remote на новый репозиторий

Выполните в PowerShell в папке проекта:

```powershell
# Удалить старый remote
git remote remove origin

# Добавить новый remote (замените на ваш правильный URL)
git remote add origin https://github.com/Alexnikolaev1/famouspeoplebottt.git

# Проверить
git remote -v

# Запушить код в новый репозиторий
git push -u origin main
```

**Важно:** После этого в Vercel Dashboard нужно:
1. Открыть проект
2. Settings → Git → Disconnect Repository
3. Add New Project → выбрать репозиторий `famouspeoplebottt`
4. Настроить Environment Variables заново (BOT_TOKEN, GEMINI_API_KEY, UPSTASH_REDIS_URL)
5. Deploy

Или можно просто обновить подключение:
1. Settings → Git → Edit
2. Выбрать репозиторий `famouspeoplebottt`
3. Сохранить
