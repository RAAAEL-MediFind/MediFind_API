from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status
from typing import Annotated, Optional
from datetime import datetime, timezone
from bson import ObjectId
import cloudinary.uploader
from db import prescriptions_collection, pharmacies_collection
from dependencies.authn import is_authenticated
from dependencies.authz import has_roles

prescription_router = APIRouter(tags=["Prescription"], prefix="/prescriptions")


# 1️ Upload and send prescription (User → Pharmacy)
@prescription_router.post("/send")
def send_prescription_to_pharmacy(
    user_id: Annotated[str, Depends(is_authenticated)],
    pharmacy_id: Annotated[str, Form(...)],
    title: Annotated[str, Form(...)],
    file: Annotated[UploadFile, File(...)],
    notes: Annotated[Optional[str], Form()] = None,
):
    """
    Upload and send a prescription (image or PDF) to a selected pharmacy.
    """
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "application/pdf"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only JPG, PNG, or PDF are allowed.",
        )

    # Check if pharmacy exists
    pharmacy = pharmacies_collection.find_one({"_id": ObjectId(pharmacy_id)})
    if not pharmacy:
        raise HTTPException(status_code=404, detail="Pharmacy not found")

    # Upload to Cloudinary
    upload_result = cloudinary.uploader.upload(file.file)
    file_url = upload_result["secure_url"]

    # Save in MongoDB
    prescription_doc = {
        "user_id": ObjectId(user_id),
        "pharmacy_id": ObjectId(pharmacy_id),
        "title": title,
        "notes": notes,
        "file_url": file_url,
        "uploaded_at": datetime.now(tz=timezone.utc),
        "is_read": False,
    }
    prescriptions_collection.insert_one(prescription_doc)

    return {
        "message": "Prescription sent successfully to pharmacy",
        "file_url": file_url,
    }


# 2️ Get prescriptions sent by the authenticated user
@prescription_router.get("/my-prescriptions")
def get_user_prescriptions(user_id: Annotated[str, Depends(is_authenticated)]):
    """
    Get all prescriptions uploaded/sent by the authenticated user.
    """
    prescriptions = list(prescriptions_collection.find({"user_id": ObjectId(user_id)}))

    if not prescriptions:
        raise HTTPException(status_code=404, detail="No prescriptions found")

    result = []
    for p in prescriptions:
        result.append({
            "prescription_id": str(p["_id"]),
            "title": p["title"],
            "notes": p.get("notes"),
            "file_url": p["file_url"],
            "uploaded_at": p["uploaded_at"].isoformat(),
            "is_read": p.get("is_read", False),
        })

    return {"prescriptions": result}


# 3️ Pharmacy Inbox — View prescriptions sent to them
@prescription_router.get("/inbox/pharmacy")
def get_pharmacy_prescriptions(
    user_id: Annotated[str, Depends(is_authenticated)],
    _: Annotated[None, Depends(has_roles(["pharmacy"]))],
):
    """
    Pharmacy can view prescriptions sent to them by users.
    """
    pharmacy = pharmacies_collection.find_one({"user_id": ObjectId(user_id)})
    if not pharmacy:
        raise HTTPException(status_code=404, detail="Pharmacy not found")

    prescriptions = list(prescriptions_collection.find({"pharmacy_id": pharmacy["_id"]}))
    if not prescriptions:
        raise HTTPException(status_code=404, detail="No prescriptions found")

    result = []
    for p in prescriptions:
        result.append({
            "prescription_id": str(p["_id"]),
            "title": p["title"],
            "notes": p.get("notes"),
            "file_url": p["file_url"],
            "uploaded_at": p["uploaded_at"].isoformat(),
            "is_read": p.get("is_read", False),
        })

    return {"inbox": result}


# 4️ Pharmacy marks prescription as viewed/read
@prescription_router.patch("/{prescription_id}/read")
def mark_prescription_as_read(
    prescription_id: str,
    user_id: Annotated[str, Depends(is_authenticated)],
    _: Annotated[None, Depends(has_roles(["pharmacy"]))],
):
    """
    Mark a prescription as read/viewed by the pharmacy.
    """
    pharmacy = pharmacies_collection.find_one({"user_id": ObjectId(user_id)})
    if not pharmacy:
        raise HTTPException(status_code=404, detail="Pharmacy not found")

    result = prescriptions_collection.update_one(
        {"_id": ObjectId(prescription_id), "pharmacy_id": pharmacy["_id"]},
        {"$set": {"is_read": True}},
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Prescription not found or already marked read")

    return {"message": "Prescription marked as read"}
