from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm # For form data login

from app.schemas.user_schema import UserCreate, UserOut, Token
from app.services.auth_service import create_new_user, authenticate_user, get_current_user, generate_jwt_token_for_user
from app.models.user_model import Users # For type hinting with Depends(get_current_user)

router = APIRouter()

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register_user(user_in: UserCreate):
    """
    Register a new user.
    """
    # Service function handles email uniqueness check and password hashing.
    try:
        new_user = await create_new_user(user_in)
        # Convert Tortoise model instance to Pydantic schema for response
        return UserOut.model_validate(new_user) # Pydantic v2
        # return UserOut.from_orm(new_user) # Pydantic v1
    except HTTPException as e:
        # Re-raise HTTPExceptions (e.g., user already exists)
        raise e
    except Exception as e:
        # Catch any other unexpected errors during user creation
        # Log the error e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during user registration: {str(e)}",
        )


@router.post("/login", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Log in a user and return an access token.
    Uses OAuth2PasswordRequestForm for username (email) and password from form data.
    """
    user = await authenticate_user(email=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = generate_jwt_token_for_user(user_email=user.email)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/users/me", response_model=UserOut)
async def read_users_me(current_user: Users = Depends(get_current_user)):
    """
    Get details of the currently authenticated user.
    """
    # The get_current_user dependency already fetches and validates the user.
    # Convert Tortoise model instance to Pydantic schema for response
    return UserOut.model_validate(current_user) # Pydantic v2
    # return UserOut.from_orm(current_user) # Pydantic v1


# Example of a superuser-only route (can be in a different router too)
# from app.services.auth_service import get_current_active_superuser
# @router.get("/admin/check", response_model=UserOut)
# async def check_admin_access(current_admin: Users = Depends(get_current_active_superuser)):
#     """
#     Check if the current user is an admin. Only accessible by superusers.
#     """
#     return UserOut.model_validate(current_admin)
