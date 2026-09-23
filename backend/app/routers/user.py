from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.database import get_supabase_admin
from app.dependencies import get_current_user
from app.schemas.user import UserResponse, UserUpdate
from app.services.user_service import (
    get_user_by_id,
    update_user_in_db,
    update_user_password,
    delete_user_from_db
)
from app.services.utils import handle_route_errors


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: dict = Depends(get_current_user)
) -> UserResponse:
    pass
    return current_user


@router.get("/{user_id}", response_model=UserResponse)
@handle_route_errors
async def get_user_profile(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_admin)
) -> UserResponse:
    pass
    return get_user_by_id(supabase, user_id)


@router.put("/me", response_model=UserResponse)
@handle_route_errors
async def update_current_user_profile(
    user_update: UserUpdate,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_admin)
) -> UserResponse:
    pass
    update_data = user_update.model_dump(exclude_none=True)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )

    # Handle password update separately
    if "password" in update_data:
        password = update_data.pop("password")
        update_user_password(supabase, current_user["id"], password)

    # Update remaining fields in database
    if update_data:
        return update_user_in_db(supabase, current_user["id"], update_data)

    # If only password was updated, return refreshed user data
    return get_user_by_id(supabase, current_user["id"])


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
@handle_route_errors
async def delete_current_user(
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_admin)
):
    pass
    user_id = current_user["id"]

    # Delete all FK-referenced data before deleting the user
    # meeting_results references meeting_proposals, so delete results first
    proposals = supabase.table("meeting_proposals").select("id").eq("proposed_by", user_id).execute()
    proposal_ids = [p["id"] for p in (proposals.data or [])]
    if proposal_ids:
        supabase.table("meeting_results").delete().in_("proposal_id", proposal_ids).execute()
    supabase.table("meeting_votes").delete().eq("user_id", user_id).execute()
    supabase.table("meeting_proposals").delete().eq("proposed_by", user_id).execute()
    supabase.table("messages").delete().eq("sender_id", user_id).execute()
    supabase.table("room_members").delete().eq("user_id", user_id).execute()
    supabase.table("group_join_requests").delete().eq("user_id", user_id).execute()
    supabase.table("user_study_groups").delete().eq("user_id", user_id).execute()
    supabase.table("schedule").delete().eq("created_by", user_id).execute()
    supabase.table("user_courses").delete().eq("user_id", user_id).execute()

    from app.routers.chat import manager
    await manager.revoke_user(user_id)

    # Delete from users table
    delete_user_from_db(supabase, user_id)

    # Delete from auth
    try:
        supabase.auth.admin.delete_user(user_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"User removed from database but auth deletion failed: {str(e)}"
        )
