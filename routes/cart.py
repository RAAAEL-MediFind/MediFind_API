from fastapi import APIRouter, HTTPException, status, Depends, Form, Path
from typing import Annotated
from bson import ObjectId
from datetime import datetime
from db import cart_collection, med_inventory_collection
from dependencies.authn import is_authenticated


cart_router = APIRouter(tags=["Cart"], prefix="/cart")


# Add to Cart
@cart_router.post("/add")
def add_to_cart(
    medicine_id: Annotated[str, Form(...)],
    # quantity
    quantity: Annotated[int, Form(..., gt=0)],
    user_id: Annotated[str, Depends(is_authenticated)],
):
    """Add a medicine to the user's cart"""

    medicine = med_inventory_collection.find_one({"_id": ObjectId(medicine_id)})
    if not medicine:
        raise HTTPException(status_code=404, detail="Medicine not found")

    cart = cart_collection.find_one({"user_id": user_id})
    if cart:
        updated = False
        for existing_item in cart["items"]:
            if existing_item["medicine_id"] == medicine_id:
                existing_item["quantity"] += quantity
                updated = True
                break

        if not updated:
            cart["items"].append({"medicine_id": medicine_id, "quantity": quantity})

        cart["updated_at"] = datetime.utcnow()
        cart_collection.update_one({"user_id": user_id}, {"$set": cart})
    else:
        new_cart = {
            "user_id": user_id,
            "items": [{"medicine_id": medicine_id, "quantity": quantity}],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        cart_collection.insert_one(new_cart)

    return {"message": "Item added to cart successfully"}


# Get Cart with Total Price
@cart_router.get("/", status_code=status.HTTP_200_OK)
def get_cart(user_id: Annotated[str, Depends(is_authenticated)]):
    """Get all items in the user's cart with total price"""
    cart = cart_collection.find_one({"user_id": user_id})
    if not cart or not cart.get("items"):
        return {"message": "Cart is empty", "items": [], "total_price": 0.0}

    total_price = 0.0
    detailed_items = []

    for item in cart["items"]:
        med = med_inventory_collection.find_one({"_id": ObjectId(item["medicine_id"])})
        if med:
            price = med.get("price", 0)
            total_price += price * item["quantity"]
            detailed_items.append(
                {
                    "medicine_id": str(item["medicine_id"]),
                    "medicine_name": med.get("medicine_name"),
                    "quantity": item["quantity"],
                    "price_per_unit": price,
                    "subtotal": price * item["quantity"],
                }
            )

    return {
        "message": "Cart fetched successfully",
        "items": detailed_items,
        "total_price": total_price,
    }


# Remove item from Cart
@cart_router.delete("/remove/{medicine_id}", status_code=status.HTTP_200_OK)
def remove_from_cart(
    medicine_id: Annotated[str, Path(...)],
    user_id: Annotated[str, Depends(is_authenticated)],
):
    """Remove a specific medicine from the user's cart"""
    cart = cart_collection.find_one({"user_id": user_id})
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")

    new_items = [i for i in cart["items"] if i["medicine_id"] != medicine_id]

    cart_collection.update_one(
        {"user_id": user_id},
        {"$set": {"items": new_items, "updated_at": datetime.utcnow()}},
    )

    return {"message": "Item removed successfully"}


# Clear Cart
@cart_router.delete("/clear", status_code=status.HTTP_200_OK)
def clear_cart(user_id: Annotated[str, Depends(is_authenticated)]):
    """Completely clear all items from the user's cart"""
    cart_collection.delete_one({"user_id": user_id})
    return {"message": "Cart cleared successfully"}
