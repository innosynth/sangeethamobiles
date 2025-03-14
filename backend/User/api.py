# from fastapi import APIRouter

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.User.UserModel import User
from backend.User.UserSchema import UserCreate, UserResponse
from backend.db.db import get_session
import uuid
# from backend.utils.password import hash_password
from passlib.context import CryptContext


router = APIRouter()   

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

@router.post("/create-user", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_session)):
    
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
  
    hashed_password = hash_password(user.password)
    db_user = User(
        id=str(uuid.uuid4()),
        name=user.name,
        password=hashed_password,
        email=user.email,
        user_role=user.user_role,
        business_key=user.business_key,
        store_id=user.store_id
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user



@router.get("/get-all-users", response_model=list[UserResponse])
def read_users(db: Session = Depends(get_session)):
    users = db.query(User).all()
    return users



