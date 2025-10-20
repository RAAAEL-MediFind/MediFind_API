from fastapi import HTTPException, status, APIRouter, Depends, File, UploadFile, Form
from db import med_inventory_collection, users_collection
from bson.objectid import ObjectId
from utils import replace_mongo_id
from typing import Annotated, Optional
import cloudinary
import cloudinary.uploader
from dependencies.authn import is_authenticated
from dependencies.authz import has_roles
from datetime import datetime, timezone

# Create inventory router
inventory_router = APIRouter(tags=["Pharmacies"], prefix="/inventory")


# Inventory endpoints (pharmacy-only)
@inventory_router.get("/my-stock")
def get_my_stock(
    user_id: Annotated[str, Depends(is_authenticated)],
    _=Depends(has_roles(["pharmacy"])),
    query: str = "",
    limit: int = 10,
    skip: int = 0,
):
    # Get pharmacy_id from user
    pharmacy_doc = users_collection.find_one(
        {"_id": ObjectId(user_id), "role": "pharmacy"}
    )
    if not pharmacy_doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pharmacy not found!")

    # Get stock from database
    stock = med_inventory_collection.find(
        filter={
            "pharmacy_id": ObjectId(pharmacy_doc["_id"]),
            "$or": [
                {"medicine_name": {"$regex": query, "$options": "i"}},
            ],
        },
        limit=int(limit),
        skip=int(skip),
    ).to_list()
    # Return response
    formatted_stock = []
    for doc in stock:
        item = replace_mongo_id(doc)
        item["pharmacy_id"] = str(item["pharmacy_id"])
        formatted_stock.append(item)
    return {"data": formatted_stock}


@inventory_router.post("/add")
def add_medicine(
    medicine_name: Annotated[str, Form()],
    quantity: Annotated[int, Form()],
    price: Annotated[float, Form()],
    description: Annotated[str, Form()],
    category: Annotated[str, Form()],
    user_id: Annotated[str, Depends(is_authenticated)],
    flyer: Annotated[Optional[UploadFile], File],
    _=Depends(has_roles(["pharmacy"])),
):
    # Get pharmacy_id from user
    pharmacy_doc = users_collection.find_one(
        {"_id": ObjectId(user_id), "role": "pharmacy"}
    )
    if not pharmacy_doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pharmacy not found!")

    # Ensure medicine does not exist for this pharmacy
    med_count = med_inventory_collection.count_documents(
        filter={
            "$and": [
                {"medicine_name": medicine_name},
                {"pharmacy_id": ObjectId(pharmacy_doc["_id"])},
            ]
        }
    )
    if med_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Medicine {medicine_name} already exists for this pharmacy!",
        )

    # Upload medicine_image to cloudinary if provided
    image_url = None
    if flyer:
        upload_result = cloudinary.uploader.upload(flyer.file)
        image_url = upload_result["secure_url"]
        print(upload_result)

    # Insert medicine into database
    med_inventory_collection.insert_one(
        {
            "pharmacy_id": ObjectId(pharmacy_doc["_id"]),
            "medicine_name": medicine_name,
            "quantity": quantity,
            "price": price,
            "description": description,
            "category": category,
            "flyer": image_url,
            "updated_at": datetime.now(tz=timezone.utc),
        }
    )
    # Return response
    return {"message": "Medicine added to stock successfully"}


@inventory_router.get("/my-stock/{medicine_id}")
def get_medicine_by_id(
    medicine_id: str,
    user_id: Annotated[str, Depends(is_authenticated)],
    _=Depends(has_roles(["pharmacy"])),
):
    # Check if medicine_id is valid
    if not ObjectId.is_valid(medicine_id):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid mongo id received!"
        )
    # Get pharmacy_id
    pharmacy_doc = users_collection.find_one(
        {"_id": ObjectId(user_id), "role": "pharmacy"}
    )
    if not pharmacy_doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pharmacy not found!")
    # Get medicine from database by id
    medicine = med_inventory_collection.find_one(
        {"_id": ObjectId(medicine_id), "pharmacy_id": ObjectId(pharmacy_doc["_id"])}
    )
    if not medicine:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Medicine not found!")
    # Return response
    formatted = replace_mongo_id(medicine)
    formatted["pharmacy_id"] = str(formatted["pharmacy_id"])
    return {"data": formatted}


@inventory_router.put("/my-stock/{medicine_id}")
def update_medicine(
    medicine_id: str,
    medicine_name: Annotated[str, Form()],
    quantity: Annotated[int, Form()],
    price: Annotated[float, Form()],
    description: Annotated[str, Form()],
    category: Annotated[str, Form()],
    user_id: Annotated[str, Depends(is_authenticated)],
    _=Depends(has_roles(["pharmacy"])),
    flyer: Annotated[Optional[UploadFile], File()] = None,
):
    # Check if medicine_id is valid mongo id
    if not ObjectId.is_valid(medicine_id):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid mongo id received!"
        )
    # Get pharmacy_id
    pharmacy_doc = users_collection.find_one(
        {"_id": ObjectId(user_id), "role": "pharmacy"}
    )
    if not pharmacy_doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pharmacy not found!")

    # Upload medicine_image to cloudinary if provided
    image_url = None
    if flyer:
        upload_result = cloudinary.uploader.upload(flyer.file)
        image_url = upload_result["secure_url"]
        print(upload_result)
    # Replace medicine in database
    med_inventory_collection.replace_one(
        filter={
            "_id": ObjectId(medicine_id),
            "pharmacy_id": ObjectId(pharmacy_doc["_id"]),
        },
        replacement={
            "pharmacy_id": ObjectId(pharmacy_doc["_id"]),
            "medicine_name": medicine_name,
            "quantity": quantity,
            "price": price,
            "description": description,
            "category": category,
            "flyer": image_url,
            "updated_at": datetime.now(tz=timezone.utc),
        },
    )
    return {"message": "Medicine updated successfully"}


@inventory_router.delete(
    "/my-stock/{medicine_id}", dependencies=[Depends(has_roles(["pharmacy"]))]
)
def delete_medicine(
    medicine_id: str, user_id: Annotated[str, Depends(is_authenticated)]
):
    # Check if medicine_id is valid mongo id
    if not ObjectId.is_valid(medicine_id):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid mongo id received!"
        )
    # Get pharmacy_id
    pharmacy_doc = users_collection.find_one(
        {"_id": ObjectId(user_id), "role": "pharmacy"}
    )
    if not pharmacy_doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pharmacy not found!")
    # Delete medicine from database
    delete_result = med_inventory_collection.delete_one(
        filter={
            "_id": ObjectId(medicine_id),
            "pharmacy_id": ObjectId(pharmacy_doc["_id"]),
        }
    )
    if not delete_result.deleted_count:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Medicine not found to delete!")
    return {"message": "Medicine deleted successfully"}
