from enum import Enum
from fastapi import APIRouter, Form, status, HTTPException, UploadFile, File, Depends
from typing import Annotated
from pydantic import EmailStr
from db import users_collection, pharmacies_collection
import bcrypt
import jwt
from dotenv import load_dotenv
import os
from datetime import timezone, datetime, timedelta
from bson import ObjectId
import cloudinary
import cloudinary.uploader


load_dotenv()
# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)


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
    flyer: Annotated[UploadFile, File()] = None,
    digital_address: Annotated[str | None, Form()] = None,
    latitude: Annotated[float | None, Form()] = None,
    longitude: Annotated[float | None, Form()] = None,
):
    # ensure user does not exist in db
    user_count = users_collection.count_documents(filter={"email": email})
    if user_count > 0:
        raise HTTPException(status.HTTP_409_CONFLICT, "User Already Exists!")
    # Hash user password
    hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    # Create a base user data
    user_doc = {
        "email": email,
        "password": hashed_password.decode(),
        "username": username,
        "phone": phone,
        "role": role,
        "created_at": datetime.now(tz=timezone.utc),
    }
    # Insert user into users_collection in database
    result = users_collection.insert_one(user_doc)
    user_id = result.inserted_id
    # If user is a pharmacy, save the additional pharmacy data
    if role == UserRole.PHARMACY:
        if not all([flyer, digital_address, latitude, longitude]):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Pharmacy Should Provide Digital Address, GPS Location and Flyer",
            )
        # Upload flyer to cloudinary to get a url to be stored in mongo db
        upload_result = cloudinary.uploader.upload(flyer.file)
        print(upload_result)
        pharmacies_collection.insert_one(
            {
                "user_id": ObjectId(user_id),
                "pharmacy_name": username,
                "flyer": upload_result["secure_url"],
                "digital_address": digital_address,
                "gps_location": {"lat": latitude, "lon": longitude},
                "created_at": datetime.now(tz=timezone.utc),
            }
        )
    # Return response
    return {"Message": f"{role.capitalize()} registered successfully!"}


@users_router.post("/users/login")
def login_user(email: Annotated[EmailStr, Form()], password: Annotated[str, Form()]):

    # Ensure user does not exist
    user = users_collection.find_one(filter={"email": email})
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User Not Found!")
    # Compare their passwords
    hashed_password_in_db = user["password"]
    correct_password = bcrypt.checkpw(password.encode(), hashed_password_in_db.encode())
    if not correct_password:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid login Credentials")
    # Generate an access token for users
    encoded_jwt = jwt.encode(
        {
            "id": str(user["_id"]),
            "exp": datetime.now(tz=timezone.utc) + timedelta(minutes=60),
        },
        os.getenv("JWT_SECRET_KEY"),
        "HS256",
    )

    return {"Message": "User logged in successfully!", "access_token": encoded_jwt}
