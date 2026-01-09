from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class User_Course_Create(BaseModel):
    pass
    nyu_id: str
    course_id: int
    course_section : int
    semester: str
    current_course_time_start : datetime
    current_course_time_end : datetime

class User_Course_Response(BaseModel):
    pass
    nyu_id: str
    course_id: int
    semester: str
    sectcourse_section : int
    current_course_time_start : datetime
    current_course_time_end : datetime
    created_at: Optional[datetime] = None