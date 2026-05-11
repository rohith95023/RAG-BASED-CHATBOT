"""
Authentication API routes for PDF RAG Chatbot application.
Provides endpoints for user registration, login, token management.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import Dict, Any
from models.schemas import (
    UserCreate, UserResponse, Token, TokenRefresh, PasswordChange,
    UserUpdate, ErrorResponse
)
from services.auth_service import AuthService
from database.repositories import UserRepository, UserSettingsRepository
from api.dependencies import (
    get_settings, get_auth_service, get_user_repository,
    get_current_user, get_current_active_user, get_user_settings_repository
)
from utils.logger import get_logger


logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    auth_service: AuthService = Depends(get_auth_service),
    user_repo: UserRepository = Depends(get_user_repository),
    settings_repo: UserSettingsRepository = Depends(get_user_settings_repository)
):
    """
    Register a new user account.

    - **username**: Unique username (3-20 characters)
    - **email**: Valid email address
    - **password**: Strong password (8+ characters, mixed case, numbers, special chars)
    - **confirm_password**: Password confirmation
    """
    try:
        logger.info(f"Registration attempt for username: {user_data.username}")

        # Register user
        user = await auth_service.register_user(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            user_repo=user_repo
        )

        # Create default settings for user
        await settings_repo.create_default_settings(user["_id"])

        logger.info(f"Successfully registered user: {user_data.username}")

        return UserResponse(
            id=user["_id"],
            username=user["username"],
            email=user["email"],
            role=user.get("role", "user"),
            is_active=user.get("is_active", True),
            created_at=user.get("created_at"),
            last_login=user.get("last_login"),
            preferences=user.get("preferences", {})
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed due to server error"
        )


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """
    Authenticate user and issue tokens.

    - **username**: Username or email address
    - **password**: User password

    Returns access token and refresh token for API authentication.
    """
    try:
        logger.info(f"Login attempt for user: {form_data.username}")

        # Authenticate user
        user = await auth_service.authenticate_user(
            username=form_data.username,
            password=form_data.password,
            user_repo=user_repo
        )

        if not user:
            logger.warning(f"Failed login attempt: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # Generate tokens
        token_response = auth_service.create_token_response(user["username"])

        logger.info(f"Successful login: {user['username']}")

        return Token(
            access_token=token_response["access_token"],
            refresh_token=token_response["refresh_token"],
            token_type=token_response["token_type"],
            expires_in=token_response["expires_in"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed due to server error"
        )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_data: TokenRefresh,
    auth_service: AuthService = Depends(get_auth_service),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """
    Refresh access token using refresh token.

    - **refresh_token**: Valid refresh token

    Returns new access token and refresh token.
    """
    try:
        logger.info("Token refresh request")

        # Refresh access token
        new_access_token = await auth_service.refresh_access_token(
            refresh_token=refresh_data.refresh_token,
            user_repo=user_repo
        )

        # Create new refresh token for rotation
        # Get user identifier from old token
        payload = auth_service.decode_token(refresh_data.refresh_token)
        user_identifier = payload.get("sub")

        # Create new token response
        token_response = auth_service.create_token_response(user_identifier)
        token_response["access_token"] = new_access_token  # Use the validated new access token

        logger.info("Token refresh successful")

        return Token(
            access_token=token_response["access_token"],
            refresh_token=token_response["refresh_token"],
            token_type=token_response["token_type"],
            expires_in=token_response["expires_in"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to refresh token"
        )


@router.post("/logout")
async def logout(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Logout current user.

    - **Authorization**: Bearer token (required)

    In a stateless JWT system, logout is primarily client-side
    (deleting the token). This endpoint can be used for:
    - Logging the logout event
    - Token blacklisting (if implemented)
    - Cleanup of server-side session data
    """
    try:
        logger.info(f"User logout: {current_user.get('username')}")

        # In a basic JWT implementation, we don't need to do much server-side
        # In production, you might:
        # - Add token to blacklist
        # - Invalidate refresh tokens
        # - Log the logout event

        return {
            "message": "Successfully logged out",
            "username": current_user.get("username")
        }

    except Exception as e:
        logger.error(f"Logout error: {e}")
        # Don't fail the logout, just log the error
        return {
            "message": "Logout completed with warnings",
            "username": current_user.get("username")
        }


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get current authenticated user profile.

    - **Authorization**: Bearer token (required)

    Returns the user's profile information excluding sensitive data.
    """
    try:
        logger.info(f"Profile request: {current_user.get('username')}")

        return UserResponse(
            id=current_user["_id"],
            username=current_user["username"],
            email=current_user["email"],
            role=current_user.get("role", "user"),
            is_active=current_user.get("is_active", True),
            created_at=current_user.get("created_at"),
            last_login=current_user.get("last_login"),
            preferences=current_user.get("preferences", {})
        )

    except Exception as e:
        logger.error(f"Profile fetch error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user profile"
        )


@router.put("/me", response_model=UserResponse)
async def update_profile(
    profile_update: UserUpdate,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """
    Update current user profile.

    - **Authorization**: Bearer token (required)
    - **email**: New email address (optional)
    - **preferences**: User preferences dictionary (optional)

    Allows updating email and preferences.
    """
    try:
        logger.info(f"Profile update request: {current_user.get('username')}")

        user_id = current_user["_id"]

        # Prepare update data
        update_data = {}
        if profile_update.email is not None:
            update_data["email"] = profile_update.email

        if profile_update.preferences is not None:
            update_data["preferences"] = profile_update.preferences

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )

        # Update user
        success = await user_repo.update(user_id, update_data)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update profile"
            )

        # Get updated user
        updated_user = await user_repo.get_by_id(user_id)

        logger.info(f"Profile updated: {current_user.get('username')}")

        return UserResponse(
            id=updated_user["_id"],
            username=updated_user["username"],
            email=updated_user["email"],
            role=updated_user.get("role", "user"),
            is_active=updated_user.get("is_active", True),
            created_at=updated_user.get("created_at"),
            last_login=updated_user.get("last_login"),
            preferences=updated_user.get("preferences", {})
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Profile update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profile update failed"
        )


@router.post("/change-password")
async def change_password(
    password_change: PasswordChange,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """
    Change current user password.

    - **Authorization**: Bearer token (required)
    - **current_password**: Current password for verification
    - **new_password**: New password (same strength requirements as registration)
    - **confirm_password**: Confirmation of new password

    Changes the user's password after verifying the current one.
    """
    try:
        logger.info(f"Password change request: {current_user.get('username')}")

        # Verify current password
        if not auth_service.verify_password(
            password_change.current_password,
            current_user.get("hashed_password", "")
        ):
            logger.warning(f"Failed password change: incorrect current password - {current_user.get('username')}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect"
            )

        # Hash new password
        hashed_password = auth_service.get_password_hash(password_change.new_password)

        # Update password
        success = await user_repo.update_password(current_user["_id"], hashed_password)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to change password"
            )

        logger.info(f"Password changed successfully: {current_user.get('username')}")

        return {
            "message": "Password changed successfully",
            "username": current_user.get("username")
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )


@router.get("/verify-token")
async def verify_token(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Verify if current access token is valid.

    - **Authorization**: Bearer token (required)

    Returns user information if token is valid.
    """
    try:
        logger.info(f"Token verification: {current_user.get('username')}")

        return {
            "valid": True,
            "user": {
                "id": current_user["_id"],
                "username": current_user["username"],
                "email": current_user["email"],
                "role": current_user.get("role", "user")
            }
        }

    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return {
            "valid": False,
            "error": "Token verification failed"
        }