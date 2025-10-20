from fastapi import APIRouter, HTTPException, status, Depends
from db import med_inventory_collection, pharmacies_collection, user_history_collection
from bson import ObjectId
from dependencies.authn import is_authenticated
from datetime import datetime, timezone


search_router = APIRouter(tags=["Search"], prefix="/search")


@search_router.get("/medicine")
def search_medicine(query: str = "", user_id: str = Depends(is_authenticated)):
    if not query:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Search query cannot be empty. Please provide a medicine name.",
        )
    
    # Log search for authenticated users
    if user_id:
        user_history_collection.insert_one(
            {
                "user_id": ObjectId(user_id),
                "search_query": query,
                "searched_at": datetime.now(tz=timezone.utc),
            }
        )

    # Find matching medicines in inventory
    medicines = list(
        med_inventory_collection.find(
            {
                "medicine_name": {"$regex": query, "$options": "i"},
                "quantity": {"$gt": 0},
            }
        )
    )

    # Build combined results with pharmacy info
    results = []
    for med in medicines:
        pharmacy = pharmacies_collection.find_one({"_id": med["pharmacy_id"]})
        if not pharmacy:
            continue  # skip if pharmacy not found

        results.append(
            {
                "medicine_name": med["medicine_name"],
                "price": med.get("price"),
                "quantity": med.get("quantity"),
                "description": med.get("description"),
                "category": med.get("category"),
                "flyer": med.get("flyer"),
                "pharmacy": {
                    "pharmacy_name": pharmacy.get("pharmacy_name"),
                    "digital_address": pharmacy.get("digital_address"),
                    "phone": pharmacy.get("phone", None),  # optional if you added phone
                    "gps_location": pharmacy.get("gps_location"),
                },
            }
        )

    # Return formatted response
    if not results:
        return {
            "total_results": 0,
            "results": [],
            "message": f"No medicines found for {query}.",
        }

    return {
        "total_results": len(results),
        "results": results,
        "message": f"Found {len(results)} results for {query}.",
    }


@search_router.get("/all")
def get_all_medicines():
    # Fetching all medicines from all pharmacies--- useful for homepage(public view)
    medicines = list(med_inventory_collection.find())
    med_list = []

    for med in medicines:
        pharmacy_id = med.get("pharmacy_id")
        if not pharmacy_id or not ObjectId.is_valid(pharmacy_id):
            continue

        pharmacy = pharmacies_collection.find_one({"_id": ObjectId(pharmacy_id)})
        if not pharmacy:
            continue

        med_list.append(
            {
                "pharmacy_name": pharmacy.get("pharmacy_name"),
                "digital_address": pharmacy.get("digital_address"),
                "gps_location": pharmacy.get("gps_location"),
                "medicine_name": med.get("medicine_name"),
                "quantity": med.get("quantity"),
                "price": med.get("price"),
                "description": med.get("description"),
                "category": med.get("category"),
                "flyer": med.get("flyer"),
                "updated_at": med.get("updated_at"),
            }
        )

    return {
        "total": len(med_list),
        "data": med_list,
        "message": f"Fetched {len(med_list)} medicines successfully.",
    }

