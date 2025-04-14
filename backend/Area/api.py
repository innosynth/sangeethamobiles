from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from backend.User.service import extract_users
from backend.db.db import get_session
from backend.Area.AreaModel import L1
from backend.Area.AreaSchema import AreaCreate, AreaResponse, AreaSummary
from backend.auth.jwt_handler import verify_token
from backend.schemas.RoleSchema import RoleEnum
from backend.auth.role_checker import check_role
from backend.User.UserModel import User


router = APIRouter()


@router.post("/create-area", response_model=AreaResponse)
@check_role([RoleEnum.L1, RoleEnum.L2, RoleEnum.L3, RoleEnum.L4])  # L0 blocked here
def create_area(
    area: AreaCreate,
    db: Session = Depends(get_session),
    token: dict = Depends(verify_token),
):
    db_area = L1(
        L1_name=area.area_name,
        user_id=token.get("user_id"),
    )

    db.add(db_area)
    db.commit()
    db.refresh(db_area)

    return AreaResponse(
        area_id=db_area.L1_id,
        area_name=db_area.L1_name,
        user_id=db_area.user_id,
        status=db_area.status,
        created_at=db_area.created_at,
        modified_at=db_area.modified_at,
    )


@router.get("/get-all-areas", response_model=list[AreaSummary])
@check_role([RoleEnum.L1, RoleEnum.L2, RoleEnum.L3, RoleEnum.L4])
def get_all_areas(
    db: Session = Depends(get_session),
    token: dict = Depends(verify_token),
):
    user_id = token.get("user_id")
    role_str = token.get("role")

    if not user_id or not role_str:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        user_role = RoleEnum(role_str)
    except ValueError:
        raise HTTPException(status_code=403, detail="Invalid user role")

    if user_role == RoleEnum.L1:
        area = db.query(L1.L1_id, L1.L1_name, User.name).join(User, L1.user_id == User.user_id).filter(L1.user_id == user_id).first()
        return [AreaSummary(area_id=area[0], area_name=area[1], asm_name=area[2])] if area else []

    downline_users = extract_users(user_id, user_role, db)
    downline_user_ids = [u.user_id for u in downline_users]
    downline_user_ids.append(user_id)

    areas = (
        db.query(L1.L1_id, L1.L1_name, User.name)
        .join(User, L1.user_id == User.user_id)
        .filter(L1.user_id.in_(downline_user_ids))
        .all()
    )

    return [
        AreaSummary(area_id=area[0], area_name=area[1], asm_name=area[2])
        for area in areas
    ]
