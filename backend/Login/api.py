from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import timedelta
from backend.db.db import get_session
from backend.Login.LoginModel import User
from backend.Login.LoginSchema import LoginSchema
from backend.auth.jwt_handler import create_access_token
from passlib.context import CryptContext

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

@router.post("/login")
def login_user(user_data: LoginSchema, db: Session = Depends(get_session)):
    user = db.query(User).filter(User.email == user_data.email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid email")
    if not verify_password(user_data.password, user.password):
        raise HTTPException(status_code=400, detail="Invalid password")
    
    # Create access token
    access_token = create_access_token(
        data={
            "sub": user.email,
            "role": user.user_role,
            "user_id": user.id
        },
        expires_delta=timedelta(minutes=30)
    )
    
    return {
        "message": "Login successful",
        "access_token": access_token,
        "token_type": "bearer"
    }

