import ast #https://docs.python.org/3/library/ast.html
from multiprocessing import Process, Queue

# Список ключевых слов и модулей, которые считаются опасными
# Эти конструкции могут повредить систему, получить доступ к файлам или завершить работу программы
FORBIDDEN_KEYWORDS = [
    "os", "subprocess", "shutil", "sys", "eval", "exec", "open", "exit", "quit", "input"
]

def is_code_safe(code: str) -> bool:
    """
    Проверяет, что исходный код не содержит запрещённых импортов и вызовов.

    :param code: строка с исходным кодом функции
    :return: True, если код безопасен, иначе False
    """
    try:
        # Парсим код в абстрактное синтаксическое дерево (AST)
        tree = ast.parse(code)

        # Проходим по всем узлам дерева
        for node in ast.walk(tree):
            # Проверка обычных импортов: import os
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in FORBIDDEN_KEYWORDS:
                        return False

            # Проверка импортов вида: from os import system
            elif isinstance(node, ast.ImportFrom):
                if node.module in FORBIDDEN_KEYWORDS:
                    return False

            # Проверка вызовов функций: eval(), exec(), open(), и т.д.
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_KEYWORDS:
                    return False

        return True  # Если ничего запрещённого не найдено
    except Exception:
        return False  # Если код не удалось распарсить — считаем его небезопасным

def _run_user_code(func, args, q):
    """
    Вспомогательная функция, которая вызывается в отдельном процессе.
    Выполняет функцию с аргументами и кладёт результат или исключение в очередь.

    :param func: функция, которую нужно выполнить
    :param args: кортеж аргументов
    :param q: очередь для передачи результата
    """
    try:
        result = func(*args)
        q.put(result)
    except Exception as e:
        q.put(e)

def run_test(func, args: set, expected, timeout: int = 1):
    """
    Запускает пользовательскую функцию в изолированном процессе с тайм-аутом и проверкой безопасности.

    :param func: функция, которую нужно протестировать
    :param args: кортеж аргументов для функции
    :param expected: ожидаемый результат
    :param timeout: максимальное время выполнения в секундах
    :return: строка-статус: 'passed', 'failed', 'timeout', 'error', 'unsafe', 'unread'
    """
    # Получаем путь к файлу, в котором определена функция
    source_path = func.__code__.co_filename

    try:
        # Читаем исходный код файла
        with open(source_path, encoding="utf-8") as f:
            source_code = f.read()
    except Exception as e:
        #ошибка при чтении кода
        return "unread"

    # Проверяем, безопасен ли код
    if not is_code_safe(source_code):
        #небезопасный код
        return "unsafe"

    # Создаём очередь и процесс для выполнения функции
    q = Queue()
    p = Process(target=_run_user_code, args=(func, args, q))
    p.start()
    p.join(timeout=timeout)

    # Если процесс не завершился вовремя — прерываем
    if p.is_alive():
        p.terminate()
        #превышен лимит по времени
        return "timeout"
    else:
        # Получаем результат из очереди
        result = q.get()
        if isinstance(result, Exception):
            #ошибка при выполнении
            return "error"
        elif result == expected:
            #все гуд
            return "passed"
        else:
            #неправильный результат
            return "failed"