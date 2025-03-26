from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from backend.db.db import get_session
from backend.Area.AreaModel import L1
from backend.Area.AreaSchema import AreaCreate, AreaResponse, AreaSummary
from backend.auth.jwt_handler import verify_token
from backend.schemas.RoleSchema import RoleEnum
from backend.auth.role_checker import check_role
from backend.User.UserModel import User


router = APIRouter()


@router.post("/create-area", response_model=AreaResponse)
@check_role([RoleEnum.L4])
async def create_area(
    area: AreaCreate,
    db: Session = Depends(get_session),
    token: dict = Depends(verify_token),
):
    db_area = L1(
        L1_name=area.area_name,  # Correct field name
        user_id=token.get("user_id"),  # Extract user_id from token
    )

    db.add(db_area)
    db.commit()
    db.refresh(db_area)

    return AreaResponse(
        area_id=db_area.L1_id,  # Mapping L1_id → area_id
        area_name=db_area.L1_name,  # Mapping L1_name → area_name
        user_id=db_area.user_id,  # Include user_id
        status=db_area.status,  # Include status
        created_at=db_area.created_at,
        modified_at=db_area.modified_at,
    )

@router.get("/get-all-areas", response_model=list[AreaSummary])
@check_role([RoleEnum.L3, RoleEnum.L4])
async def get_all_areas(
    db: Session = Depends(get_session),
    token: dict = Depends(verify_token),
):
    user_id = token.get("user_id")

    # Get the business_id of the logged-in user
    user = db.query(User.business_id).filter(User.user_id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    business_id = user.business_id

    # Query areas where the user's business_id matches
    areas = (
        db.query(L1.L1_id, L1.L1_name)
        .join(User, User.user_id == L1.user_id)  # Join on user_id
        .filter(User.business_id == business_id)  # Filter by business_id
        .all()
    )

    return [
        AreaSummary(
            area_id=area[0],  # L1_id
            area_name=area[1],  # L1_name
        )
        for area in areas
    ]
