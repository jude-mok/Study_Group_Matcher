from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class StudyGroupCreate(BaseModel):
    course_id: int = Field(..., description="course id")
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
    id: str
    course_id: int
    name: str
    max_members: int
    admin_id: Optional[str] = None
    location: Optional[str] = None
    created_at: Optional[datetime] = None
    current_members: Optional[int] = None

    class Config:
        from_attributes = True


class GroupMemberResponse(BaseModel):
    user_id: str
    role: str  # "admin" | "member"
    name: str
    nyu_email: str
    major: str
    academic_standing: int
    work_willingness: int
    avg_gpa: Optional[float] = None

    class Config:
        from_attributes = True


class StudyGroupJoin(BaseModel):
    role: str = Field(default="member", description="Role in the group: 'admin' or 'member'")


class StudyGroupRecommendation(BaseModel):
    id: str
    course_id: int
    name: str
    max_members: int
    location: Optional[str] = None
    created_at: Optional[datetime] = None
    current_members: int
    match_score: float = Field(..., description="Total match score (0-100)")
    score_breakdown: dict = Field(..., description="Score breakdown by factor")

    class Config:
        from_attributes = True
