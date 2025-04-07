from fastapi import APIRouter, Depends
from firebase_admin import auth
from ..dependencies import get_current_user
import logging

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"],
)

logger = logging.getLogger(__name__)

@router.get("/me")
async def read_users_me(current_user: auth.UserRecord = Depends(get_current_user)):
    """
    Get the profile of the currently authenticated user.
    """
    logger.info(f"Fetching profile for user: {current_user.uid}")
    # Return relevant user information
    # Avoid returning sensitive info unless necessary
    return {
        "uid": current_user.uid,
        "email": current_user.email,
        "email_verified": current_user.email_verified,
        "display_name": current_user.display_name,
        "photo_url": current_user.photo_url,
        "disabled": current_user.disabled,
        "creation_timestamp": current_user.user_metadata.creation_timestamp,
        "last_sign_in_timestamp": current_user.user_metadata.last_sign_in_timestamp,
        # Add custom claims if you use them: "custom_claims": current_user.custom_claims 
    } 