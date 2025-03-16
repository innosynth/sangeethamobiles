from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.Store.StoreModel import Store
from backend.Store.StoreSchema import StoreCreate, StoreResponse, StoreSummary
from backend.db.db import get_session
from typing_extensions import Annotated
from backend.schemas.RoleSchema import RoleEnum
from backend.auth.role_checker import check_role
from backend.auth.jwt_handler import verify_token

router = APIRouter()


@router.post("/create-store", response_model=StoreResponse)
@check_role([RoleEnum.L2, RoleEnum.L0])
async def create_store(
    store: StoreCreate,
    db: Session = Depends(get_session),
    token: dict = Depends(verify_token),
):
    db_store = Store(
        store_name=store.store_name,
        store_code=store.store_code,
        store_address=store.store_address,
        district=store.district,
        state=store.state,
        store_status=store.store_status,
        business_id=store.business_id,
        area_id=store.area_id,
    )
    db.add(db_store)
    db.commit()
    db.refresh(db_store)
    return db_store


@router.get("/get-all-stores", response_model=list[StoreSummary])
@check_role([RoleEnum.L0, RoleEnum.L1, RoleEnum.L2, RoleEnum.L3])
async def read_stores(
    db: Session = Depends(get_session),
    token: dict = Depends(
        verify_token
    ),  # This dependency validates the token and provides its payload
):
    stores = db.query(
        Store.store_id, Store.store_name, Store.district, Store.state
    ).all()
    return [
        StoreSummary(
            store_id=store[0], store_name=store[1], district=store[2], state=store[3]
        )
        for store in stores
    ]


@router.get("/store-details/{store_id}", response_model=StoreResponse)
@check_role([RoleEnum.L0, RoleEnum.L1, RoleEnum.L2, RoleEnum.L3])
async def read_store(
    store_id: str,
    db: Session = Depends(get_session),
    token: dict = Depends(verify_token),
):
    store = db.query(Store).filter(Store.store_id == store_id).first()
    if store is None:
        raise HTTPException(status_code=404, detail="Store not found")
    return store
