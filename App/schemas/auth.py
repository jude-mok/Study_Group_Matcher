from pydantic import BaseModel, EmailStr
from typing import Optional
from schemas.user import User_Response

class Create_User(BaseModel):
    pass
    name: str
    nyu_email : EmailStr
    nyu_id : str
    password: str
    major: str
    minor: Optional[str] = None
    academic_standing: int
    work_willingness: int
    
class Login_Request(BaseModel):
    pass
    nyu_email : EmailStr
    password : str

class Token_Response(BaseModel):
    pass
    access_token : str
    token_type: str = "bearer"
    user: User_Response