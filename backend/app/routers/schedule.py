from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.database import get_supabase_admin
from app.dependencies import get_current_user
from app.schemas.schedule import ScheduleCreate, ScheduleResponse, ScheduleUpdate
from app.services.schedule_service import (
    assert_group_member,
    assert_schedule_owner,
    get_schedule_by_id,
)
from app.services.utils import handle_route_errors


router = APIRouter(prefix="/schedules", tags=["schedules"])


def _as_datetime(value: datetime | str) -> datetime:
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value


def _validate_time_range(start_time: datetime, end_time: datetime) -> None:
    if start_time >= end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_time must be after start_time",
        )


@router.get("/me", response_model=List[ScheduleResponse])
@handle_route_errors
async def get_my_schedules(
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_admin),
) -> List[ScheduleResponse]:
    result = (
        supabase.table("schedule")
        .select("*")
        .eq("created_by", current_user["id"])
        .is_("group_id", "null")
        .order("start_time")
        .execute()
    )
    return result.data or []


@router.get("/group/{group_id}", response_model=List[ScheduleResponse])
@handle_route_errors
async def get_group_schedules(
    group_id: str,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_admin),
) -> List[ScheduleResponse]:
    assert_group_member(supabase, group_id, current_user["id"])

    result = (
        supabase.table("schedule")
        .select("*")
        .eq("group_id", group_id)
        .order("start_time")
        .execute()
    )
    return result.data or []


@router.get("/{schedule_id}", response_model=ScheduleResponse)
@handle_route_errors
async def get_schedule(
    schedule_id: str,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_admin),
) -> ScheduleResponse:
    schedule = get_schedule_by_id(supabase, schedule_id)

    if schedule["group_id"]:
        assert_group_member(supabase, schedule["group_id"], current_user["id"])
    elif schedule["created_by"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this schedule",
        )

    return schedule


@router.post("/", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
@handle_route_errors
async def create_schedule(
    request: ScheduleCreate,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_admin),
) -> ScheduleResponse:
    _validate_time_range(request.start_time, request.end_time)

    if request.group_id:
        assert_group_member(supabase, request.group_id, current_user["id"])

    data = request.model_dump(mode="json")
    data["created_by"] = current_user["id"]

    result = supabase.table("schedule").insert(data).execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create schedule",
        )

    return result.data[0]


@router.put("/{schedule_id}", response_model=ScheduleResponse)
@handle_route_errors
async def update_schedule(
    schedule_id: str,
    request: ScheduleUpdate,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_admin),
) -> ScheduleResponse:
    schedule = get_schedule_by_id(supabase, schedule_id)
    assert_schedule_owner(schedule, current_user["id"])

    update_data = request.model_dump(mode="json", exclude_none=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    start_time = request.start_time or _as_datetime(schedule["start_time"])
    end_time = request.end_time or _as_datetime(schedule["end_time"])
    _validate_time_range(start_time, end_time)

    result = (
        supabase.table("schedule")
        .update(update_data)
        .eq("id", schedule_id)
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update schedule",
        )

    return result.data[0]


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_route_errors
async def delete_schedule(
    schedule_id: str,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_admin),
) -> None:
    schedule = get_schedule_by_id(supabase, schedule_id)
    assert_schedule_owner(schedule, current_user["id"])

    supabase.table("schedule").delete().eq("id", schedule_id).execute()
