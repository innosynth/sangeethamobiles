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
from backend.schemas.RoleSchema import RoleEnum
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

        # # Ensure area_name is always set
        if store:
            area = db.query(Area).filter(Area.area_id == store.area_id).first()
            area_name = area.area_name if area else "Unknown"
        else:
            area_name = "Unknown"  # Set default value if store is None

        # Calculate total recording duration
        total_duration = (
            db.query(func.sum(VoiceRecording.call_duration))
            .filter(VoiceRecording.user_id == user.id)
            .scalar()
            or 0
        )
        total_listening_time = (
            db.query(func.sum(VoiceRecording.listening_time))
            .filter(VoiceRecording.user_id == user.id)
            .scalar()
            or 0
        )
        listening_hours = round(total_listening_time / 3600, 2)
        recording_hours = round(total_duration / 3600, 2)

        # Count the number of recordings for this user
        recording_count = (
            db.query(func.count(VoiceRecording.id))
            .filter(VoiceRecording.user_id == user.id)
            .scalar()
            or 0
        )

        user_data.append(
            UserResponse(
                id=user.id,
                name=user.name,
                email=user.email,
                user_role=user.user_role,
                business_key=user.business_key,
                store_id=user.store_id,
                store_name=store_name,
                area_name=area_name,
                last_login=user.last_login,
                user_status=user.user_status,
                created_at=user.created_at,
                modified_at=user.modified_at,
                recording_hours=recording_hours,
                recording_count=recording_count,
                listening_hours=listening_hours,
            )
        )

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

@router.put("/edit-user/{user_id}", response_model=dict)
def edit_user(
    user_id: str,
    user_update: UserCreate,
    db: Session = Depends(get_session),
    token: dict = Depends(verify_token),
):
    try:
        token_user_id = token.get("user_id")
        role_str = token.get("role")
        if not token_user_id:
            raise HTTPException(status_code=401, detail="Unauthorized")

        try:
            user_role = RoleEnum(role_str)
        except ValueError:
            raise HTTPException(status_code=403, detail="Invalid user role.")

        if user_role != RoleEnum.L3:
            raise HTTPException(status_code=403, detail="Only admins can edit users.")

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user.name = user_update.name
        user.email = user_update.email
        user.user_role = user_update.user_role
        user.business_key = user_update.business_key
        user.store_id = user_update.store_id
        db.commit()
        db.refresh(user)
        return {"message": "User updated successfully", "user_id": user.id}

    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating user: {str(e)}")


@router.delete("/delete-user/{user_id}", response_model=dict)
def delete_user(
    user_id: str,
    db: Session = Depends(get_session),
    token: dict = Depends(verify_token),
):
    try:
        token_user_id = token.get("user_id")
        role_str = token.get("role")
        if not token_user_id:
            raise HTTPException(status_code=401, detail="Unauthorized")

        try:
            user_role = RoleEnum(role_str)
        except ValueError:
            raise HTTPException(status_code=403, detail="Invalid user role.")

        if user_role != RoleEnum.L3:
            raise HTTPException(status_code=403, detail="Only admins can delete users.")

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        db.delete(user)
        db.commit()
        return {"message": "User deleted successfully", "user_id": user_id}

    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting user: {str(e)}")
