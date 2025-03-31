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
    StaffResponses,
)
from backend.Store.StoreModel import L0
from backend.Area.AreaModel import L1
from backend.schemas.RoleSchema import RoleEnum
from backend.AudioProcessing.VoiceRecordingModel import VoiceRecording
from sqlalchemy import func
from backend.db.db import get_session
from sqlalchemy.exc import SQLAlchemyError
from backend.User.UserSchema import UserUpdateSchema, UserUpdateResponse
import uuid
from backend.User.service import extract_users
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
    existing_user = db.query(User).filter(User.email_id == user.email_id).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = hash_password(user.password)
    db_user = User(
        user_id=str(uuid.uuid4()),
        name=user.name,
        email_id=user.email_id,
        user_code=user.user_code,
        password=hashed_password,
        user_ph_no=user.user_ph_no,
        reports_to=user.reports_to,
        business_id=user.business_id,
        role=user.role,
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


@router.get("/get-all-users", response_model=list[UserResponse])
def read_users(
    db: Session = Depends(get_session),
    token: dict = Depends(verify_token),
):
    user_id = token.get("user_id")
    user_role = token.get("role")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    user_data = extract_users(user_id, user_role, db)
    if not user_data:
        raise HTTPException(status_code=404, detail="No users found")

    return user_data


@router.put("/edit-user/{user_id}", response_model=UserUpdateResponse)
def edit_user(
    user_id: str,
    user_update: UserUpdateSchema,  # Use a dedicated update schema
    db: Session = Depends(get_session),
    token: dict = Depends(verify_token),
):
    try:
        token_user_id = token.get("user_id")
        if not token_user_id:
            raise HTTPException(status_code=401, detail="Authentication required")

        try:
            user_role = RoleEnum(token.get("role", ""))
        except ValueError:
            raise HTTPException(status_code=403, detail="Invalid user role")

        if user_role != RoleEnum.L4:
            raise HTTPException(
                status_code=403,
                detail="Only administrators can modify user information",
            )

        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user_update.email_id and user_update.email_id != user.email_id:
            existing_user = (
                db.query(User)
                .filter(User.email_id == user_update.email_id, User.user_id != user_id)
                .first()
            )
            if existing_user:
                raise HTTPException(
                    status_code=400, detail="Email already in use by another account"
                )

        update_data = user_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)
        db.commit()
        db.refresh(user)

        return {
            "message": "User updated successfully",
            "user_id": user.user_id,
            "updated_fields": list(update_data.keys()),
        }

    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail="Database error while updating user"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


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

        if user_role != RoleEnum.L4:
            raise HTTPException(status_code=403, detail="Only admins can delete users.")

        user = db.query(User).filter(User.user_id == user_id).first()
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


@router.post("/add-staff", response_model=StaffResponse)
def add_staff(
    staff_body: StaffCreate,
    db: Session = Depends(get_session),
    token: dict = Depends(verify_token),
):
    user_id = token.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token or user ID missing")
    new_staff = Staff(
        name=staff_body.name,
        email_id=staff_body.email_id,
        user_id=user_id,
    )

    db.add(new_staff)
    db.commit()
    db.refresh(new_staff)

    return StaffResponse(
        staff_id=new_staff.id,
        name=new_staff.name,
        email_id=new_staff.email_id,
        affilated_user_id=new_staff.user_id,
        created_at=new_staff.created_at,
        modified_at=new_staff.modified_at,
        staff_status=new_staff.staff_status,
    )


@router.get("/get-all-staff", response_model=list[StaffResponses])
async def get_all_staff(
    db: Session = Depends(get_session),
    token: dict = Depends(verify_token),
):
    try:
        # Get the logged-in user's business ID
        user = db.query(User).filter(User.user_id == token.get("user_id")).first()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid user")

        # Fetch staff members linked to the same business
        staff_members = (
            db.query(Staff)
            .join(
                User, User.user_id == Staff.user_id
            )  # Ensure staff is linked to a valid user
            .filter(User.business_id == user.business_id)  # Filter by business ID
            .all()
        )

        return [
            StaffResponses(
                id=staff.id,
                name=staff.name,
                email_id=staff.email_id,
                affiliated_user_id=staff.user_id,
                created_at=staff.created_at,
                modified_at=staff.modified_at,
                staff_status=staff.staff_status,
            )
            for staff in staff_members
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving staff: {str(e)}")
