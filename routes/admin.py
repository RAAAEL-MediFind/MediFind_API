from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId
from db import users_collection, pharmacies_collection
from typing import Annotated
from utils import replace_mongo_id
from dependencies.authz import has_roles


# Creating an Admin Router
admin_router = APIRouter(tags=["Admin"])


# Defining endpoints for Admin to fetch all users and all pharmacies.
@admin_router.get("/users/all")
def get_all_users(user: dict = Depends(has_roles(["admin"]))):
    users = list(users_collection.find({}))
    formatted_users = [replace_mongo_id(user_doc) for user_doc in users]
    return {"Users": formatted_users}


@admin_router.get("/users/pharmacies/all")
def get_all_pharmacies(user: Annotated[dict, Depends(has_roles(["admin"]))]):
    pharmacies = list(pharmacies_collection.find({}))
    formatted_pharmacies = []
    for pharmacy_doc in pharmacies:
        if "user_id" in pharmacy_doc:
            pharmacy_doc["user_id"] = str(pharmacy_doc["user_id"])
        formatted_pharmacies.append(replace_mongo_id(pharmacy_doc))
    return {"Pharmacies": formatted_pharmacies}


@admin_router.delete("/users/{user_id}/delete")
def delete_user(user_id: str, user: dict = Depends(has_roles(["admin"]))):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid ID format")
    result = users_collection.delete_one({"_id": ObjectId(user_id)})
    if result.deleted_count == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return {"message": "User deleted successfully."}


@admin_router.delete("/pharmacies/{pharmacy_id}/delete")
def delete_pharmacy(pharmacy_id: str, user: dict = Depends(has_roles(["admin"]))):
    if not ObjectId.is_valid(pharmacy_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid ID format")
    result = pharmacies_collection.delete_one({"_id": ObjectId(pharmacy_id)})
    if result.deleted_count == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pharmacy not found")
    return {"message": "Pharmacy deleted successfully."}


# Mini statistics of users on the platform, limited for admin use only.


@admin_router.get("/dashboard/stats")
def get_dashboard_stats(user: dict = Depends(has_roles(["admin"]))):
    total_users = users_collection.count_documents({})
    total_pharmacies = pharmacies_collection.count_documents({})
    total_patients = users_collection.count_documents({"role": "patient"})
    total_admins = users_collection.count_documents({"role": "admin"})

    return {
        "Total Users": total_users,
        "Total Pharmacies": total_pharmacies,
        "Total Patients": total_patients,
        "Total Admins": total_admins,
        "message": "Platform summary fetched successfully.",
    }
