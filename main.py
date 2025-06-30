from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from pydantic import BaseModel
from typing import List, Optional
from jose import JWTError, jwt
from datetime import datetime, timedelta
import bcrypt
import json
import os

# ----------------------------
# CONFIGURARE
# ----------------------------

SECRET_KEY = "secrettoken123"  
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

FILE_PATH = "articles.json"
USERS_FILE = "users.json"

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="login",
    scopes={},
    description="Autentificare simplă cu username și parolă"
)

# ----------------------------
# MODELE
# ----------------------------

class User(BaseModel):
    id: int
    username: str
    password: str  # hash-ul parolei

class UserCreate(BaseModel):
    username: str
    password: str

class Article(BaseModel):
    id: int
    title: str
    content: str
    published: Optional[bool] = True
    user_id: int

class ArticleCreate(BaseModel):
    title: str
    content: str
    published: Optional[bool] = True

# ----------------------------
# FUNCȚII PAROLĂ
# ----------------------------

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))

# ----------------------------
# SALVARE / ÎNCĂRCARE JSON
# ----------------------------

def load_articles() -> List[Article]:
    if os.path.exists(FILE_PATH):
        try:
            with open(FILE_PATH, "r") as f:
                data = json.load(f)
                return [Article(**a) for a in data]
        except json.JSONDecodeError:
            return []
    return []

def save_articles():
    try:
        with open(FILE_PATH, "w") as f:
            json.dump([article.dict() for article in db_articles], f, indent=4)
    except Exception as e:
        print(f"Error saving articles: {e}")

def load_users() -> List[dict]:
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

def save_users(users: List[dict]):
    try:
        with open(USERS_FILE, "w") as f:
            json.dump(users, f, indent=4)
    except Exception as e:
        print(f"Error saving users: {e}")

# ----------------------------
# HELPERI UTILIZATOR
# ----------------------------

def get_user_by_username(username: str) -> Optional[dict]:
    users = load_users()
    for user in users:
        if user["username"] == username:
            return user
    return None

def get_user_by_id(user_id: int) -> Optional[dict]:
    users = load_users()
    for user in users:
        if user["id"] == user_id:
            return user
    return None

# ----------------------------
# JWT TOKEN
# ----------------------------

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception
    user = get_user_by_id(user_id)
    if user is None:
        raise credentials_exception
    return user

# ----------------------------
# DATE ÎN MEMORIE
# ----------------------------

db_articles: List[Article] = load_articles()

# ----------------------------
# ROUTE-URI
# ----------------------------

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI!"}

@app.post("/register")
def register_user(user: UserCreate):
    users = load_users()
    if any(u["username"] == user.username for u in users):
        raise HTTPException(status_code=400, detail="Username already exists")
    new_user = {
        "id": users[-1]["id"] + 1 if users else 1,
        "username": user.username,
        "password": hash_password(user.password),
    }
    users.append(new_user)
    save_users(users)
    return {"message": "User registered successfully", "username": new_user["username"], "id": new_user["id"]}

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = get_user_by_username(form_data.username)
    if not user or not verify_password(form_data.password, user["password"]):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = create_access_token(
        data={"sub": str(user["id"])},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/articles", response_model=List[Article])
def get_published_articles():
    return [a for a in db_articles if a.published]

@app.get("/my-articles", response_model=List[Article])
def get_my_articles(user: dict = Depends(get_current_user)):
    return [a for a in db_articles if a.user_id == user["id"]]

from fastapi import Security

@app.get("/articles/{article_id}", response_model=Article)
def get_article(article_id: int, token: Optional[str] = Depends(oauth2_scheme)):
    article = next((a for a in db_articles if a.id == article_id), None)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    if article.published:
        return article  # articol public

    # articol privat: verificăm autentificarea
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = get_current_user(token)
    if article.user_id != user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to view this article")

    return article

@app.post("/articles", response_model=Article, status_code=201)
def create_article(article: ArticleCreate, user: dict = Depends(get_current_user)):
    new_id = db_articles[-1].id + 1 if db_articles else 1
    new_article = Article(id=new_id, user_id=user["id"], **article.dict())
    db_articles.append(new_article)
    save_articles()
    return new_article

@app.put("/articles/{article_id}", response_model=Article)
def update_article(article_id: int, updated_article: ArticleCreate, user: dict = Depends(get_current_user)):
    for index, article in enumerate(db_articles):
        if article.id == article_id and article.user_id == user["id"]:
            new_article = Article(id=article_id, user_id=user["id"], **updated_article.dict())
            db_articles[index] = new_article
            save_articles()
            return new_article
    raise HTTPException(status_code=403, detail="Not authorized to update this article")

@app.delete("/articles/{article_id}", status_code=204)
def delete_article(article_id: int, user: dict = Depends(get_current_user)):
    for index, article in enumerate(db_articles):
        if article.id == article_id and article.user_id == user["id"]:
            del db_articles[index]
            save_articles()
            return
    raise HTTPException(status_code=403, detail="Not authorized to delete this article")

@app.delete("/delete-account", status_code=204)
def delete_account(current_user: dict = Depends(get_current_user)):
    users = load_users()
    updated_users = [u for u in users if u["id"] != current_user["id"]]
    if len(users) == len(updated_users):
        raise HTTPException(status_code=404, detail="User not found")
    save_users(updated_users)

    global db_articles
    db_articles = [a for a in db_articles if a.user_id != current_user["id"]]
    save_articles()
    return
