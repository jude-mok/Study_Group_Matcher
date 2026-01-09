from pydantic import BaseModel, EmailStr
from typing import Optional

class User_Response(BaseModel):
    pass
    id: str
    name: str
    nyu_email : EmailStr
    nyu_id : str
    major: str
    minor: Optional[str] = None
    academic_standing: int
    work_willingness: int


class Update_User(BaseModel):
    name: Optional[str] = None
    password: Optional[str] = None
    major: Optional[str] = None
    minor: Optional[str] = None
    academic_standing: Optional[int]
    work_willingness: Optional[int]