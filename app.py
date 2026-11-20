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
