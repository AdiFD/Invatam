from fastapi import FastAPI, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import List, Optional

import bcrypt

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))

from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt
from datetime import datetime, timedelta

SECRET_KEY = "secrettoken123"  
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="login",
    scopes={},  # evită extra scopuri
    description="Autentificare simplă cu username și parolă"
)

app = FastAPI()

# ----------------------------
# JSON PATH
# ----------------------------

import json
import os

FILE_PATH = "articles.json"

def save_articles():
    with open(FILE_PATH, "w") as f:
        json.dump([article.dict() for article in db_articles], f, indent=4)

def load_articles():
    if os.path.exists(FILE_PATH):
        with open(FILE_PATH, "r") as f:
            try:
                data = json.load(f)
                return [Article(**a) for a in data]
            except json.JSONDecodeError:
                return []
    return []

# ----------------------------
# USER JSON
# ----------------------------

USERS_FILE = "users.json"

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

# ----------------------------
# USER MODELS
# ----------------------------

class User(BaseModel):
    id: int
    username: str
    password: str  # parola va fi hashuită

class UserCreate(BaseModel):
    username: str
    password: str


# ----------------------------
# MODELE
# ----------------------------

class Article(BaseModel):
    id: int
    title: str
    content: str
    published: Optional[bool] = True

class ArticleCreate(BaseModel):
    title: str
    content: str
    published: Optional[bool] = True


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes = 15))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_user_by_username(username: str):
    users = load_users()
    for user in users:
        if user["username"] == username:
            return user
    return None

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = get_user_by_username(form_data.username)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    if not verify_password(form_data.password, user["password"]):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": user["id"]}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": access_token, "token_type": "bearer"}


# ----------------------------
# DEPENDENCY
# ----------------------------

from fastapi import Security

def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user_by_id(user_id)  # Va trebui să implementezi această funcție
    if user is None:
        raise credentials_exception
    return user

def get_user_by_id(user_id: int):
    users = load_users()
    for user in users:
        if user["id"] == user_id:
            return user
    return None


# ----------------------------
# DATABASE JSON
# ----------------------------

db_articles: List[Article] = load_articles()

# ----------------------------
# ROUTE: HOME
# ----------------------------

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI!"}

# ----------------------------
# GET all articles (with filter)
# ----------------------------

@app.post("/register")
def register_user(user: UserCreate):
    users = load_users()
    if any(u["username"] == user.username for u in users):
        raise HTTPException(status_code=400, detail = "username already exists")
    
    new_user = {
        "id": users[-1]["id"] + 1 if users else 1,
        "username": user.username,
        "password": hash_password(user.password)
    }

    users.append(new_user)
    save_users(users)
    return {"message": "User registered successfully"} 


@app.get("/articles", response_model=List[Article])
def get_articles(
    published: Optional[bool] = Query(None),
    user: dict = Depends(get_current_user)
):
    if published is not None:
        return [a for a in db_articles if a.published == published]
    return db_articles

# ----------------------------
# GET one article by ID
# ----------------------------

@app.get("/articles/{article_id}", response_model=Article)
def get_article(article_id: int, user: dict = Depends(get_current_user)):
    for article in db_articles:
        if article.id == article_id:
            return article
    raise HTTPException(status_code=404, detail="Article not found")

# ----------------------------
# POST create article
# ----------------------------

@app.post("/articles", response_model=Article, status_code=201)
def create_article(article: ArticleCreate, user: dict = Depends(get_current_user)):
    new_id = db_articles[-1].id + 1 if db_articles else 1
    new_article = Article(id=new_id, **article.dict())
    db_articles.append(new_article)
    save_articles()
    return new_article

# ----------------------------
# PUT update article
# ----------------------------

@app.put("/articles/{article_id}", response_model=Article)
def update_article(article_id: int, updated_article: ArticleCreate, user: dict = Depends(get_current_user)):
    for index, article in enumerate(db_articles):
        if article.id == article_id:
            new_article = Article(id=article_id, **updated_article.dict())
            db_articles[index] = new_article
            save_articles()
            return new_article
    raise HTTPException(status_code=404, detail="Article not found")

# ----------------------------
# DELETE article
# ----------------------------

@app.delete("/articles/{article_id}", status_code=204)
def delete_article(article_id: int, user: dict = Depends(get_current_user)):
    for index, article in enumerate(db_articles):
        if article.id == article_id:
            del db_articles[index]
            save_articles()
            return
    raise HTTPException(status_code=404, detail="Article not found")
