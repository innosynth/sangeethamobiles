from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.db.db import get_session
from typing_extensions import Annotated
from backend.schemas.RoleSchema import RoleEnum
from backend.auth.jwt_handler import verify_token
from backend.Dashboard.schemas import *
from backend.User.UserModel import User

router = APIRouter()


@router.get("/last-login", response_model=LastLogin)
async def get_last_login(
    user_id: str = Query(None),  # Optional user_id as query parameter
    db: Session = Depends(get_session),
    token: dict = Depends(verify_token),
):
    token_user_id = token.get("user_id")
    role = token.get("role")

    if not token_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        user_role = RoleEnum(role)
    except ValueError:
        raise HTTPException(status_code=403, detail="Invalid role in token")

    if user_id:
        if user_role != RoleEnum.L3:
            raise HTTPException(status_code=403, detail="Permission denied")
    else:
        user_id = token_user_id

    user = db.query(User).filter(User.user_id == user_id).first()
    print(user.__dict__)

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
