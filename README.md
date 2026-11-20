# python-wsgi-demo

Учебный веб-сервис на **чистом Python + WSGI** без фреймворков (только stdlib и `waitress`). Демонстрирует парсинг запросов, ручной роутинг, работу с POST и цепочку middleware (тайминг + Bearer-авторизация) с параллелями к Java Servlet API.

## Стек и структура
* **Python 3.8+** (тестировалось на 3.14) и **Waitress** (`requirements.txt`).
* `app.py` — всё приложение в одном файле: обработчики, middleware и сборка цепочки `TimingMiddleware(AuthMiddleware(application))`.

## Маршруты и доступ

| Метод | Путь | Описание | Доступ |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | HTML-приветствие (`?name=...`) и форма для теста POST | Публичный |
| `POST` | `/echo` | Чтение `wsgi.input`, возврат сырого тела и поля `message` | Публичный |
| `GET` | `/profile` | Профиль из `environ['CURRENT_USER']` | `Authorization: Bearer <token>` |

**Тестовые токены** (`AuthMiddleware.TOKENS_DB`): `secret-token-123` (Seva, admin), `user-token-456` (Mary, developer).  
`TimingMiddleware` добавляет ко всем ответам заголовки `X-Process-Time-Ms` и `X-Powered-By`, а также логирует время в консоль.

## Установка и запуск

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate | Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

waitress-serve --host=127.0.0.1 --port=8000 app:application
```
*(Либо программно через `waitress.serve(application, host='127.0.0.1', port=8000)`).*

## Примеры запросов

```bash
# GET с параметром
curl "http://127.0.0"

# POST-данные
curl -X POST http://127.0.0 --data "message=Привет, WSGI!"

# Защищённый маршрут (без токена вернёт 401)
curl http://127.0.0 -H "Authorization: Bearer secret-token-123"
```
