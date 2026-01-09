from pydantic import BaseModel

class Create_Course(BaseModel):
    pass
    course_code : str
    course_name : str
    course_section : int

class Course_Response(BaseModel):
    pass
    id : int
    course_code : str
    course_name : str
    course_section : int