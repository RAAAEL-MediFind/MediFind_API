from fastapi import APIRouter, HTTPException, Query
from bson import ObjectId
from db import users_collection, med_inventory_collection

public_router = APIRouter(prefix="/public", tags=["Public Access"])


def serialize_doc(doc):
    # Convert ObjectId to string for MongoDB documents.
    doc["_id"] = str(doc["_id"])
    if "pharmacy_id" in doc and isinstance(doc["pharmacy_id"], ObjectId):
        doc["pharmacy_id"] = str(doc["pharmacy_id"])
    return doc


# Get all pharmacies (with optional filters)
@public_router.get("/pharmacies")
def get_all_pharmacies(
    name: str | None = Query(None, description="Filter by pharmacy name"),
    location: str | None = Query(None, description="Filter by location"),
):
    query = {"role": "pharmacy"}
    if name:
        query["name"] = {"$regex": name, "$options": "i"}
    if location:
        query["location"] = {"$regex": location, "$options": "i"}

    pharmacies = list(users_collection.find(query, {"password": 0}))
    if not pharmacies:
        raise HTTPException(status_code=404, detail="No pharmacies found")

    return [serialize_doc(p) for p in pharmacies]


# Get pharmacy by ID
@public_router.get("/pharmacies/{pharmacy_id}")
def get_pharmacy_by_id(pharmacy_id: str):
    if not ObjectId.is_valid(pharmacy_id):
        raise HTTPException(status_code=400, detail="Invalid pharmacy ID")

    pharmacy = users_collection.find_one(
        {"_id": ObjectId(pharmacy_id), "role": "pharmacy"}, {"password": 0}
    )
    if not pharmacy:
        raise HTTPException(status_code=404, detail="Pharmacy not found")

    return serialize_doc(pharmacy)


# Get all medicines (with pharmacy info)
@public_router.get("/medicines")
def get_all_medicines(
    name: str | None = Query(None, description="Search by medicine name"),
    category: str | None = Query(None, description="Filter by category"),
    pharmacy_id: str | None = Query(None, description="Filter by pharmacy ID"),
):
    query = {}
    if name:
        query["name"] = {"$regex": name, "$options": "i"}
    if category:
        query["category"] = {"$regex": category, "$options": "i"}
    if pharmacy_id and ObjectId.is_valid(pharmacy_id):
        query["pharmacy_id"] = ObjectId(pharmacy_id)

    medicines = list(med_inventory_collection.find(query))
    if not medicines:
        raise HTTPException(status_code=404, detail="No medicines found")

    results = []
    for med in medicines:
        med = serialize_doc(med)
        # Fetch pharmacy details
        if "pharmacy_id" in med and med["pharmacy_id"]:
            pharmacy = users_collection.find_one(
                {"_id": ObjectId(med["pharmacy_id"]), "role": "pharmacy"},
                {"_id": 1, "name": 1, "location": 1, "contact": 1},
            )
            if pharmacy:
                med["pharmacy_info"] = serialize_doc(pharmacy)
        results.append(med)

    return results


# Get medicine by ID (with pharmacy info)
@public_router.get("/medicines/{medicine_id}")
def get_medicine_by_id(medicine_id: str):
    if not ObjectId.is_valid(medicine_id):
        raise HTTPException(status_code=400, detail="Invalid medicine ID")

    medicine = med_inventory_collection.find_one({"_id": ObjectId(medicine_id)})
    if not medicine:
        raise HTTPException(status_code=404, detail="Medicine not found")

    medicine = serialize_doc(medicine)

    # Add pharmacy info
    if "pharmacy_id" in medicine and medicine["pharmacy_id"]:
        pharmacy = users_collection.find_one(
            {"_id": ObjectId(medicine["pharmacy_id"]), "role": "pharmacy"},
            {"_id": 1, "name": 1, "location": 1, "contact": 1},
        )
        if pharmacy:
            medicine["pharmacy_info"] = serialize_doc(pharmacy)

    return medicine
