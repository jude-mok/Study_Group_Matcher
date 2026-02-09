from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class StudyGroupCreate(BaseModel):
    pass
    course_id: str = Field(..., description="class code of the course")
    name: str = Field(..., min_length=1, description="Study group name")
    max_members: int = Field(ge=2, description="Maximum number of members")
    location: Optional[str] = Field(None, description="Meeting location")

    class Config:
        json_schema_extra = {
            "example": {
                "course_id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "DS&A Study Group A",
                "max_members": 4,
                "location": "Dibner Library 2nd Floor"
            }
        }


class StudyGroupResponse(BaseModel):
    pass
    id: str
    course_id: str
    name: str
    members: int
    location: Optional[str] = None
    created_at: Optional[datetime] = None
    current_members: Optional[int] = None

    class Config:
        from_attributes = True


class StudyGroupJoin(BaseModel):
    pass
    role: str = Field(default="member", description="Role in the group: 'admin' or 'member'")
