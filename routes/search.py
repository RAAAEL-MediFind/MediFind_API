from fastapi import APIRouter, HTTPException, status
from db import med_inventory_collection, pharmacies_collection
from bson import ObjectId

search_router = APIRouter(tags=["Search"], prefix="/search")


@search_router.get("/medicine")
def search_medicine(query: str = ""):
    """Search for medicines by name"""
    if not query:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Search query cannot be empty. Please provide a medicine name.",
        )

    medicines = list(
        med_inventory_collection.find(
            {
                "medicine_name": {"$regex": query, "$options": "i"},
                "quantity": {"$gt": 0},
            }
        )
    )

    results = []
    for med in medicines:
        pharmacy_id = med.get("pharmacy_id")
        if not pharmacy_id or not ObjectId.is_valid(pharmacy_id):
            continue

        pharmacy = pharmacies_collection.find_one({"_id": ObjectId(pharmacy_id)})
        if not pharmacy:
            continue

        results.append({
            "medicine_id": str(med["_id"]),
            "medicine_name": med.get("medicine_name"),
            "price": med.get("price"),
            "quantity": med.get("quantity"),
            "description": med.get("description"),
            "category": med.get("category"),
            "flyer": med.get("flyer"),
            "pharmacy": {
                "pharmacy_name": pharmacy.get("pharmacy_name"),
                "digital_address": pharmacy.get("digital_address"),
                "gps_location": pharmacy.get("gps_location"),
                # "phone": pharmacy.get("phone", None),
            },
        })

    if not results:
        return {"total_results": 0, "results": [], "message": f"No medicines found for '{query}'."}

    return {"total_results": len(results), "results": results}


@search_router.get("/all")
def get_all_medicines():
    """Fetch all medicines from all pharmacies"""
    medicines = list(med_inventory_collection.find())
    med_list = []

    for med in medicines:
        pharmacy_id = med.get("pharmacy_id")
        if not pharmacy_id or not ObjectId.is_valid(pharmacy_id):
            continue

        pharmacy = pharmacies_collection.find_one({"_id": ObjectId(pharmacy_id)})
        if not pharmacy:
            continue

        med_list.append({
            "medicine_id": str(med["_id"]),
            "medicine_name": med.get("medicine_name"),
            "price": med.get("price"),
            "quantity": med.get("quantity"),
            "description": med.get("description"),
            "category": med.get("category"),
            "flyer": med.get("flyer"),
            "pharmacy_name": pharmacy.get("pharmacy_name"),
            "digital_address": pharmacy.get("digital_address"),
            "gps_location": pharmacy.get("gps_location"),
            "updated_at": med.get("updated_at"),
        })

    return {"total": len(med_list), "data": med_list}
