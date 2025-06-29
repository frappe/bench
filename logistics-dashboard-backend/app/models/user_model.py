from tortoise import fields, models
from tortoise.contrib.pydantic import pydantic_model_creator

class Users(models.Model):
    """
    User model for authentication and authorization.
    """
    id = fields.IntField(pk=True)
    email = fields.CharField(max_length=100, unique=True, index=True, description="User's email address")
    hashed_password = fields.CharField(max_length=255, description="Hashed password")

    full_name = fields.CharField(max_length=100, null=True, description="User's full name")
    is_active = fields.BooleanField(default=True, description="Whether the user account is active")
    is_superuser = fields.BooleanField(default=False, description="Whether the user has superuser privileges")

    # Using role as a simple string for now. Could be a ForeignKey to a Roles table later.
    role = fields.CharField(max_length=50, default="user", description="User role (e.g., 'user', 'admin', 'manager')")

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    def __str__(self):
        return self.email

# Pydantic model for API responses (excluding sensitive fields like hashed_password)
# This can also be defined in schemas, but often convenient here or in a dedicated pydantic_models.py
UserPydantic = pydantic_model_creator(Users, name="User", exclude=("hashed_password",))
UserInPydantic = pydantic_model_creator(Users, name="UserIn", exclude_readonly=True, exclude=("id", "created_at", "updated_at", "is_active", "is_superuser")) # For creation, might need adjustment
UserCreatePydantic = pydantic_model_creator(Users, name="UserCreate", include=("email", "full_name", "role")) # Schema for creating a user, password handled separately.

# We will likely define more specific schemas in app/schemas/user_schema.py
# For example, UserCreate will need a password field not directly in the model.
