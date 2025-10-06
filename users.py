from enum import Enum
from fastapi import APIRouter, Form, status, HTTPException
from typing import Annotated
from pydantic import EmailStr
from db import users_collection
import bcrypt
import jwt
import os
from datetime import timezone, datetime, timedelta


class UserRole(str, Enum):
    ADMIN = "admin"
    PHARMACY = "pharmacy"
    PATIENT = "patient"


# Create users router
users_router = APIRouter(tags=["Users"])


# Defining endpoints for users
@users_router.post("/users/register")
def register_users(
    email: Annotated[EmailStr, Form()],
    password: Annotated[str, Form(min_length=8)],
    username: Annotated[str, Form()],
    phone: Annotated[str, Form()],
    role: Annotated[UserRole, Form()] = UserRole.PATIENT,
):
    # ensure user does not exist in db
    user_count = users_collection.count_documents(filter={"email": email})
    if user_count > 0:
        raise HTTPException(status.HTTP_409_CONFLICT, "User Already Exist!")
    # Hash user password
    hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    # Save user into database
    users_collection.insert_one(
        {
            "email": email,
            "password": hashed_password.decode(),
            "username": username,
            "phone": phone,
            "role": role,
        }
    )
    # Return response
    return {"Message": "User registered successfully!"}
