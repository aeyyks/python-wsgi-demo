import time
from urllib.parse import parse_qs


def application(environ, start_response):
    # 1. Получаем базовую информацию о запросе (аналог HttpServletRequest)
    method = environ.get('REQUEST_METHOD', 'GET')
    path = environ.get('PATH_INFO', '/')
    query_string = environ.get('QUERY_STRING', '')

    # 2. Простейший ручной роутинг
    if path == '/':
        return handle_home(method, query_string, start_response)
    elif path == '/echo' and method == 'POST':
        return handle_echo(environ, start_response)
    elif path == '/profile':
        # Этот обработчик уверен, что раз запрос до него дошел,
        # значит AuthMiddleware уже проверил токен и положил юзера в environ
        return handle_profile(environ, start_response)
    else:
        return handle_not_found(path, start_response)


def handle_home(method, query_string, start_response):
    # Парсим GET-параметры (например, /?name=Alex)
    params = parse_qs(query_string)
    name = params.get('name', ['Гость'])[0]

    status = '200 OK'
    headers = [('Content-Type', 'text/html; charset=utf-8')]
    start_response(status, headers)

    html = f"""
    <html>
        <body style="font-family: sans-serif; padding: 20px;">
            <h1>Привет, {name}!</h1>
            <p>Метод запроса: <b>{method}</b></p>
            <p>Попробуй передать параметр в URL: <a href="/?name=JavaDev">/?name=JavaDev</a></p>
            <hr>
            <h3>Тест POST-запроса (аналог doPost):</h3>
            <form method="POST" action="/echo">
                <input type="text" name="message" placeholder="Введи текст..." required>
                <button type="submit">Отправить</button>
            </form>
        </body>
    </html>
    """
    return [html.encode('utf-8')]


def handle_echo(environ, start_response):
    # В WSGI тело POST-запроса лежит в потоке environ['wsgi.input']
    # Чтобы прочитать его, нужно знать длину из заголовка CONTENT_LENGTH
    try:
        content_length = int(environ.get('CONTENT_LENGTH', 0))
    except ValueError:
        content_length = 0

    # Читаем сырые байты из потока и декодируем (аналог request.getReader())
    raw_body = environ['wsgi.input'].read(content_length).decode('utf-8')
    parsed_data = parse_qs(raw_body)
    message = parsed_data.get('message', ['пусто'])[0]

    status = '200 OK'
    headers = [('Content-Type', 'text/plain; charset=utf-8')]
    start_response(status, headers)

    response_text = f"Сервер получил POST-данные.\nСырое тело: {raw_body}\nРаспарсенное сообщение: {message}"
    return [response_text.encode('utf-8')]


def handle_not_found(path, start_response):
    status = '404 Not Found'
    headers = [('Content-Type', 'text/plain; charset=utf-8')]
    start_response(status, headers)
    return [f"404: Путь '{path}' не найден".encode('utf-8')]


def handle_profile(environ, start_response):
    # Достаем пользователя, которого положил AuthMiddleware!
    user = environ.get('CURRENT_USER', {})

    start_response('200 OK', [('Content-Type', 'text/plain; charset=utf-8')])
    text = f"Добро пожаловать в личный кабинет!\nВаше имя: {user.get('name')}\nВаша роль: {user.get('role')}"
    return [text.encode('utf-8')]


# --- 2. MIDDLEWARE (Аналог Servlet Filter) ---

class TimingMiddleware:
    """
    Используем класс с методом __call__, чтобы объект вел себя как функция.
    """

    def __init__(self, app):
        # Сохраняем ссылку на следующее приложение в цепочке (аналог FilterChain)
        self.app = app

    def __call__(self, environ, start_response):
        # [ШАГ 1: ДО ЗАПРОСА] (аналог кода до chain.doFilter)
        start_time = time.perf_counter()
        method = environ.get('REQUEST_METHOD')
        path = environ.get('PATH_INFO')

        # Мы даже можем модифицировать environ перед передачей дальше!
        environ['CUSTOM_TRACE_ID'] = 'req-12345'

        # [ШАГ 2: ПЕРЕХВАТ START_RESPONSE]
        # Чтобы добавить свой HTTP-заголовок (например, время выполнения),
        # мы подменяем оригинальный start_response своей функцией-оберткой.
        def custom_start_response(status, headers, exc_info=None):
            duration_ms = (time.perf_counter() - start_time) * 1000
            # Добавляем наш кастомный заголовок к тем, что сформировало приложение
            headers.append(('X-Process-Time-Ms', f'{duration_ms:.2f}'))
            headers.append(('X-Powered-By', 'Pure-Python-WSGI'))

            # Вызываем настоящий start_response от Waitress
            return start_response(status, headers, exc_info)

        # [ШАГ 3: ВЫЗОВ ОСНОВНОГО ПРИЛОЖЕНИЯ] (аналог chain.doFilter)
        # Передаем измененный environ и нашу обертку custom_start_response
        response_iterable = self.app(environ, custom_start_response)

        # [ШАГ 4: ПОСЛЕ ЗАПРОСА] (аналог кода после chain.doFilter)
        total_ms = (time.perf_counter() - start_time) * 1000
        print(f"[LOG] {method} {path} -> выполнено за {total_ms:.2f} мс")

        # Возвращаем байты ответа наверх серверу Waitress
        return response_iterable


# --- 2. MIDDLEWARE АВТОРИЗАЦИИ (Аналог SecurityFilter в Java) ---
class AuthMiddleware:
    # Имитация базы данных с валидными токенами
    TOKENS_DB = {
        'secret-token-123': {'name': 'Seva', 'role': 'admin'},
        'user-token-456': {'name': 'Mary', 'role': 'developer'},
    }

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '/')

        # 1. Публичные маршруты пропускаем без проверки
        if path != '/profile':
            return self.app(environ, start_response)

        # 2. Достаем заголовок Authorization (в WSGI он имеет префикс HTTP_)
        auth_header = environ.get('HTTP_AUTHORIZATION', '')

        # Проверяем формат "Bearer <токен>"
        if not auth_header.startswith('Bearer '):
            return self._unauthorized(start_response, "Отсутствует заголовок Authorization: Bearer <token>")

        token = auth_header.split(' ')[1]
        user = self.TOKENS_DB.get(token)

        # 3. Если токен не найден — прерываем запрос и не пускаем его в приложение!
        if not user:
            return self._unauthorized(start_response, "Неверный или просроченный токен")

        # 4. Токен верный! Обогащаем environ данными пользователя (Security Context)
        environ['CURRENT_USER'] = user

        # Передаем управление дальше по цепочке
        return self.app(environ, start_response)

    def _unauthorized(self, start_response, message):
        status = '401 Unauthorized'
        headers = [
            ('Content-Type', 'text/plain; charset=utf-8'),
            ('WWW-Authenticate', 'Bearer')  # Стандартный заголовок для 401 ответа
        ]
        start_response(status, headers)
        return [f"401 Доступ запрещен: {message}".encode('utf-8')]


# --- 3. СБОРКА МАТРЕШКИ ---
# Оборачиваем application в наш Middleware.
# Для Waitress переменная `application` по-прежнему выглядит как обычная функция!
# Запрос идет снаружи внутрь: TimingMiddleware -> AuthMiddleware -> application
application = TimingMiddleware(AuthMiddleware(application))
