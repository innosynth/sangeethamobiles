from fastapi import APIRouter, Depends, HTTPException
from requests import Session

from backend.User.UserModel import User
from backend.User.service import extract_users
from backend.auth.jwt_handler import verify_token
from backend.db.db import get_session
from backend.sales.SalesModel import L2
from backend.sales.SalesSchema import RegionListResponse, RegionOut
from backend.schemas.RoleSchema import RoleEnum

router = APIRouter()


@router.get("/get-regions", response_model=RegionListResponse)
def get_regions(
    db: Session = Depends(get_session),
    token: dict = Depends(verify_token),
):
    user_id = token.get("user_id")
    role_str = token.get("role")

    if not user_id or role_str is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        user_role = RoleEnum(role_str)
    except ValueError:
        raise HTTPException(status_code=403, detail="Invalid role")

    if user_role not in [RoleEnum.L4, RoleEnum.L3]:
        raise HTTPException(status_code=403, detail="Only L3 and L4 users can access all regions")

    downline_users = extract_users(user_id, user_role, db)
    l2_users = [user for user in downline_users if user.role == RoleEnum.L2.value]

    if not l2_users:
        return RegionListResponse(regions=[])

    l2_user_ids = [u.user_id for u in l2_users]

    regions = (
        db.query(L2, User.email_id)
        .join(User, L2.user_id == User.user_id)
        .filter(L2.user_id.in_(l2_user_ids))
        .all()
    )

    return RegionListResponse(
        regions=[
            RegionOut(
                region_id=region.L2_id,
                region_name=region.L2_name,
                region_email=email
            )
            for region, email in regions
        ]
    )
