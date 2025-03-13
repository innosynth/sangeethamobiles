from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from passlib.context import CryptContext
from backend.db.db import get_session
from backend.Login.LoginModel import User
from backend.Login.LoginSchema import LoginSchema

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


@router.post("/login")
def login_user(user_data: LoginSchema, db: Session = Depends(get_session)):
    user = db.query(User).filter(User.email == user_data.email).first()
    if not user :
        return {"message": "Invalid email"}
    if not verify_password(user_data.password, user.password):
        raise HTTPException(status_code=400, detail="Invalid password")
    return {"message": "Login successful"}

