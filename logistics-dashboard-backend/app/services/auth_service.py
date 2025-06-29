from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from typing import Optional

from app.models.user_model import Users
from app.schemas.user_schema import UserCreate, UserOut, TokenData
from app.core.security import get_password_hash, verify_password, create_access_token, decode_access_token
from app.core.config import settings

# OAuth2PasswordBearer scheme for token-based authentication
# tokenUrl should point to the login endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


async def get_user_by_email(email: str) -> Optional[Users]:
    """Fetches a user by email from the database."""
    return await Users.get_or_none(email=email)


async def create_new_user(user_in: UserCreate) -> Users:
    """Creates a new user in the database."""
    existing_user = await get_user_by_email(user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists.",
        )

    hashed_password = get_password_hash(user_in.password)

    # Create user instance. Ensure fields match the Users model.
    # UserCreate schema might not directly map all fields, handle explicitly.
    user_data = user_in.model_dump(exclude={"password"}) # Pydantic v2
    # user_data = user_in.dict(exclude={"password"}) # Pydantic v1

    new_user = await Users.create(
        **user_data,
        hashed_password=hashed_password,
        # Set defaults if not in UserCreate or handle them in the model
        is_active=True, # Default new users to active, or make it part of UserCreate
        is_superuser=False # Default new users to not superuser
    )
    return new_user


async def authenticate_user(email: str, password: str) -> Optional[Users]:
    """
    Authenticates a user by email and password.
    Returns the user object if authentication is successful, otherwise None.
    """
    user = await get_user_by_email(email)
    if not user:
        return None
    if not user.is_active: # Optional: check if user is active
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def get_current_user(token: str = Depends(oauth2_scheme)) -> Users:
    """
    Dependency to get the current authenticated user from a JWT token.
    To be used in protected API endpoints.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token_data = decode_access_token(token)
    if token_data is None or token_data.email is None: # Check if email exists in token
        raise credentials_exception

    user = await get_user_by_email(token_data.email)
    if user is None:
        raise credentials_exception
    if not user.is_active: # Optional: ensure the user is still active
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")

    return user


async def get_current_active_superuser(current_user: Users = Depends(get_current_user)) -> Users:
    """
    Dependency to get the current active superuser.
    If the user is not a superuser, it raises an HTTPException.
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user

# Helper to create token for a user
def generate_jwt_token_for_user(user_email: str) -> str:
    """Generates a JWT access token for a given user email."""
    # The subject ('sub') of the token is usually the user's ID or email.
    # Here, we use email as per TokenData and decode_access_token logic.
    access_token = create_access_token(data={"sub": user_email})
    return access_token
