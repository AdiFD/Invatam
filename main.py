from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

# -------------------------
# MODELE (cu Pydantic)
# -------------------------

class Article(BaseModel):
    id: int
    title: str
    content: str
    published: Optional[bool] = True

class ArticleCreate(BaseModel):
    title: str
    content: str
    published: Optional[bool] = True

# -------------------------
# DEPENDENCY (fake user)
# -------------------------

def get_current_user():
    # Exemplu de utilizator "autentificat"
    return {"username": "admin"}

# -------------------------
# MEMORIE (fake DB)
# -------------------------

db_articles: List[Article] = []

# -------------------------
# ROUTING
# -------------------------

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI!"}

@app.get("/articles", response_model=List[Article])
def get_articles(user: dict = Depends(get_current_user)):
    return db_articles

@app.get("/articles/{article_id}", response_model=Article)
def get_article(article_id: int, user: dict = Depends(get_current_user)):
    for article in db_articles:
        if article.id == article_id:
            return article
    raise HTTPException(status_code=404, detail="Article not found")

@app.post("/articles", response_model=Article)
def create_article(article: ArticleCreate, user: dict = Depends(get_current_user)):
    new_id = len(db_articles) + 1
    new_article = Article(id=new_id, **article.dict())
    db_articles.append(new_article)
    return new_article

@app.put("/articles/{article_id}", response_model=Article)
def update_article(article_id: int, updated_article: ArticleCreate, user: dict = Depends(get_current_user)):
    for index, article in enumerate(db_articles):
        if article.id == article_id:
            new_article = Article(id=article_id, **updated_article.dict())
            db_articles[index] = new_article
            return new_article
    raise HTTPException(status_code=404, detail="Article not found")


@app.delete("/articles/{article_id}")
def delete_article(article_id: int, user: dict = Depends(get_current_user)):
    for index, article in enumerate(db_articles):
        if article.id == article_id:
            del db_articles[index]
            return {"message": "Article deleted"}
    raise HTTPException(status_code=404, detail="Article not found")
