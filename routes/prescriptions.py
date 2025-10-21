from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status
from typing import Annotated, Optional
from datetime import datetime, timezone
from bson import ObjectId
import cloudinary.uploader
from db import prescriptions_collection
from dependencies.authn import is_authenticated

prescription_router = APIRouter(tags=["Prescription"], prefix="/prescriptions")


@prescription_router.post("/upload")
def upload_prescription(
    user_id: Annotated[str, Depends(is_authenticated)],
    title: Annotated[str, Form(...)],
    file: Annotated[UploadFile, File(...)],
    notes: Annotated[Optional[str], Form()]=None,
):
    """
    Upload a prescription (image or PDF) for the authenticated user.
    """
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "application/pdf"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only JPG, PNG, or PDF are allowed.",
        )

    # Upload to Cloudinary or store file info (use local later if preferred)
    upload_result = cloudinary.uploader.upload(file.file)
    file_url = upload_result["secure_url"]

    # Save in MongoDB
    prescription_doc = {
        "user_id": ObjectId(user_id),
        "title": title,
        "notes": notes,
        "file_url": file_url,
        "uploaded_at": datetime.now(tz=timezone.utc),
    }
    prescriptions_collection.insert_one(prescription_doc)

    return {"message": "Prescription uploaded successfully", "file_url": file_url}


@prescription_router.get("/my-prescriptions")
def get_user_prescriptions(user_id: Annotated[str, Depends(is_authenticated)]):
    """
    Get all prescriptions uploaded by the authenticated user.
    """
    prescriptions = list(
        prescriptions_collection.find({"user_id": ObjectId(user_id)})
    )

    if not prescriptions:
        raise HTTPException(status_code=404, detail="No prescriptions found")

    for p in prescriptions:
        p["_id"] = str(p["_id"])
        p["user_id"] = str(p["user_id"])
        p["uploaded_at"] = p["uploaded_at"].isoformat()

    return {"prescriptions": prescriptions}

# 
# Get a specific prescription by ID
@prescription_router.get("/{prescription_id}")
def get_prescription_by_id(
    prescription_id: str,
    user_id: Annotated[str, Depends(is_authenticated)],
):
    """
    Get a specific prescription by its ID for the authenticated user.
    """
    prescription = prescriptions_collection.find_one(
        {"_id": ObjectId(prescription_id), "user_id": ObjectId(user_id)}
    )

    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")

    prescription["_id"] = str(prescription["_id"])
    prescription["user_id"] = str(prescription["user_id"])
    prescription["uploaded_at"] = prescription["uploaded_at"].isoformat()

    return {"prescription": prescription}