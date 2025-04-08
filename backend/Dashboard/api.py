from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.User.service import extract_users
from backend.db.db import get_session
from typing_extensions import Annotated
from backend.schemas.RoleSchema import RoleEnum
from backend.auth.jwt_handler import verify_token
from backend.Dashboard.schemas import *
from backend.User.UserModel import User

router = APIRouter()


@router.get("/last-login", response_model=LastLogin)
async def get_last_login(
    user_id: Optional[str] = Query(None, description="User ID to fetch last login for"),
    db: Session = Depends(get_session),
    token: dict = Depends(verify_token),
):
    token_user_id = token.get("user_id")
    role_str = token.get("role")

    if not token_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        user_role = RoleEnum(role_str)
    except ValueError:
        raise HTTPException(status_code=403, detail="Invalid role in token")

    # 🚀 **L0 Users Can Only Access Their Own Last Login**
    if user_role == RoleEnum.L0:
        if user_id and user_id != token_user_id:
            raise HTTPException(
                status_code=403,
                detail="L0 users cannot access other users' last login info."
            )
        user_id = token_user_id  # Force L0 users to fetch their own last login

    else:
        if user_id:
            # Check if the requested user_id reports to the logged-in user
            user_reports = extract_users(token_user_id, user_role, db)
            allowed_user_ids = {user.user_id for user in user_reports}

            if user_id not in allowed_user_ids and user_role != RoleEnum.L3:
                raise HTTPException(
                    status_code=403,
                    detail="You don't have permission to access this user's last login info."
                )
        else:
            user_id = token_user_id  # Default to the logged-in user's ID if not provided

    # Fetch the user record
    user = db.query(User).filter(User.user_id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return LastLogin(user_id=user_id, last_login=user.last_login)


# ## available staff based on user_id
# @router.get("/available-staff", response_model=AvailableStaff)
# async def create_store(
#     db: Session = Depends(get_session),
#     token: dict = Depends(verify_token),
# ):
#     pass

# ## available staff based on user_id
# @router.get("/available-staff", response_model=AvailableStaff)
# async def create_store(
#     db: Session = Depends(get_session),
#     token: dict = Depends(verify_token),
# ):
#     pass


# @router.get("latest-voice-recording")
# async def latest_voice_recording():
#     pass
