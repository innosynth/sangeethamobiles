from fastapi import APIRouter

router = APIRouter()

router.get("/stores")
def get_stores():
    return {"message": "Get all stores"}

router.get("/stores/{store_id}")
def get_store(store_id: str):
    return {"message": f"Get store with ID {store_id}"}

router.post("/create-store")
def create_store():
    return {"message": "Create store"}

router.put("/update-store/{store_id}") 
def update_store(store_id: str):
    return {"message": f"Update store with ID {store_id}"}

router.delete("/delete-store/{store_id}")
def delete_store(store_id: str):
    # make status as inactive dont delete from DB
    return {"message": f"Delete store with ID {store_id}"}

