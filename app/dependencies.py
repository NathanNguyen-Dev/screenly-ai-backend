from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from firebase_admin import auth
# Import specific exceptions directly from firebase_admin.auth
from firebase_admin.auth import InvalidIdTokenError, ExpiredIdTokenError
import logging

# Setup logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# This scheme expects the token to be sent in the Authorization header
# as 'Bearer <token>'
# The tokenUrl is not actually used here for verification but is part of the OpenAPI spec
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> auth.UserRecord:
    """
    Dependency function to verify Firebase ID token and get user data.
    
    Raises:
        HTTPException: 401 Unauthorized if token is invalid, expired, or missing.
    
    Returns:
        auth.UserRecord: The decoded Firebase user record.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Verify the ID token while checking for revocation.
        decoded_token = auth.verify_id_token(token, check_revoked=True)
        uid = decoded_token.get("uid")
        if not uid:
            logger.warning("UID not found in decoded token.")
            raise credentials_exception
        
        # Optionally, you could fetch the full UserRecord here if needed elsewhere,
        # but often the UID from the decoded token is sufficient for ownership checks.
        # user = auth.get_user(uid)
        # return user 

        # For now, returning the decoded token dictionary might be simpler if we just need UID
        # Or construct a simple object/dataclass if preferred
        # Returning the full UserRecord as per type hint for consistency:
        user_record = auth.get_user(uid)
        logger.info(f"Authenticated user: {user_record.uid}")
        return user_record

    except InvalidIdTokenError as e:
        logger.error(f"Invalid ID token: {e}")
        raise credentials_exception from e
    except ExpiredIdTokenError as e:
        logger.error(f"Expired ID token: {e}")
        raise credentials_exception from e
    except Exception as e:
        # Catch any other auth or unexpected errors during verification/fetch
        logger.error(f"Authentication error: {e}")
        raise credentials_exception from e

# Example of a stricter dependency that checks for a specific role (if needed later)
# async def get_current_admin_user(current_user: auth.UserRecord = Depends(get_current_user)):
#     if not current_user.custom_claims or current_user.custom_claims.get("role") != "admin":
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
#     return current_user 