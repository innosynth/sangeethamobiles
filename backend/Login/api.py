from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import timedelta
from backend.db.db import get_session
from backend.User.UserModel import User
from backend.Login.LoginSchema import LoginSchema
from backend.auth.jwt_handler import create_access_token
from passlib.context import CryptContext
from datetime import datetime


router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


@router.post("/login")
def login_user(user_data: LoginSchema, db: Session = Depends(get_session)):
    user = db.query(User).filter(User.email_id == user_data.email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid email")
    if not verify_password(user_data.password, user.password):
        raise HTTPException(status_code=400, detail="Invalid password")

    access_token = create_access_token(
        data={"sub": user.email_id, "role": user.role, "user_id": user.user_id},
        expires_delta=timedelta(minutes=480),
    )

    user.last_login = datetime.utcnow()
    db.commit()
    db.refresh(user)

    return {
        "user_id": user.user_id,
        "message": "Login successful",
        "role" : user.role,
        "access_token": access_token,
        "token_type": "bearer",
        "last_login": user.last_login.isoformat(),
    }
