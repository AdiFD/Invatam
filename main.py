from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from pydantic import BaseModel
from typing import List, Optional
from jose import JWTError, jwt
from datetime import datetime, timedelta
import bcrypt

from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
import models
import schemas

# Creează tabelele în DB la pornire
Base.metadata.create_all(bind=engine)

app = FastAPI()

SECRET_KEY = "secrettoken123"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


# Dependency pentru sesiunea DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        if user_id is None:
            raise credentials_exception
    except (JWTError, ValueError):
        raise credentials_exception

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user


@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI with MySQL!"}


@app.post("/register", response_model=schemas.User)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    hashed_password = bcrypt.hashpw(user.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    db_user = models.User(username=user.username, password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not bcrypt.checkpw(form_data.password.encode("utf-8"), user.password.encode("utf-8")):
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": str(user.id)}, expires_delta=access_token_expires)

    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/articles", response_model=List[schemas.Article])
def get_published_articles(db: Session = Depends(get_db)):
    articles = db.query(models.Article).filter(models.Article.published == True).all()
    return articles


@app.get("/my-articles", response_model=List[schemas.Article])
def get_my_articles(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    articles = db.query(models.Article).filter(models.Article.user_id == current_user.id).all()
    return articles


@app.get("/articles/{article_id}", response_model=schemas.Article)
def get_article(article_id: int, token: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    article = db.query(models.Article).filter(models.Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    if article.published:
        return article

    # articol privat: verificăm autentificarea
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = get_current_user(token, db)
    if article.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this article")

    return article


@app.post("/articles", response_model=schemas.Article, status_code=201)
def create_article(article: schemas.ArticleCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_article = models.Article(**article.dict(), user_id=current_user.id)
    db.add(db_article)
    db.commit()
    db.refresh(db_article)
    return db_article


@app.put("/articles/{article_id}", response_model=schemas.Article)
def update_article(article_id: int, updated_article: schemas.ArticleCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    article = db.query(models.Article).filter(models.Article.id == article_id).first()
    if not article or article.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this article")

    article.title = updated_article.title
    article.content = updated_article.content
    article.published = updated_article.published
    db.commit()
    db.refresh(article)
    return article


@app.delete("/articles/{article_id}", status_code=204)
def delete_article(article_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    article = db.query(models.Article).filter(models.Article.id == article_id).first()
    if not article or article.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this article")

    db.delete(article)
    db.commit()
    return


@app.delete("/delete-account", status_code=204)
def delete_account(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Șterge toate articolele utilizatorului
    db.query(models.Article).filter(models.Article.user_id == current_user.id).delete()
    # Șterge utilizatorul
    db.query(models.User).filter(models.User.id == current_user.id).delete()
    db.commit()
    return
