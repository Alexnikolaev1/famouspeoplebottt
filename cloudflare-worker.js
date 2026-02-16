/**
 * Cloudflare Worker — прокси для Telegram Bot API
 * Обходит блокировку api.telegram.org (например, в РФ)
 * 
 * Деплой: см. CLOUDFLARE_SETUP.md
 */
export default {
  async fetch(request) {
    const url = new URL(request.url);

    // Проверка работы воркера (GET /)
    if (url.pathname === '/' || url.pathname === '') {
      return new Response(
        JSON.stringify({
          status: 'ok',
          message: 'Telegram Bot API Proxy',
          usage: 'Use this URL as TELEGRAM_API_URL in .env',
        }),
        { headers: { 'Content-Type': 'application/json' } }
      );
    }

    // CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
          'Access-Control-Allow-Headers': '*',
        },
      });
    }

    // Проксирование на официальный Telegram API
    const externalUrl = 'https://api.telegram.org';
    const proxiedUrl = externalUrl + url.pathname + url.search;

    try {
      const proxiedRequest = new Request(proxiedUrl, {
        method: request.method,
        headers: request.headers,
        body: request.body,
      });

      const response = await fetch(proxiedRequest);
      console.log('Telegram API status:', response.status, proxiedUrl);
      const newResponse = new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: response.headers,
      });
      newResponse.headers.set('Access-Control-Allow-Origin', '*');
      return newResponse;
    } catch (error) {
      return new Response(
        JSON.stringify({ error: error.message }),
        {
          status: 500,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }
  },
};
