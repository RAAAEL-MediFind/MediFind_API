from fastapi import APIRouter, HTTPException, status
from db import med_inventory_collection, pharmacies_collection

search_router = APIRouter(tags=["Search"], prefix="/search")


@search_router.get("/medicine")
def search_medicine(query: str = ""):
    if not query:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Search query cannot be empty. Please provide a medicine name.",
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
