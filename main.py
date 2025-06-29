from fastapi import FastAPI, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import List, Optional

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

# ----------------------------
# DEPENDENCY
# ----------------------------

def get_current_user():
    return {"username": "admin"}

# ----------------------------
# FAKE DATABASE
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
