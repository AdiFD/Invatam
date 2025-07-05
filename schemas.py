from pydantic import BaseModel
from typing import Optional

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    class Config:
        from_attributes = True

class ArticleBase(BaseModel):
    title: str
    content: str
    published: Optional[bool] = True

class ArticleCreate(ArticleBase):
    pass

class Article(ArticleBase):
    id: int
    user_id: int
    class Config:
        from_attributes = True
