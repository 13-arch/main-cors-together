#Gfhdthev
#Логирование


#импортируем библиотеки
import os
import datetime
import pandas as pd
from functools import wraps
import inspect
from fastapi import Request

#берем имя пользователя компьютера
user=os.getlogin()

#работа с временем
def now_time():
    now_date=datetime.datetime.now().strftime('%d.%m.%Y') #полное время, включая год, месяц и т.д.
    return now_date
def sec():
    now_datetime=str(datetime.datetime.now()).split() #разделяем на дату и время
    current_time= now_datetime[1] #берем только время
    return current_time


def log_test(func):
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        '''(user, test_file, user_file, result, passed, failed)'''
        user, test_file, user_file, res, passed, failed = result

        #проверяем, существует ли файл
        if os.path.isfile("log_tests.csv"):
            file_df = pd.read_csv("log_tests.csv", index_col=0)
            next_index = file_df.index.max() + 1
        else:
            file_df = None
            next_index = 0

        data = {
            "user": [user],
            "test_file": [test_file],
            "user_file": [user_file],
            "result": [res],
            "passed_tests": [passed],
            "failed_tests": [failed],
            "date": [now_time()],
            "time": [sec()]
        }

        df = pd.DataFrame(data, index=[next_index])

        if file_df is None:
            df.to_csv("log_tests.csv", index=True, index_label="")
        else:
            df.to_csv("log_tests.csv", mode="a", header=False, index=True)

        return result
    return wrapper


def server_logs(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if inspect.iscoroutinefunction(func):
            response = await func(*args, **kwargs)
        else:
            response = func(*args, **kwargs)

        request: Request = kwargs.get("request") or next((arg for arg in args if hasattr(arg, "url")), None)

        url = str(request.url) if request else "unknown"
        status_code = response.status_code if hasattr(response, "status_code") else "unknown"

        # Проверяем, залогинен ли пользователь
        session_id = request.cookies.get("session_id", "") if request else ""
        user = request.cookies.get("username", "") if session_id else ""
        role = request.cookies.get("role", "") if session_id else ""

        log_data = {
            "date": now_time(),
            "time": sec(),
            "function": func.__name__,
            "status_code": status_code,
            "url": url,
            "user": user,
            "role": role,
            "session_id": session_id
        }

        log_df = pd.DataFrame([log_data])

        if os.path.isfile("server_logs.csv"):
            log_df.to_csv("server_logs.csv", mode="a", header=False, index=False)
        else:
            log_df.to_csv("server_logs.csv", index=False)

        return response

    return wrapper