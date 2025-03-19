# from fastapi import APIRouter
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.User.UserModel import User, Staff
from backend.User.UserSchema import (
    UserCreate,
    UserResponse,
    StaffResponse,
    StaffCreate,
    CreateUserResponse,
)
from backend.Store.StoreModel import Store
from backend.Area.AreaModel import Area
from backend.AudioProcessing.VoiceRecordingModel import VoiceRecording
from sqlalchemy import func
from backend.db.db import get_session
import uuid
from backend.auth.jwt_handler import verify_token

# from backend.utils.password import hash_password
from passlib.context import CryptContext


router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


@router.post("/create-user", response_model=CreateUserResponse)
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
        store_id=user.store_id,
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


@router.get("/get-all-users", response_model=list[UserResponse])
def read_users(db: Session = Depends(get_session)):
    users = db.query(User).all()
    user_data = []
    for user in users:
        store = db.query(Store).filter(Store.store_id == user.store_id).first()
        store_name = store.store_name if store else "Unknown"
        print(store_name)

        area = db.query(Area).filter(Area.area_id == store.area_id).first() if store else None
        area_manager_name = area.area_manager_name if area else "Unknown"

        total_duration = (
            db.query(func.sum(VoiceRecording.call_duration))
            .filter(VoiceRecording.user_id == user.id)
            .scalar()
            or 0
        )
        recording_hours = round(total_duration / 3600, 2)
        print("hello")
        user_data.append(
            UserResponse(
                id=user.id,
                name=user.name,
                email=user.email,
                user_role=user.user_role,
                business_key=user.business_key,
                store_id=user.store_id,
                store_name=store_name,
                area_manager_name=area_manager_name,
                last_login=user.last_login,
                user_status=user.user_status,
                created_at=user.created_at,
                modified_at=user.modified_at,
                recording_hours=recording_hours,
            )
        )

        print(users[0].__dict__)
    return user_data


@router.post("/add-staff", response_model=StaffResponse)
def add_staff(
    staff_body: StaffCreate,
    db: Session = Depends(get_session),
    token: dict = Depends(verify_token),
):
    affilated_user_id = token.get("user_id")
    if not affilated_user_id:
        raise HTTPException(status_code=401, detail="Invalid token or user ID missing")
    new_staff = Staff(
        name=staff_body.name,
        email_id=staff_body.email_id,
        affilated_user_id=affilated_user_id,
    )

    db.add(new_staff)
    db.commit()
    db.refresh(new_staff)

    return StaffResponse(
        id=new_staff.id,
        name=new_staff.name,
        email_id=new_staff.email_id,
        affilated_user_id=new_staff.affilated_user_id,
        created_at=new_staff.created_at,
        modified_at=new_staff.modified_at,
        staff_status=new_staff.staff_status,
    )
