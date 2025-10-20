# I need to create an endpoint to get user profile information and user history (previously viewed items, orders, etc.) in routes/profiles.py
from fastapi import APIRouter, Depends, HTTPException, status, Form
from db import users_collection, user_history_collection
from bson.objectid import ObjectId
from utils import replace_mongo_id
from typing import Annotated
from pydantic import EmailStr
from dependencies.authn import is_authenticated

profile_router = APIRouter(tags=["Profile"], prefix="/profile")


# user profile endpoint
@profile_router.get("/me")
def get_user_profile(user_id: Annotated[str, Depends(is_authenticated)]):
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found!")

    user_info = replace_mongo_id(user)
    # Don’t expose password
    user_info.pop("password", None)
    return {"data": user_info, "message": "Profile fetched successfully"}


# search history endpoint
@profile_router.get("/me/history")
def get_user_history(user_id: Annotated[str, Depends(is_authenticated)]):
    history = list(
        user_history_collection.find({"user_id": ObjectId(user_id)}).sort(
            "searched_at", -1
        )
    )
    formatted_history = []
    for h in history:
        formatted_history.append(
            {
                "query": h["query"],
                "searched_at": h["searched_at"].strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

    return {
        "total": len(formatted_history),
        "history": formatted_history,
        "message": "Search history fetched successfully",
    }


# endpoint to clear user history
@profile_router.delete("/me/history")
def clear_user_history(user_id: Annotated[str, Depends(is_authenticated)]):
    result = user_history_collection.delete_many({"user_id": ObjectId(user_id)})
    return {
        "deleted_count": result.deleted_count,
        "message": "User history cleared successfully",
    }

