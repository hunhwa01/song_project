from fastapi import FastAPI, Form, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, HTMLResponse
import sqlite3

app = FastAPI()

# Static 파일 설정
app.mount("/static", StaticFiles(directory="static"), name="static")

# 템플릿 디렉토리 설정
templates = Jinja2Templates(directory="templates")

# 데이터베이스 연결 및 테이블 확인/생성
def setup_database():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS emotions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        emotion TEXT NOT NULL,
        date DATE DEFAULT (DATE('now')),
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );
    """)
    conn.commit()
    conn.close()

setup_database()

# 데이터베이스 연결 함수
def get_db_connection():
    conn = sqlite3.connect("users.db")
    conn.row_factory = sqlite3.Row
    return conn

# 메인 페이지
@app.get("/")
def main_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# 로그인 페이지
@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# 회원가입 페이지
@app.get("/signup")
def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

# 회원가입 처리
@app.post("/signup")
def signup(username: str = Form(...), password: str = Form(...), confirm_password: str = Form(...)):
    print(f"회원가입 시도: {username}")  # 디버깅 로그

    if password != confirm_password:
        return {"error": "비밀번호가 일치하지 않습니다."}

    conn = get_db_connection()
    cursor = conn.cursor()

    # 중복 확인
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    if cursor.fetchone():
        print(f"중복된 아이디 발견: {username}")  # 디버깅 로그
        conn.close()
        return {"error": "이미 존재하는 아이디입니다."}

    # 회원 정보 저장
    cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
    conn.commit()
    conn.close()

    print(f"회원가입 성공: {username}")  # 디버깅 로그
    return RedirectResponse(url="/", status_code=302)

# 로그인 처리
@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    conn = get_db_connection()
    cursor = conn.cursor()
    print(f"로그인 시도: {username}, {password}")  # 디버깅 로그 추가

    # 사용자 인증
    cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
    user = cursor.fetchone()
    conn.close()

    if not user:
        print("로그인 실패: 잘못된 아이디 또는 비밀번호")  # 디버깅 로그
        return templates.TemplateResponse("login.html", {"request": Request, "error": "아이디나 비밀번호가 틀렸습니다."})

    print("로그인 성공")  # 디버깅 로그
    return RedirectResponse(url="/home", status_code=302)

# 환영 페이지
@app.get("/welcome")
def welcome_page(request: Request):
    return templates.TemplateResponse("welcome.html", {"request": request, "username": "로그인 성공!"})

# 비밀번호 찾기 페이지
@app.get("/forgot-password")
def forgot_password_page(request: Request):
    return templates.TemplateResponse("forgot_password.html", {"request": request})

# 비밀번호 재설정 처리
@app.post("/reset-password")
def reset_password(username: str = Form(...), new_password: str = Form(...)):
    conn = get_db_connection()
    cursor = conn.cursor()

    # 사용자 존재 여부 확인
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    if not cursor.fetchone():
        conn.close()
        return {"error": "존재하지 않는 아이디입니다."}

    # 비밀번호 업데이트
    cursor.execute("UPDATE users SET password = ? WHERE username = ?", (new_password, username))
    conn.commit()
    conn.close()
    return {"message": "비밀번호가 성공적으로 변경되었습니다."}

# 감정 정보 저장 처리
@app.post("/save-emotion")
def save_emotion(username: str = Form(...), emotion: str = Form(...)):
    valid_emotions = {"happy", "soso", "angry", "sad"}
    if emotion not in valid_emotions:
        return {"error": "유효하지 않은 감정입니다. 'happy', 'soso', 'angry', 'sad' 중 하나를 선택하세요."}

    conn = get_db_connection()
    cursor = conn.cursor()

    # 사용자 ID 확인
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()

    if not user:
        conn.close()
        return {"error": "존재하지 않는 사용자입니다."}

    # 감정 정보 저장
    cursor.execute("INSERT INTO emotions (user_id, emotion) VALUES (?, ?)", (user["id"], emotion))
    conn.commit()
    conn.close()

    return {"message": "감정 정보가 성공적으로 저장되었습니다."}

# 사용자 정보 조회 API
@app.get("/users")
def get_users():
    """
    이 API는 데이터베이스에 저장된 모든 사용자 정보를 반환합니다.
    반환 데이터: 사용자 ID와 username
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username FROM users")
    users = cursor.fetchall()
    conn.close()

    # 결과를 JSON 형식으로 반환
    return {"users": [dict(user) for user in users]}

# 사용자별 감정 정보 조회 API
@app.get("/user-emotions/{username}")
def get_user_emotions(username: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    # 사용자 ID 가져오기
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()

    if not user:
        conn.close()
        return {"error": "존재하지 않는 사용자입니다."}

    # 감정 정보 조회
    cursor.execute("SELECT emotion, date FROM emotions WHERE user_id = ?", (user["id"],))
    emotions = cursor.fetchall()
    conn.close()

    return {"emotions": [dict(emotion) for emotion in emotions]}

@app.get("/home", response_class=HTMLResponse)
async def read_home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/box")
def read_box(request: Request):
    return templates.TemplateResponse("box.html", {"request": request})

@app.get("/main_home_pli", response_class=HTMLResponse)
async def read_main_home_pli(request: Request):
    return templates.TemplateResponse("main_home_pli.html", {"request": request})

@app.get("/list", response_class=HTMLResponse)
async def read_list(request: Request):
    return templates.TemplateResponse("list.html", {"request": request})

@app.get("/sing", response_class=HTMLResponse)
async def read_sing(request: Request):
    return templates.TemplateResponse("sing.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
