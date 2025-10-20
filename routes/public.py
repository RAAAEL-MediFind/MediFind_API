from fastapi import APIRouter, HTTPException, status
from db import pharmacies_collection, med_inventory_collection
from bson import ObjectId
from utils import replace_mongo_id

public_router = APIRouter(tags=["Public"], prefix="/public")


# Get all pharmacies (public view)
@public_router.get("/pharmacies/all")
def get_all_pharmacies():
    pharmacies = list(pharmacies_collection.find({}))
    pharm_list = []

    for pharmacy in pharmacies:
        doc = replace_mongo_id(pharmacy)
        if "user_id" in doc:
            doc["user_id"] = str(doc["user_id"])
        pharm_list.append(doc)

    return {
        "total": len(pharm_list),
        "data": pharm_list,
        "message": f"Fetched {len(pharm_list)} pharmacies successfully.",
    }


# Get a single pharmacy by ID
@public_router.get("/pharmacies/{pharmacy_id}")
def get_pharmacy_by_id(pharmacy_id: str):
    if not ObjectId.is_valid(pharmacy_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid pharmacy ID format")

    pharmacy = pharmacies_collection.find_one({"_id": ObjectId(pharmacy_id)})
    if not pharmacy:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pharmacy not found")

    item = replace_mongo_id(pharmacy)
    if "user_id" in item:
        item["user_id"] = str(item["user_id"])

    return {"data": item, "message": "Pharmacy fetched successfully."}


@public_router.get("/pharmacies/{pharmacy_id}/ads")
def get_medicines_by_pharmacy(pharmacy_id: str):
    # Validate ObjectId format
    if not ObjectId.is_valid(pharmacy_id):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Invalid pharmacy ID format"
        )

    # Get pharmacy info
    pharmacy = pharmacies_collection.find_one({"_id": ObjectId(pharmacy_id)})
    if not pharmacy:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Pharmacy not found")

    # Get all medicines that belong to this pharmacy
    medicines = list(
        med_inventory_collection.find({"pharmacy_id": ObjectId(pharmacy_id)})
    )

    if not medicines:
        return {
            "total": 0,
            "data": [],
            "message": f"No ads found for {pharmacy.get('pharmacy_name')}.",
        }

    # Convert ObjectIds and build response list
    med_list = []
    for med in medicines:
        # Convert MongoDB document safely
        item = replace_mongo_id(med)

        # Convert pharmacy_id if it exists
        if "pharmacy_id" in item:
            item["pharmacy_id"] = str(item["pharmacy_id"])

        # Attach pharmacy info (for frontend display)
        item["pharmacy"] = {
            "pharmacy_name": pharmacy.get("pharmacy_name"),
            "digital_address": pharmacy.get("digital_address"),
            "gps_location": pharmacy.get("gps_location"),
        }

        med_list.append(item)

    # Return the final JSON response
    return {
        "total": len(med_list),
        "data": med_list,
        "message": f"Fetched {len(med_list)} ads for {pharmacy.get('pharmacy_name')}.",
    }


@public_router.get("/medicines/{medicine_id}")
def get_medicine_by_id(medicine_id: str):
    # Validate the ID format first
    if not ObjectId.is_valid(medicine_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid medicine ID format",
        )

    # Find the medicine document
    medicine = med_inventory_collection.find_one({"_id": ObjectId(medicine_id)})
    if not medicine:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Medicine not found")

    # Replace Mongo _id → id
    med = replace_mongo_id(medicine)

    # Convert pharmacy_id safely
    pharmacy_id = med.get("pharmacy_id")
    if isinstance(pharmacy_id, ObjectId):
        pharmacy_id = str(pharmacy_id)
    med["pharmacy_id"] = pharmacy_id

    # Get the pharmacy details
    pharmacy = (
        pharmacies_collection.find_one({"_id": ObjectId(pharmacy_id)})
        if pharmacy_id
        else None
    )

    # Build the clean response structure
    response = {
        "medicine": {
            "id": med.get("id"),
            "name": med.get("medicine_name"),
            "price": med.get("price"),
            "quantity": med.get("quantity"),
            "category": med.get("category"),
            "description": med.get("description"),
            "flyer": med.get("flyer"),
            "updated_at": med.get("updated_at"),
        },
        "pharmacy": {
            "pharmacy_name": pharmacy.get("pharmacy_name") if pharmacy else None,
            "digital_address": pharmacy.get("digital_address") if pharmacy else None,
            "gps_location": pharmacy.get("gps_location") if pharmacy else None,
        },
        "message": f"Fetched medicine '{med.get('medicine_name')}' successfully.",
    }

    return response
