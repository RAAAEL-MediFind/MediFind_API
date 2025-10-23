from fastapi import APIRouter, Depends, Form, HTTPException, status
from typing import Annotated
from bson import ObjectId
from datetime import datetime, timezone
from db import messages_collection, pharmacies_collection, users_collection
from dependencies.authn import is_authenticated
from dependencies.authz import has_roles

messages_router = APIRouter(tags=["Messaging"], prefix="/messages")


# 1. Send Message (User → Pharmacy)
@messages_router.post("/send")
def send_message(
    pharmacy_id: Annotated[str, Form(...)],
    subject: Annotated[str, Form(...)],
    message: Annotated[str, Form(...)],
    user_id: Annotated[str, Depends(is_authenticated)],
):
    """Allow user to send a message to a pharmacy."""
    pharmacy = pharmacies_collection.find_one({"_id": ObjectId(pharmacy_id)})
    if not pharmacy:
        raise HTTPException(status_code=404, detail="Pharmacy not found")

    messages_collection.insert_one(
        {
            "user_id": ObjectId(user_id),
            "pharmacy_id": ObjectId(pharmacy_id),
            "subject": subject,
            "message": message,
            "sent_at": datetime.now(tz=timezone.utc),
            "is_read": False,
        }
    )

    return {"message": "Message sent successfully"}


# 2. Pharmacy Inbox (view messages sent to them)
@messages_router.get("/inbox")
def get_pharmacy_messages(
    user_id: Annotated[str, Depends(is_authenticated)],
    _: Annotated[None, Depends(has_roles(["pharmacy"]))],
):
    """Get all messages sent to the pharmacy."""
    # Find the pharmacy linked to the authenticated user
    pharmacy = pharmacies_collection.find_one({"user_id": ObjectId(user_id)})
    if not pharmacy:
        raise HTTPException(status_code=404, detail="Pharmacy not found")

    # Fetch messages sent to that pharmacy
    messages = list(messages_collection.find({"pharmacy_id": pharmacy["_id"]}))
    if not messages:
        raise HTTPException(status_code=404, detail="No messages found")

    result = []
    for msg in messages:
        user = users_collection.find_one({"_id": ObjectId(msg["user_id"])})
        result.append(
            {
                "message_id": str(msg["_id"]),
                "subject": msg["subject"],
                "message": msg["message"],
                "sender_name": user.get("username") if user else "Unknown",
                "sent_at": msg["sent_at"].isoformat(),
                "is_read": msg.get("is_read", False),
            }
        )

    return {"inbox": result}


# 3. Mark message as read
@messages_router.patch("/{message_id}/read")
def mark_message_as_read(
    message_id: str,
    user_id: Annotated[str, Depends(is_authenticated)],
    _: Annotated[None, Depends(has_roles(["pharmacy"]))],
):
    """Mark a message as read by pharmacy."""
    # Find pharmacy linked to this user
    pharmacy = pharmacies_collection.find_one({"user_id": ObjectId(user_id)})
    if not pharmacy:
        raise HTTPException(status_code=404, detail="Pharmacy not found")

    # Update the message for this pharmacy
    result = messages_collection.update_one(
        {"_id": ObjectId(message_id), "pharmacy_id": pharmacy["_id"]},
        {"$set": {"is_read": True}},
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Message not found or already read")

    return {"message": "Message marked as read"}


# 4. User “Sent Messages” (view messages they’ve sent)
@messages_router.get("/sent")
def get_user_sent_messages(
    user_id: Annotated[str, Depends(is_authenticated)],
):
    """View all messages the user has sent to pharmacies."""
    messages = list(messages_collection.find({"user_id": ObjectId(user_id)}))
    if not messages:
        raise HTTPException(status_code=404, detail="No sent messages found")

    result = []
    for msg in messages:
        pharmacy = pharmacies_collection.find_one({"_id": ObjectId(msg["pharmacy_id"])})
        result.append(
            {
                "message_id": str(msg["_id"]),
                "subject": msg["subject"],
                "message": msg["message"],
                "pharmacy_name": (
                    pharmacy.get("pharmacy_name") if pharmacy else "Unknown"
                ),
                "sent_at": msg["sent_at"].isoformat(),
                "is_read": msg.get("is_read", False),
            }
        )

    return {"sent_messages": result}