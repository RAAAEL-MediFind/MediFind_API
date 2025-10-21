from fastapi import APIRouter, HTTPException, status
from db import med_inventory_collection, pharmacies_collection
from bson import ObjectId

count_router = APIRouter(tags=["Counts"])


# Get total count of all medicines
@count_router.get("/meds/all/count")
def get_meds_count():
    meds_count = med_inventory_collection.count_documents(filter={})
    return {"data": meds_count}


# Get total count of medicines added by a specific pharmacy
@count_router.get("/pharmacy/{pharmacy_id}/meds/count")
def get_meds_count_by_pharmacy(pharmacy_id: str):
    # Validate the pharmacy ID format
    if not ObjectId.is_valid(pharmacy_id):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Invalid pharmacy ID format"
        )

    # Check if the pharmacy exists
    pharmacy = pharmacies_collection.find_one({"_id": ObjectId(pharmacy_id)})
    if not pharmacy:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Pharmacy not found")

    # Count medicines linked to this pharmacy
    meds_count = med_inventory_collection.count_documents(
        {"pharmacy_id": ObjectId(pharmacy_id)}
    )

    return {
        "pharmacy_id": pharmacy_id,
        "pharmacy_name": pharmacy.get("pharmacy_name"),
        "total_medicines": meds_count,
    }