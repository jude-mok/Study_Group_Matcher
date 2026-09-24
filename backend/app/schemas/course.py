from pydantic import BaseModel, Field


class CourseCreate(BaseModel):
    course_code: str = Field(..., min_length=1, description="Course code (e.g., CS-UY 1134)")
    course_name: str = Field(..., min_length=1, description="Course name")

    class Config:
        json_schema_extra = {
            "example": {
                "course_code": "CSCI102",
                "course_name": "Data Structures and Algorithms"
            }
        }


class CourseResponse(BaseModel):
    id: int
    course_code: str
    course_name: str

    class Config:
        from_attributes = True


# Keep aliases for backward compatibility
Create_Course = CourseCreate
Course_Response = CourseResponse
