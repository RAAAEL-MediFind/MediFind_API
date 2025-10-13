from fastapi import APIRouter, Depends
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
