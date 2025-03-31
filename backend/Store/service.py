
from backend.Store.StoreModel import L0
from backend.User.UserModel import User
from backend.schemas.RoleSchema import RoleEnum

def get_stores(db):
    # stores = (
    #     db.query(L0)
    #     .join(User, L0.user_id == User.user_id).all()
    # )
    pass


def extract_stores(business_id, user_id, role, db):
    if role == RoleEnum.L1:
        stores = db.query(L0).filter(L0.user_id == user_id).all()

    elif role == RoleEnum.L2:
        pass
    elif role == RoleEnum.L3:
        pass

    elif role == RoleEnum.L4:
        pass