from pydantic import BaseModel, EmailStr
from typing import List

class RegisterIn(BaseModel):
    email: EmailStr
    password: str

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

class RecordIn(BaseModel):
    date: str
    description: str
    amount: float
    source: str = "manual"

class RecordOut(BaseModel):
    id: int
    date: str
    description: str
    amount: float
    category: str
    confidence: float
    source: str

class RecurringIn(BaseModel):
    name: str
    amount: float
    category: str
    schedule: str = "monthly"
    day_of_month: int = 1
    active: bool = True

class RecurringOut(BaseModel):
    id: int
    name: str
    amount: float
    category: str
    schedule: str
    day_of_month: int
    active: bool
