from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.Store.StoreModel import Store
from backend.Store.StoreSchema import StoreCreate, StoreResponse, StoreSummary, StoreUpdateSchema, StoreUpdateResponse
from backend.Area.AreaModel import Area
from backend.db.db import get_session
from typing_extensions import Annotated
from backend.schemas.RoleSchema import RoleEnum
from backend.auth.role_checker import check_role
from backend.auth.jwt_handler import verify_token
from sqlalchemy.exc import SQLAlchemyError

router = APIRouter()


@router.post("/create-store", response_model=StoreResponse)

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

@router.put("/edit-store/{store_id}", response_model=StoreUpdateResponse)
@check_role([RoleEnum.L4])  # Assuming this decorator handles role validation
async def edit_store(
    store_id: str,
    store_update: StoreUpdateSchema,  # Using dedicated update schema
    db: Session = Depends(get_session),
    token: dict = Depends(verify_token),
):
    """
    Update store information (Admin only)
    
    - Only L4 (admin) users can perform this action
    - Validates store exists
    - Checks for duplicate store codes
    - Validates area_id exists
    - Provides detailed error responses
    """
    try:
        # Validate store exists
        store = db.query(Store).filter(Store.store_id == store_id).first()
        if not store:
            raise HTTPException(status_code=404, detail="Store not found")

        # Check for store code conflicts (if store_code is being changed)
        if store_update.store_code and store_update.store_code != store.store_code:
            existing_store = db.query(Store).filter(
                Store.store_code == store_update.store_code,
                Store.store_id != store_id
            ).first()
            if existing_store:
                raise HTTPException(
                    status_code=400,
                    detail="Store code already in use by another store"
                )

        # Validate area exists if being updated
        if store_update.area_id:
            area = db.query(Area).filter(Area.area_id == store_update.area_id).first()
            if not area:
                raise HTTPException(status_code=400, detail="Invalid area ID")

        # Update only provided fields (partial update support)
        update_data = store_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(store, field, value)

        db.commit()
        db.refresh(store)

        return {
            "message": "Store updated successfully",
            "store_id": store.store_id,
            "updated_fields": list(update_data.keys())
        }

    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Database error while updating store"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )

@router.delete("/delete-store/{store_id}", response_model=dict)
@check_role([RoleEnum.L4])
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
