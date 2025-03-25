from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from backend.db.db import get_session
from backend.Area.AreaModel import Area
from backend.Area.AreaSchema import AreaCreate, AreaResponse, AreaSummary
from backend.auth.jwt_handler import verify_token
from backend.schemas.RoleSchema import RoleEnum
from backend.auth.role_checker import check_role

router = APIRouter()


@router.post("/create-area", response_model=AreaResponse)
@check_role([RoleEnum.L4])
async def create_area(
    area: AreaCreate,
    db: Session = Depends(get_session),
    token: dict = Depends(verify_token),
):
    db_area = Area(
        area_name=area.area_name,
        sales_id=area.sales_id,
        area_manager_name=area.area_manager_name,
    )
    db.add(db_area)
    db.commit()
    db.refresh(db_area)
    return db_area


@router.get("/get-all-areas", response_model=list[AreaSummary])
@check_role([RoleEnum.L3,RoleEnum.L4])
async def get_all_areas(
    db: Session = Depends(get_session),
    token: dict = Depends(verify_token),
):
    areas = db.query(Area.area_id, Area.area_name, Area.sales_id,Area.area_manager_name).all()

    return [
        AreaSummary(
            area_id=area[0],
            area_name=area[1],
            sales_id=area[2],
            area_manager_name=area[3],
        )
        for area in areas
    ]
