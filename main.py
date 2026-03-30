from fastapi import FastAPI, File, HTTPException, Request, Form, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from defs_file import (
    hash_password,
    verify_password,
    testing_funcktion_from_file,
    check_password,
    update_password_info,
    need_to_update_password
)
from log import server_logs
from https_cert import generate_self_signed_cert
import csv
import os
import pandas as pd
import datetime
import uuid
import shutil
import uvicorn
import json
from typing import List, Optional
from pydantic import BaseModel

app = FastAPI()
app.mount('/static', StaticFiles(directory='static'), name='static')
templates = Jinja2Templates(directory="templates")

sessions = {}
USERS_FILE = os.path.join(app.root_path, "users.csv")
# УДАЛЕНО: QUESTIONS_CSV больше не используется, вопросы хранятся в QUIZZES_DIR
RESULTS_CSV = os.path.join(app.root_path, "static", "results.csv")
# НОВОЕ: Папка для тем викторин
QUIZZES_DIR = os.path.join(app.root_path, "quizzes") 

SESSION_TTL = datetime.timedelta(hours=2) 
WHITE_LIST = ['/', '/login', '/logout', '/register', '/update_password'] 

# --- МОДЕЛИ DTO (Pydantic) ---

# Модель одного вопроса (используется для TopicPayload)
class Question(BaseModel):
    question: str
    answers: List[str]
    correct: int

# НОВОЕ: Модель для массового добавления вопросов
class TopicPayload(BaseModel):
    topic_name: str
    questions: List[Question]

# ОБНОВЛЕНО: Модель результата теперь включает тему
class Result(BaseModel):
    score: int
    total: int
    topic: str

# --- ФУНКЦИИ УТИЛИТЫ ---

def ensure_files():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["user_name", "user_password", "check_password", "role"])

    # УДАЛЕНО: Старая логика создания QUESTIONS_CSV

    # ОБНОВЛЕНО: Добавлена колонка topic в RESULTS_CSV
    if not os.path.exists(RESULTS_CSV):
        with open(RESULTS_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["username", "score", "total", "topic"]) 

    os.makedirs('tests', exist_ok=True)
    os.makedirs('codes', exist_ok=True)
    # НОВОЕ: Создание папки для тем викторин
    os.makedirs(QUIZZES_DIR, exist_ok=True)

ensure_files()

def get_session_user(request: Request):
    session_id = request.cookies.get('session_id')
    if not session_id or session_id not in sessions:
        return None
    created = sessions[session_id]["created"]
    if datetime.datetime.now() - created > SESSION_TTL:
        del sessions[session_id]
        return None
    sessions[session_id]["created"] = datetime.datetime.now()
    return sessions[session_id]

# --- MIDDLEWARE ---

@app.middleware("http")
@server_logs
async def check_session(request: Request, call_next):
    if request.url.path.startswith('/static') or request.url.path in WHITE_LIST:
        return await call_next(request)

    session_data = get_session_user(request)
    if not session_data:
        if request.url.path.startswith("/api"):
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
        return RedirectResponse(url='/login')

    return await call_next(request)

# --- РОУТЫ СТРАНИЦ (GET) ---

@app.get("/", response_class=HTMLResponse)
@app.get("/login", response_class=HTMLResponse)
@server_logs
def get_login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/update_password", response_class=HTMLResponse)
@server_logs
def update_password(request: Request):
    return templates.TemplateResponse("update_password.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
@server_logs
def get_register_page(request: Request): 
    # ВАШ ОРИГИНАЛЬНЫЙ КОД
    if request.cookies.get('role') == 'admin':
        return templates.TemplateResponse("register.html", {"request": request})
    else:
        return templates.TemplateResponse("403.html", {"request": request})

@app.get("/home", response_class=HTMLResponse)
@server_logs
def get_start_page(request: Request):
    username = request.cookies.get("username")
    return templates.TemplateResponse("main.html", {"request": request, "username": username})

@app.get("/create", response_class=HTMLResponse)
@server_logs
def get_tests_page(request: Request):
    return templates.TemplateResponse("create_test.html", {"request": request})

@app.get('/upload', response_class=HTMLResponse)
@server_logs
async def index(request: Request):
    folder = "tests"
    files = os.listdir(folder)
    files = [f[:-4] for f in files if os.path.isfile(os.path.join(folder, f))]
    return templates.TemplateResponse("open_test.html", {"request": request, "files": files})

@app.get("/upload/{test}", response_class=HTMLResponse)
@server_logs
def get_tests_page_upload(request: Request, test: str):
    return templates.TemplateResponse("tests.html", {"request": request, "test": test})

@app.get('/check', response_class=HTMLResponse)
@server_logs
async def get_upload_tests_page(request: Request):
    folder = "tests"
    files = os.listdir(folder)
    files = [f[:-4] for f in files if os.path.isfile(os.path.join(folder, f))]
    return templates.TemplateResponse("open_test_check.html", {"request": request, 'files': files})

@app.get('/check/{test}', response_class=HTMLResponse)
@server_logs
async def check_passed_test(request: Request, test: str):
    if not os.path.exists("log_tests.csv"):
        return templates.TemplateResponse("check_test.html", {"request": request, "rows": []})
    df = pd.read_csv("log_tests.csv")
    filtered = df[df["test_file"] == f'{test}.csv']
    rows = filtered.to_dict(orient="records")
    return templates.TemplateResponse("check_test.html", {"request": request, "rows": rows})

@app.get("/logout", response_class=HTMLResponse)
@server_logs
async def logout(request: Request):
    try:
        session_id = request.cookies.get("session_id")
        if session_id and session_id in sessions:
            del sessions[session_id]
        response = templates.TemplateResponse("login.html", {"request": request, 'error': 'Вы вышли из системы'})
        response.delete_cookie("session_id")
        response.delete_cookie("username")
        response.delete_cookie("role")
        return response
    except Exception:
        return RedirectResponse(url="/")

@app.get("/logout_afk", response_class=HTMLResponse)
@server_logs
async def logout_afk(request: Request):
    try:
        session_id = request.cookies.get("session_id")
        if session_id and session_id in sessions:
            del sessions[session_id]
        response = templates.TemplateResponse("login.html", {"request": request, 'error': 'Ваша сессия закончилась из-за бездействия'})
        response.delete_cookie("session_id")
        response.delete_cookie("username")
        response.delete_cookie("role")
        return response
    except Exception:
        return RedirectResponse(url="/")

@app.get("/quiz", response_class=HTMLResponse)
def quiz_page(request: Request):
    user = get_session_user(request)
    if not user:
        return RedirectResponse("/login")
    return templates.TemplateResponse("quiz.html", {
        "request": request,
        "username": user['username'],
        "role": user['role']
    })

@app.get('/password_info', response_class=HTMLResponse)
@server_logs
def password_info(request: Request):
    # ВАШ ОРИГИНАЛЬНЫЙ КОД
    if request.cookies.get('role') == 'admin':
        min_symbols, digits, symbols, lower_letters, upper_letters = update_password_info('password_info.json')
        return templates.TemplateResponse("password_info.html", {
            "request": request,
            'min_symbols': min_symbols,
            'digits': digits,
            'symbols': symbols,
            'lower_letters': lower_letters,
            'upper_letters': upper_letters
        })
    else:
        return templates.TemplateResponse("403.html", {"request": request})

# --- РОУТЫ СТРАНИЦ (POST) ---

@app.post("/login")
@server_logs
def login(request: Request,
          username: str = Form(...),
          password: str = Form(...)):

    # ВАШ ОРИГИНАЛЬНЫЙ КОД
    users = pd.read_csv(USERS_FILE)
    users['user_name'] = users['user_name'].astype(str)

    if username in users['user_name'].values:
        if verify_password(password, str(users[users["user_name"] == username].values[0][1])):
            session_id = str(uuid.uuid4())
            role = str(users[users["user_name"] == username].values[0][3])
            sessions[session_id] = {
                "username": username,
                "role": role,
                "created": datetime.datetime.now()
            }
            page = need_to_update_password(users, username, password)
            response = RedirectResponse(url=page, status_code=302)
            response.set_cookie(key='session_id', value=session_id, httponly=True)
            response.set_cookie(key='username', value=username, httponly=True)
            response.set_cookie(key='role', value=role, httponly=True)
            return response

    return templates.TemplateResponse("login.html", {"request": request, 'error': 'Неверный логин или пароль'})

@app.post('/register')
@server_logs
def register(request: Request,
             username: str = Form(...),
             password: str = Form(...),
             confirm_password: str = Form(...)):

    # ВАШ ОРИГИНАЛЬНЫЙ КОД
    users = pd.read_csv(USERS_FILE)

    result_of_password = check_password(password)
    if result_of_password is not True:
        return templates.TemplateResponse("register.html", {"request": request, 'error': result_of_password})

    if username in users['user_name'].values:
        return templates.TemplateResponse("register.html", {"request": request, 'error': 'Такое имя пользователя уже существует'})

    if password != confirm_password:
        return templates.TemplateResponse("register.html", {"request": request, 'error': 'Введенные вами пароли не совпадают'})

    new_row = [username, hash_password(password), False, 'user']
    with open(USERS_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(new_row)

    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "username": username,
        "role": "user",
        "created": datetime.datetime.now()
    }
    response = RedirectResponse(url='/home', status_code=302)
    response.set_cookie(key='session_id', value=session_id, httponly=True)
    response.set_cookie(key='username', value=username, httponly=True)
    response.set_cookie(key='role', value='user', httponly=True)
    return response

@app.post('/update_password')
@server_logs
def post_update_password(request: Request,
                         password: str = Form(...),
                         confirm_password: str = Form(...)):

    # ВАШ ОРИГИНАЛЬНЫЙ КОД
    users = pd.read_csv(USERS_FILE)

    result_of_password = check_password(password)
    if result_of_password is not True:
        return templates.TemplateResponse("update_password.html", {"request": request, 'error': result_of_password})

    if password != confirm_password:
        return templates.TemplateResponse("update_password.html", {"request": request, 'error': 'Введенные вами пароли не совпадают'})

    username = request.cookies.get('username')
    if username is None:
        return RedirectResponse(url='/login', status_code=302)

    users.loc[users["user_name"] == username, "user_password"] = hash_password(password)
    users.loc[users["user_name"] == username, "check_password"] = False
    users.to_csv(USERS_FILE, index=False)

    return RedirectResponse(url='/home', status_code=302)

@app.post("/create")
@server_logs
def create_test(request: Request,
                name_of_test: str = Form(...),
                task: str = Form(...),  
                test_data: str = Form(...)):

    # ВАШ ОРИГИНАЛЬНЫЙ КОД
    try:
        data_list = json.loads(test_data)
    except json.JSONDecodeError:
        return templates.TemplateResponse("create_test.html", {"request": request, "error": "Ошибка обработки данных"})

    name_of_test_path = os.path.join('tests', f"{name_of_test}.csv")
    with open(name_of_test_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["params", "answer"])
        for one_test in data_list:
            result = int(one_test[-1])
            params_items = one_test[:-1]
            params = tuple(int(i) for i in params_items)
            writer.writerow([params, result])

    return templates.TemplateResponse("create_test.html", {"request": request, "answer": "Тест создан"})

@app.post("/upload/{test}")
@server_logs
async def create_upload_file(request: Request,
                             test: str,
                             file: UploadFile = File(...)):

    # ВАШ ОРИГИНАЛЬНЫЙ КОД
    username = request.cookies.get("username")
    if not username:
        return RedirectResponse(url="/login", status_code=302)

    safe_filename = f"{username}_{file.filename}"
    file_path = os.path.join("codes", safe_filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    result = testing_funcktion_from_file(file_path, f'{test}.csv', username)
    return templates.TemplateResponse("tests.html", {"request": request, 'answer': result[3], "test": test})

@app.post('/password_info')
@server_logs
def post_password_info(request: Request,
                       min_symbols: str = Form(...),
                       digits: Optional[bool] = Form(False, alias="digits"),
                       symbols: Optional[bool] = Form(False, alias="symbols"),
                       lower_letters: Optional[bool] = Form(False, alias="lower_letters"),
                       upper_letters: Optional[bool] = Form(False, alias="upper_letters")):

    # ВАШ ОРИГИНАЛЬНЫЙ КОД
    if request.cookies.get('role') != 'admin':
        return templates.TemplateResponse("403.html", {"request": request})

    password_info = {
        'min_symbols': int(min_symbols),
        'digits': bool(digits),
        'symbols': bool(symbols),
        'lower_letters': bool(lower_letters),
        'upper_letters': bool(upper_letters)
    }

    with open('password_info.json', 'w', encoding='utf-8') as f:
        json.dump(password_info, f, ensure_ascii=False, indent=2)

    min_symbols_web, digits_web, symbols_web, lower_letters_web, upper_letters_web = update_password_info('password_info.json')

    users = pd.read_csv(USERS_FILE)
    users['check_password'] = True
    users.to_csv(USERS_FILE, index=False)

    return templates.TemplateResponse("password_info.html", {
        "request": request,
        'min_symbols': min_symbols_web,
        'digits': digits_web,
        'symbols': symbols_web,
        'lower_letters': lower_letters_web,
        'upper_letters': upper_letters_web,
        'answer': 'Загружено успешно'
    })

# --- НОВЫЕ API ДЛЯ ТЕМ И МАССОВОГО ДОБАВЛЕНИЯ ВИКТОРИН ---

# 1. НОВОЕ: Получить список доступных тем
@app.get("/api/topics")
def api_get_topics():
    # Сканируем папку quizzes
    files = [f.replace('.csv', '') for f in os.listdir(QUIZZES_DIR) if f.endswith('.csv')]
    return {"topics": files}

# 2. НОВОЕ: Получить вопросы по конкретной теме
@app.get("/api/questions")
def api_get_questions_by_topic(request: Request, topic: str):
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    file_path = os.path.join(QUIZZES_DIR, f"{topic}.csv")
    if not os.path.exists(file_path):
        return []
    
    questions = []
    try:
        with open(file_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                questions.append({
                    "question": row["question"],
                    "answers": [row.get("answer1", ""), row.get("answer2", ""), row.get("answer3", ""), row.get("answer4", "")],
                    "correct": int(row["correct"])
                })
    except Exception as e:
        print(f"Ошибка чтения файла {topic}: {e}")
        return []
        
    return questions

# 3. НОВОЕ: Сохранить пачку вопросов в тему (Админка)
@app.post("/api/save_topic")
def api_save_topic_questions(payload: TopicPayload, request: Request):
    user = get_session_user(request)
    if not user or user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Доступ запрещен")
    
    filename = f"{payload.topic_name}.csv"
    file_path = os.path.join(QUIZZES_DIR, filename)
    file_exists = os.path.exists(file_path)
    
    try:
        with open(file_path, "a", newline="", encoding="utf-8") as f:
            fieldnames = ["question", "answer1", "answer2", "answer3", "answer4", "correct"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            if not file_exists:
                writer.writeheader()
                
            for q in payload.questions:
                writer.writerow({
                    "question": q.question,
                    "answer1": q.answers[0],
                    "answer2": q.answers[1],
                    "answer3": q.answers[2],
                    "answer4": q.answers[3],
                    "correct": q.correct
                })
        return {"status": "ok", "message": f"Saved {len(payload.questions)} questions to {payload.topic_name}"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

# --- API РЕЗУЛЬТАТОВ ---

@app.get("/api/results")
def api_load_results(request: Request):
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Доступ запрещен")

    results = []
    if os.path.exists(RESULTS_CSV):
        with open(RESULTS_CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                results.append(row)
    return results

@app.post("/api/results")
def api_save_result(r: Result, request: Request):
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    file_exists = os.path.exists(RESULTS_CSV)
    with open(RESULTS_CSV, "a", newline="", encoding="utf-8") as f:
        # ОБНОВЛЕНО: fieldnames теперь включает 'topic'
        fieldnames = ["username", "score", "total", "topic"] 
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "username": user['username'],
            "score": r.score,
            "total": r.total,
            "topic": r.topic # <-- СОХРАНЯЕМ ТЕМУ
        })
    return {"status": "saved"}

# --- ОБРАБОТКА 404 ---

@app.get("/{url_path:path}", response_class=HTMLResponse)
@server_logs
async def not_found_catch_all(request: Request, url_path: str):
    return templates.TemplateResponse("404.html", {"request": request})

# -------------------------------
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
