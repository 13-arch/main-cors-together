'''ФАЙЛ С ОБЫЧНЫМИ ФУНКЦИЯМИ'''

import csv
import hashlib
import importlib.util
import os
import sys
import gfhdthev as gf
import ast
import json
from log import log_test
import pandas as pd

#символы для пароля
digits='1234567890'
upper_letters='ABCDEFGHIJKLMNOPQRSTUVWXYZ'
lower_letters='abcdefghijklmnopqrstuvwxyz'
symbols='!@#$%^&*()-+'

# --- Хэширование через SHA-512 ---
def hash_password(password: str) -> str:
    return hashlib.sha512(password.encode("utf-8")).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

#импорт функции по пути
def import_function_from_file(file_path: str, function_name: str):
    module_name = os.path.splitext(os.path.basename(file_path))[0]

    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    return getattr(module, function_name)

'''user,test_file,user_file,result,passed_tests,failes_tests,date,time'''
@log_test
def testing_funcktion_from_file(file_path: os.path, file_with_tests, username) -> set:#username передается только для логов
    #в файле с тестами (file_with_tests) обязательно столбцы называются params и answer
    # Импортируем функцию main из загруженного файла
    try:
        main = import_function_from_file(file_path, "main")#проверять функцию main, а не по отдельности
    except Exception as e:
        return {"error": str(e)}
    
    file_with_tests = os.path.join('tests', file_with_tests)

    #файлы для логов
    user_file = f'{file_path}'[6:]
    test_file = f'{file_with_tests}'[6:]

    passed_tests = {}
    failed_tests = {}

    with open(file_with_tests, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            params = ast.literal_eval(row["params"])  # Преобразуем строку в кортеж
            answer = int(row["answer"])  
            result = gf.run_test(main, params, answer)# пример вызова

            if result == 'passed': 
                passed_tests[result] = row
            else: 
                failed_tests[result] = row

            if failed_tests: #если словарь с ошибками не пустой, то провал
                result = next(iter(failed_tests.values()))#берет первое value
            else:
                result = 'passed'

    result = (username, test_file, user_file, result, passed_tests, failed_tests)

    return result


def check_password(password: str):
    #берем из 'password_info.json' требования к паролю
    try:
        with open('password_info.json', 'r', encoding='utf-8') as f:
            password_info = json.load(f)

    except FileNotFoundError: #если файла не существует, то просто возвращаем, что пароль подходит
        return True
    
    else:
        flag = False
        if len(password) < password_info['min_symbols']: 
            return 'Пароль должен состоять минимум из 8 символов'
        
        if password_info['digits'] is True:#проверяем каждое требование по json-у
            for i in password:
                if i in digits: 
                    flag = True
            if flag is True:
                flag = False
            else:
                return 'Ваш пароль должен содержать хотя бы одну цифру'
        
        if password_info['lower_letters'] is True:
            for i in password:
                if i in lower_letters: 
                    flag = True
            if flag is True:
                flag = False
            else:
                return 'Ваш пароль должен содержать хотя бы один символ маленького регистра'
        
        if password_info['upper_letters'] is True:
            for i in password:
                if i in upper_letters: 
                    flag = True
            if flag is True:
                flag = False
            else:
                return 'Ваш пароль должен содержать хотя бы один символ большого регистра'
        
        if password_info['symbols'] is True:
            for i in password:
                if i in symbols: 
                    flag = True
            if flag is True:
                flag = False
            else:
                return 'Ваш пароль должен содержать хотя бы один специальный символ'

        return True

def update_password_info(file):
    try:
        with open(file, 'r', encoding='utf-8') as f:
            password_info = json.load(f)

    except FileNotFoundError:#если файла нету, то передает обычные значения
        min_symbols = 'Ввод'
        digits = 'on'
        symbols = 'on'
        lower_letters = 'on'
        upper_letters = 'on'
        
    else:#если есть, то проверяет инт и булевы значения
        min_symbols = password_info['min_symbols']
        digits = 'yes' if password_info['digits'] else 'on'
        symbols = 'yes' if password_info['symbols'] else 'on'
        lower_letters = 'yes' if password_info['lower_letters'] else 'on'
        upper_letters = 'yes' if password_info['upper_letters'] else 'on'

    return min_symbols, digits, symbols, lower_letters, upper_letters

def need_to_update_password(users: pd.DataFrame, username: str, password: str) -> str:
    #если у пользователя пароль подходит по требованиям, то пропускаем его дальше без проверки
    if users[users["user_name"] == username].values[0][2] == False:
        #чтобы что-то положить в куки, надо обязательно создать response
        return '/home'
    
    else: #если надо проверить пароль
        answer = check_password(password)
        #если пароль проходит проверку
        if answer == True:
            #меняем на false, чтобы при следующем заходе не проверять 
            users.loc[users["user_name"] == username, "check_password"] = False
            users.to_csv("users.csv", index=False) #обновляем csv
            return '/home'
        else:
            return '/update_password'