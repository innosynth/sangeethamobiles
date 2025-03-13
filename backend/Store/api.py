# from fastapi import APIRouter

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.Store.StoreModel  import Store
from backend.Store.StoreSchema import StoreCreate, StoreResponse
from backend.db.db import get_session
router = APIRouter()


@router.post("/stores/", response_model=StoreResponse)
def create_store(store: StoreCreate, db: Session = Depends(get_session)):
    db_store = Store(
        store_name=store.store_name,
        store_code=store.store_code,
        store_address=store.store_address,
        district=store.district,
        state=store.state,
        store_status=store.store_status,
        business_id=store.business_id,
        area_id=store.area_id
    )
    db.add(db_store)
    db.commit()
    db.refresh(db_store)
    return db_store


@router.get("/stores/", response_model=list[StoreResponse])
def read_stores(db: Session = Depends(get_session)):
    stores = db.query(Store).all()
    return stores


@router.get("/stores/{store_id}", response_model=StoreResponse)
def read_store(store_id: str, db: Session = Depends(get_session)):
    store = db.query(Store).filter(Store.store_id == store_id).first()
    if store is None:
        raise HTTPException(status_code=404, detail="Store not found")
    return store
