# Настройка Cloudflare Workers

## Gemini API (нейросеть)

Бот использует **Gemini 2.5 Flash** через Cloudflare Worker — это обходит ограничения по региону («User location is not supported»).

**По умолчанию** используется публичный воркер: `https://gemini-proxy.alex555196.workers.dev`

В `.env`:
```
GEMINI_API_KEY=ваш_ключ_от_ai.google.dev
```

**Важно:** `GEMINI_WORKER_URL` и `TELEGRAM_API_URL` — это **разные** воркеры!
- GEMINI_WORKER_URL → generativelanguage.googleapis.com (для нейросети)
- TELEGRAM_API_URL → api.telegram.org (для бота)

Не путайте! Если указать воркер Telegram в GEMINI_WORKER_URL, нейросеть не заработает.

Если публичный воркер недоступен, разверните свой: скопируйте `cloudflare-worker-gemini.js` в новый Worker.

---

## Telegram API

Если `api.telegram.org` недоступен (например, заблокирован), используйте Cloudflare Worker как прокси. Worker бесплатен в рамках free-тира.

---

## Шаг 1. Регистрация в Cloudflare

1. Зайдите на [dash.cloudflare.com](https://dash.cloudflare.com/)
2. Войдите или создайте бесплатный аккаунт
3. Перейдите в **Workers & Pages** (меню слева)

---

## Шаг 2. Создание Worker

1. Нажмите **Create** → **Create Worker**
2. Введите имя (например, `telegram-api-proxy`) и нажмите **Deploy**
3. После деплоя нажмите **Edit code**
4. Удалите весь код по умолчанию
5. Скопируйте содержимое файла **`cloudflare-worker.js`** из этого проекта
6. Вставьте в редактор и нажмите **Save and Deploy**

---

## Шаг 3. Получение URL воркера

1. После деплоя откройте вкладку **Triggers**
2. Скопируйте URL вида: `https://telegram-api-proxy.ВАШ-АККАУНТ.workers.dev`
3. Либо нажмите **Custom Domain**, если хотите свой домен

---

## Шаг 4. Проверка работы

Откройте в браузере URL воркера (например, `https://telegram-api-proxy.xxx.workers.dev`).

Должен появиться ответ:
```json
{"status":"ok","message":"Telegram Bot API Proxy","usage":"Use this URL as TELEGRAM_API_URL in .env"}
```

---

## Шаг 5. Настройка бота

Добавьте в ваш **`.env`**:

```
TELEGRAM_API_URL=https://telegram-api-proxy.ВАШ-АККАУНТ.workers.dev
```

**Важно:** URL должен быть **без** слэша в конце.

---

## Шаг 6. Запуск бота

```bash
python main.py
```

Бот будет отправлять запросы к Telegram через Cloudflare Worker вместо заблокированного `api.telegram.org`.

---

## Альтернатива: Wrangler CLI

Если установлен [Wrangler](https://developers.cloudflare.com/workers/wrangler/install/):

```bash
# Установка (если нужно)
npm install -g wrangler

# Логин
wrangler login

# Деплой
wrangler deploy
```

---

## Устранение неполадок

| Проблема | Решение |
|----------|---------|
| `getaddrinfo failed` | Убедитесь, что `TELEGRAM_API_URL` указан в `.env` и бот перезапущен |
| `404 Not Found` | Проверьте, что URL воркера скопирован целиком, без лишних символов |
| `500 Internal Error` | Проверьте логи воркера в Cloudflare Dashboard → Workers → Ваш воркер → Logs |
