from fastapi import APIRouter, HTTPException, status, Depends
from typing import Annotated
from bson import ObjectId
from datetime import datetime
from db import cart_collection, med_inventory_collection
from dependencies.authn import is_authenticated

cart_router = APIRouter(tags=["Cart"], prefix="/cart")


@cart_router.post("/add")
def add_to_cart(
    medicine_id: str,
    quantity: int,
    user_id: Annotated[str, Depends(is_authenticated)],
):
    """Add a medicine to the user's cart (restrict to one pharmacy per cart)."""

    # Validate ID
    if not ObjectId.is_valid(medicine_id):
        raise HTTPException(status_code=400, detail="Invalid medicine ID format")

    # Check medicine exists
    medicine = med_inventory_collection.find_one({"_id": ObjectId(medicine_id)})
    if not medicine:
        raise HTTPException(status_code=404, detail="Medicine not found")

    pharmacy_id = str(medicine["pharmacy_id"])
    cart = cart_collection.find_one({"user_id": user_id})

    if cart:
        # Restrict cart to a single pharmacy
        current_pharmacy = cart.get("pharmacy_id")
        if current_pharmacy and current_pharmacy != pharmacy_id:
            raise HTTPException(
                status_code=400,
                detail="You can only add medicines from one pharmacy at a time. Please clear your cart before switching pharmacies.",
            )

        # Add or update item
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
        # Create new cart tied to pharmacy
        new_cart = {
            "user_id": user_id,
            "pharmacy_id": pharmacy_id,
            "items": [{"medicine_id": medicine_id, "quantity": quantity}],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        cart_collection.insert_one(new_cart)

    return {"message": "Item added to cart successfully"}


@cart_router.get("/", status_code=status.HTTP_200_OK)
def get_cart(user_id: Annotated[str, Depends(is_authenticated)]):
    """Get all items in the user's cart with total price"""
    cart = cart_collection.find_one({"user_id": user_id})
    if not cart or not cart.get("items"):
        return {"message": "Cart is empty", "items": [], "total_price": 0.0}

    total_price = 0.0
    detailed_items = []
    pharmacy_name = None

    for item in cart["items"]:
        med = med_inventory_collection.find_one({"_id": ObjectId(item["medicine_id"])})
        if med:
            price = med.get("price", 0)
            subtotal = price * item["quantity"]
            total_price += subtotal
            detailed_items.append({
                "medicine_id": str(item["medicine_id"]),
                "medicine_name": med.get("medicine_name"),
                "quantity": item["quantity"],
                "price_per_unit": price,
                "subtotal": subtotal,
            })

    return {
        "message": "Cart fetched successfully",
        "pharmacy_id": cart.get("pharmacy_id"),
        "items": detailed_items,
        "total_price": total_price,
    }


@cart_router.delete("/remove/{medicine_id}", status_code=status.HTTP_200_OK)
def remove_from_cart(medicine_id: str, user_id: Annotated[str, Depends(is_authenticated)]):
    """Remove a specific medicine from the user's cart"""
    cart = cart_collection.find_one({"user_id": user_id})
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")

    new_items = [i for i in cart["items"] if i["medicine_id"] != medicine_id]

    if not new_items:
        # If last item removed, delete entire cart
        cart_collection.delete_one({"user_id": user_id})
    else:
        cart_collection.update_one(
            {"user_id": user_id},
            {"$set": {"items": new_items, "updated_at": datetime.utcnow()}},
        )

    return {"message": "Item removed successfully"}


@cart_router.delete("/clear", status_code=status.HTTP_200_OK)
def clear_cart(user_id: Annotated[str, Depends(is_authenticated)]):
    """Completely clear all items from the user's cart"""
    cart_collection.delete_one({"user_id": user_id})
    return {"message": "Cart cleared successfully"}
