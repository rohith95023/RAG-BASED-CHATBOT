"""
Authentication service for PDF RAG Chatbot application.
Provides JWT token management, password hashing, and user authentication.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from config.settings import Settings
from database.repositories import UserRepository
from utils.logger import get_logger


logger = get_logger(__name__)


class AuthService:
    """Service for authentication and authorization operations"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a plain password against a hashed password.

        Args:
            plain_password: Plain text password
            hashed_password: Bcrypt hashed password

        Returns:
            True if password matches, False otherwise
        """
        try:
            return self.pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            logger.error(f"Password verification failed: {e}")
            return False

    def get_password_hash(self, password: str) -> str:
        """
        Hash a password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Hashed password
        """
        try:
            return self.pwd_context.hash(password)
        except Exception as e:
            logger.error(f"Password hashing failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process password"
            )

    def create_access_token(self, data: Dict[str, Any],
                           expires_delta: Optional[timedelta] = None) -> str:
        """
        Create JWT access token.

        Args:
            data: Data to encode in token (typically user identifier)
            expires_delta: Optional custom expiration time

        Returns:
            JWT access token
        """
        try:
            to_encode = data.copy()

            # Set expiration time
            if expires_delta:
                expire = datetime.utcnow() + expires_delta
            else:
                expire = datetime.utcnow() + timedelta(
                    minutes=self.settings.ACCESS_TOKEN_EXPIRE_MINUTES
                )

            to_encode.update({
                "exp": expire,
                "iat": datetime.utcnow(),
                "type": "access",
                "app": self.settings.APP_NAME
            })

            # Encode token
            token = jwt.encode(
                to_encode,
                self.settings.JWT_SECRET_KEY,
                algorithm=self.settings.JWT_ALGORITHM
            )

            logger.info(f"Created access token for user: {data.get('sub', 'unknown')}")
            return token

        except Exception as e:
            logger.error(f"Access token creation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create access token"
            )

    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """
        Create JWT refresh token.

        Args:
            data: Data to encode in token (typically user identifier)

        Returns:
            JWT refresh token
        """
        try:
            to_encode = data.copy()

            # Set longer expiration for refresh token
            expire = datetime.utcnow() + timedelta(
                days=self.settings.REFRESH_TOKEN_EXPIRE_DAYS
            )

            to_encode.update({
                "exp": expire,
                "iat": datetime.utcnow(),
                "type": "refresh",
                "app": self.settings.APP_NAME
            })

            # Encode token
            token = jwt.encode(
                to_encode,
                self.settings.JWT_SECRET_KEY,
                algorithm=self.settings.JWT_ALGORITHM
            )

            logger.info(f"Created refresh token for user: {data.get('sub', 'unknown')}")
            return token

        except Exception as e:
            logger.error(f"Refresh token creation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create refresh token"
            )

    def decode_token(self, token: str) -> Dict[str, Any]:
        """
        Decode and validate JWT token.

        Args:
            token: JWT token to decode

        Returns:
            Decoded token payload

        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token,
                self.settings.JWT_SECRET_KEY,
                algorithms=[self.settings.JWT_ALGORITHM]
            )

            # Validate token structure
            if "sub" not in payload:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: missing subject"
                )

            if "type" not in payload:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: missing type"
                )

            # Validate app name
            if payload.get("app") != self.settings.APP_NAME:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: wrong application"
                )

            return payload

        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        except Exception as e:
            logger.error(f"Token decoding failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token validation failed"
            )

    async def get_current_user(self, token: str, user_repo: UserRepository) -> Dict[str, Any]:
        """
        Get current authenticated user from token.

        Args:
            token: JWT access token
            user_repo: User repository instance

        Returns:
            User dictionary

        Raises:
            HTTPException: If token is invalid or user not found
        """
        # Decode token
        payload = self.decode_token(token)

        # Validate token type
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type: expected access token"
            )

        # Get user identifier
        user_identifier = payload.get("sub")
        if not user_identifier:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user identifier"
            )

        # Check if identifier is username or email
        # Try username first, then email
        user = await user_repo.get_by_username(user_identifier)
        if not user:
            user = await user_repo.get_by_email(user_identifier)

        if not user:
            logger.warning(f"User not found: {user_identifier}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        # Check if user is active
        if not user.get("is_active", True):
            logger.warning(f"Inactive user attempt: {user_identifier}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled"
            )

        logger.info(f"Successfully authenticated user: {user.get('username')}")
        return user

    async def register_user(self, username: str, email: str, password: str,
                          user_repo: UserRepository, role: str = "user") -> Dict[str, Any]:
        """
        Register a new user.

        Args:
            username: Desired username
            email: User email address
            password: Plain text password
            user_repo: User repository instance
            role: User role (default: "user")

        Returns:
            Created user dictionary

        Raises:
            HTTPException: If registration fails
        """
        try:
            # Check if username already exists
            if await user_repo.username_exists(username):
                logger.warning(f"Registration attempt with existing username: {username}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already exists"
                )

            # Check if email already exists
            if await user_repo.email_exists(email):
                logger.warning(f"Registration attempt with existing email: {email}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )

            # Hash password
            hashed_password = self.get_password_hash(password)

            # Create user
            user_id = await user_repo.create_user(
                username=username,
                email=email,
                hashed_password=hashed_password,
                role=role
            )

            # Get created user
            user = await user_repo.get_by_id(user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create user"
                )

            logger.info(f"Successfully registered user: {username}")
            return user

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"User registration failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Registration failed"
            )

    async def authenticate_user(self, username: str, password: str,
                             user_repo: UserRepository) -> Optional[Dict[str, Any]]:
        """
        Authenticate user with credentials.

        Args:
            username: Username or email
            password: Plain text password
            user_repo: User repository instance

        Returns:
            User dictionary if authentication successful, None otherwise
        """
        try:
            # Find user by username or email
            user = await user_repo.get_by_username(username)
            if not user:
                user = await user_repo.get_by_email(username)

            if not user:
                logger.warning(f"Authentication failed: user not found - {username}")
                return None

            # Verify password
            if not self.verify_password(password, user.get("hashed_password", "")):
                logger.warning(f"Authentication failed: invalid password - {username}")
                return None

            # Check if user is active
            if not user.get("is_active", True):
                logger.warning(f"Authentication failed: user disabled - {username}")
                return None

            # Update last login
            await user_repo.update_last_login(user["_id"])

            logger.info(f"Successfully authenticated user: {username}")
            return user

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None

    async def refresh_access_token(self, refresh_token: str,
                                 user_repo: UserRepository) -> str:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: JWT refresh token
            user_repo: User repository instance

        Returns:
            New access token

        Raises:
            HTTPException: If refresh token is invalid
        """
        try:
            # Decode refresh token
            payload = self.decode_token(refresh_token)

            # Validate token type
            if payload.get("type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type: expected refresh token"
                )

            # Get user identifier
            user_identifier = payload.get("sub")
            if not user_identifier:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: missing user identifier"
                )

            # Get user
            user = await user_repo.get_by_username(user_identifier)
            if not user:
                user = await user_repo.get_by_email(user_identifier)

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )

            # Check if user is still active
            if not user.get("is_active", True):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User account is disabled"
                )

            # Create new access token
            access_token = self.create_access_token(
                data={"sub": user_identifier}
            )

            logger.info(f"Refreshed access token for user: {user_identifier}")
            return access_token

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to refresh token"
            )

    def get_token_expires_in(self, token_type: str = "access") -> int:
        """
        Get token expiration time in seconds.

        Args:
            token_type: Type of token ("access" or "refresh")

        Returns:
            Expiration time in seconds
        """
        if token_type == "access":
            return self.settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        else:
            return self.settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

    def create_token_response(self, user_identifier: str) -> Dict[str, Any]:
        """
        Create complete token response with access and refresh tokens.

        Args:
            user_identifier: User username or email

        Returns:
            Dictionary with access_token, refresh_token, token_type, expires_in
        """
        access_token = self.create_access_token(
            data={"sub": user_identifier}
        )
        refresh_token = self.create_refresh_token(
            data={"sub": user_identifier}
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": self.get_token_expires_in("access")
        }