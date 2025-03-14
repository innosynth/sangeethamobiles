from pydantic import BaseModel
from typing import Optional

class LoginSchema(BaseModel):
    email: str
    password: str

