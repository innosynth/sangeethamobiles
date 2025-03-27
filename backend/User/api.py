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

    # Get the business_id of the logged-in user
    current_user = db.query(User.business_id).filter(User.user_id == user_id).first()

    if not current_user:
        raise HTTPException(status_code=404, detail="User not found")

    business_id = current_user.business_id

    # Fetch all users in the business in one query
    users = db.query(User).filter(User.business_id == business_id).all()

    if not users:
        return []

    user_ids = [user.user_id for user in users]
    reports_to_ids = [user.reports_to for user in users if user.reports_to]

    # Batch fetch L0 (store names)
    l0_data = (
        db.query(L0.user_id, L0.L0_name)
        .filter(L0.user_id.in_(user_ids))
        .all()
    )
    store_map = {l0.user_id: l0.L0_name for l0 in l0_data}

    # Batch fetch L1 (area names)
    l1_data = (
        db.query(L1.user_id, L1.L1_name)
        .filter(L1.user_id.in_(user_ids))
        .all()
    )
    area_map = {l1.user_id: l1.L1_name for l1 in l1_data}

    # Batch fetch manager names using reports_to (email_id mapping)
    managers = (
        db.query(User.email_id, User.name)
        .filter(User.email_id.in_(reports_to_ids))
        .all()
    )
    manager_map = {m.email_id: m.name for m in managers}

    # Batch fetch total recording durations, counts, and listening times
    recording_data = (
        db.query(
            VoiceRecording.user_id,
            func.sum(VoiceRecording.call_duration).label("total_duration"),
            func.sum(VoiceRecording.listening_time).label("total_listening"),
            func.count(VoiceRecording.id).label("recording_count"),
        )
        .filter(VoiceRecording.user_id.in_(user_ids))
        .group_by(VoiceRecording.user_id)
        .all()
    )
    recording_map = {rec.user_id: rec for rec in recording_data}

    user_data = []

    for user in users:
        store_name = store_map.get(user.user_id, "Unknown")
        area_name = area_map.get(user.user_id, "Unknown")
        reports_to_name = manager_map.get(user.reports_to, "Unknown")

        rec_stats = recording_map.get(user.user_id)
        recording_hours = round((rec_stats.total_duration or 0) / 3600, 2) if rec_stats else 0
        listening_hours = round((rec_stats.total_listening or 0) / 3600, 2) if rec_stats else 0
        recording_count = rec_stats.recording_count if rec_stats else 0

        user_data.append(
            UserResponse(
                user_id=user.user_id,
                name=user.name,
                email_id=user.email_id,
                user_code=user.user_code,
                user_ph_no=user.user_ph_no,
                reports_to=reports_to_name,
                business_id=user.business_id,
                role=user.role,
                store_name=store_name,
                area_name=area_name,
                created_at=user.created_at,
                modified_at=user.modified_at,
                status=user.status,
                recording_hours=recording_hours,
                recording_count=recording_count,
                listening_hours=listening_hours,
            )
        )

    return user_data


@router.put("/edit-user/{user_id}", response_model=UserUpdateResponse)
def edit_user(
    user_id: str,
    user_update: UserUpdateSchema,  # Use a dedicated update schema
    db: Session = Depends(get_session),
    token: dict = Depends(verify_token),
):
    """
    Update user information (Admin only)
    
    - Only L4 (admin) users can perform this action
    - Validates user exists
    - Checks for duplicate email
    - Provides detailed error responses
    """
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
                detail="Only administrators can modify user information"
            )

        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user_update.email_id and user_update.email_id != user.email_id:
            existing_user = db.query(User).filter(
                User.email_id == user_update.email_id,
                User.user_id != user_id
            ).first()
            if existing_user:
                raise HTTPException(
                    status_code=400,
                    detail="Email already in use by another account"
                )

        update_data = user_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)
        db.commit()
        db.refresh(user)

        return {
            "message": "User updated successfully",
            "user_id": user.user_id,
            "updated_fields": list(update_data.keys())
        }

    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Database error while updating user"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )

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
        id=new_staff.id,
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
            .join(User, User.user_id == Staff.user_id)  # Ensure staff is linked to a valid user
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
