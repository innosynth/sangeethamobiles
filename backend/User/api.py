from fastapi import APIRouter

router = APIRouter()   

router.get("/users")
def get_users():
    return {"message": "Get all users"}

router.get("/users/{user_id}")
def get_user(user_id: str):
    return {"message": f"Get user with ID {user_id}"}

router.post("/create-user")
def create_user():
    return {"message": "Create user"}

router.put("/update-user/{user_id}")
def update_user(user_id: str):
    return {"message": f"Update user with ID {user_id}"}

router.delete("/delete-user/{user_id}")
def delete_user(user_id: str):
    # make status as inactive dont delete from DB
    return {"message": f"Delete user with ID {user_id}"}
