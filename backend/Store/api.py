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
@check_role([RoleEnum.L3])
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
        pin_code=store.pin_code,
        store_ph_no=store.store_ph_no,
        lat=store.lat,
        long=store.long,
    )
    db.add(db_store)
    db.commit()
    db.refresh(db_store)
    return db_store


@router.get("/get-all-stores", response_model=list[StoreSummary])
@check_role([RoleEnum.L0, RoleEnum.L1, RoleEnum.L2, RoleEnum.L3, RoleEnum.L4])
async def read_stores(
    db: Session = Depends(get_session),
    token: dict = Depends(
        verify_token
    ),  # This dependency validates the token and provides its payload
):
    stores = db.query(
        Store
    ).all()
    return [
        StoreSummary(
            store_id=store.store_id,
            store_name=store.store_name,
            store_code=store.store_code,
            district=store.district,
            state=store.state,
        )
        for store in stores
    ]


# @router.get("/store-details/{store_id}", response_model=StoreResponse)
# @check_role([RoleEnum.L0, RoleEnum.L1, RoleEnum.L2, RoleEnum.L3])
# async def read_store(
#     store_id: str,
#     db: Session = Depends(get_session),
#     token: dict = Depends(verify_token),
# ):
#     store = db.query(Store).filter(Store.store_id == store_id).first()
#     if store is None:
#         raise HTTPException(status_code=404, detail="Store not found")
#     return store

@router.put("/edit-store/{store_id}", response_model=dict)
@check_role([RoleEnum.L3])
async def edit_store(
    store_id: str,
    store_update: StoreCreate,
    db: Session = Depends(get_session),
    token: dict = Depends(verify_token),
):
    try:
        store = db.query(Store).filter(Store.store_id == store_id).first()
        if not store:
            raise HTTPException(status_code=404, detail="Store not found")

        store.store_name = store_update.store_name
        store.store_code = store_update.store_code
        store.store_address = store_update.store_address
        store.district = store_update.district
        store.state = store_update.state
        store.store_status = store_update.store_status
        store.business_id = store_update.business_id
        store.area_id = store_update.area_id

        db.commit()
        db.refresh(store)
        return {"message": "Store updated successfully", "store_id": store.store_id}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating store: {str(e)}")


@router.delete("/delete-store/{store_id}", response_model=dict)
@check_role([RoleEnum.L3])
async def delete_store(
    store_id: str,
    db: Session = Depends(get_session),
    token: dict = Depends(verify_token),
):
    try:
        store = db.query(Store).filter(Store.store_id == store_id).first()
        if not store:
            raise HTTPException(status_code=404, detail="Store not found")

        db.delete(store)
        db.commit()
        return {"message": "Store deleted successfully", "store_id": store_id}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting store: {str(e)}")
