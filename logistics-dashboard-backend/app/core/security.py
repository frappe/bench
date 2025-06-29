from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.schemas.user_schema import TokenData

# Password hashing context
# Using bcrypt as the default hashing scheme
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hashes a plain password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Creates a JWT access token.
    The 'data' dictionary is encoded into the token.
    'expires_delta' can specify a custom token lifetime.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    # 'sub' (subject) is a standard claim, often user ID or email
    if "sub" not in to_encode and "email" in to_encode:
        to_encode["sub"] = to_encode["email"]

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[TokenData]:
    """
    Decodes a JWT access token.
    Returns TokenData if the token is valid, otherwise None or raises JWTError.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: Optional[str] = payload.get("sub") # Assuming 'sub' holds the email
        if email is None:
            # Could raise an exception or return None based on desired error handling
            # For now, let's rely on TokenData validation if email is optional there
            pass

        # You might want to add more validation here, e.g., checking token type, jti, etc.

        token_data = TokenData(email=email) # Or however TokenData is structured
        return token_data
    except JWTError:
        # This could be due to token expiration, invalid signature, etc.
        # Consider logging the error for debugging.
        # raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
        return None

# Example of how to generate a strong secret key:
# import secrets
# secrets.token_urlsafe(32)
# Store this in your .env file for SECRET_KEY
# Make sure it's not committed to version control if it's the actual production key.
