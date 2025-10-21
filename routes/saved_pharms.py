from fastapi import APIRouter, HTTPException, status, Depends, Form
from typing import Annotated
from bson import ObjectId
from datetime import datetime, timezone
from db import saved_pharmacies_collection, pharmacies_collection, users_collection
from dependencies.authn import is_authenticated

saved_router = APIRouter(tags=["Saved Pharmacies"], prefix="/pharmacies")


# 1. Save a Pharmacy
@saved_router.post("/save")
def save_pharmacy(
    pharmacy_id: Annotated[str, Form(...)],
    user_id: Annotated[str, Depends(is_authenticated)],
):
    """
    Save (favorite) a pharmacy for the authenticated user.
    """

    # Check if pharmacy exists
    pharmacy = pharmacies_collection.find_one({"_id": ObjectId(pharmacy_id)})
    if not pharmacy:
        raise HTTPException(status_code=404, detail="Pharmacy not found")

    # Prevent duplicates
    existing = saved_pharmacies_collection.find_one(
        {"user_id": ObjectId(user_id), "pharmacy_id": ObjectId(pharmacy_id)}
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Pharmacy already saved.",
        )

    # Save it
    saved_pharmacies_collection.insert_one(
        {
            "user_id": ObjectId(user_id),
            "pharmacy_id": ObjectId(pharmacy_id),
            "saved_at": datetime.now(tz=timezone.utc),
        }
    )

    return {"message": "Pharmacy saved successfully"}


# 2. Unsave (remove) a saved pharmacy
@saved_router.delete("/unsave/{pharmacy_id}")
def unsave_pharmacy(
    pharmacy_id: str,
    user_id: Annotated[str, Depends(is_authenticated)],
):
    """
    Remove a saved pharmacy from user's favorites.
    """
    result = saved_pharmacies_collection.delete_one(
        {"user_id": ObjectId(user_id), "pharmacy_id": ObjectId(pharmacy_id)}
    )

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Pharmacy not found in saved list")

    return {"message": "Pharmacy removed from saved list"}


# 3. View all saved pharmacies
@saved_router.get("/saved")
def get_saved_pharmacies(
    user_id: Annotated[str, Depends(is_authenticated)],
):
    """
    Get all pharmacies saved by the authenticated user.
    """
    saved = list(saved_pharmacies_collection.find({"user_id": ObjectId(user_id)}))
    if not saved:
        raise HTTPException(status_code=404, detail="No saved pharmacies found")

    result = []
    for item in saved:
        pharmacy = pharmacies_collection.find_one({"_id": item["pharmacy_id"]})
        pharmacy_user_info = users_collection.find_one({"_id": pharmacy["user_id"]})
        if pharmacy:
            result.append(
                {
                    "pharmacy_id": str(pharmacy["_id"]),
                    "name": pharmacy.get("pharmacy_name"),
                    "email": pharmacy_user_info.get("email"),
                    "address": pharmacy.get("digital_address"),
                    "phone": pharmacy_user_info.get("phone"),
                    "saved_at": item["saved_at"].isoformat(),
                }
            )

    return {"saved_pharmacies": result}
