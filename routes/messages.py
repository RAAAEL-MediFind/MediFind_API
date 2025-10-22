from fastapi import APIRouter, Depends, Form, HTTPException
from typing import Annotated
from bson import ObjectId
from datetime import datetime, timezone
from db import messages_collection, pharmacies_collection, users_collection
from dependencies.authn import is_authenticated
from dependencies.authz import has_roles

messages_router = APIRouter(prefix="/messages")


# 1. Send Message (User → Pharmacy)
@messages_router.post("/send", tags=["user_messages"])
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
            "message": message.strip(),
            "sent_at": datetime.now(tz=timezone.utc),
            "is_read": False,
            "is_reply": False,
        }
    )

    return {"message": "Message sent successfully"}


# 2. Pharmacy Inbox (view messages sent to them)
@messages_router.get("/inbox/pharmacy", tags=["pharmacy_messages"])
def get_pharmacy_received_messages(
    user_id: Annotated[str, Depends(is_authenticated)],
    _: Annotated[None, Depends(has_roles(["pharmacy"]))],
):
    """Get all messages sent to the pharmacy."""
    # Find the pharmacy linked to the authenticated user
    pharmacy = pharmacies_collection.find_one({"user_id": ObjectId(user_id)})
    if not pharmacy:
        raise HTTPException(status_code=404, detail="Pharmacy not found")

    # Fetch messages sent to that pharmacy (exclude replies)
    messages = list(
        messages_collection.find({"pharmacy_id": pharmacy["_id"], "is_reply": False})
    )

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
                "phone": user.get("phone"),
                "email": user.get("email"),
            }
        )

    return {"inbox": result}


# 3a. Mark message as read (Pharmacy)
@messages_router.patch("/pharmacy/{message_id}/read", tags=["pharmacy_messages"])
def mark_message_as_read_pharmacy(
    message_id: str,
    user_id: Annotated[str, Depends(is_authenticated)],
    _: Annotated[None, Depends(has_roles(["pharmacy"]))],
):
    """Mark a message as read by pharmacy."""
    # Find pharmacy linked to this user
    pharmacy = pharmacies_collection.find_one({"user_id": ObjectId(user_id)})
    if not pharmacy:
        raise HTTPException(status_code=404, detail="Pharmacy not found")

    # Update message for this pharmacy
    result = messages_collection.update_one(
        {"_id": ObjectId(message_id), "pharmacy_id": pharmacy["_id"]},
        {"$set": {"is_read": True}},
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Message not found or already read")

    return {"message": "Message marked as read by pharmacy"}


# 3b. Mark message as read (User)
@messages_router.patch("/user/{message_id}/read", tags=["user_messages"])
def mark_message_as_read_user(
    message_id: str,
    user_id: Annotated[str, Depends(is_authenticated)],
):
    """Mark a message as read by user (for pharmacy replies)."""
    result = messages_collection.update_one(
        {"_id": ObjectId(message_id), "user_id": ObjectId(user_id)},
        {"$set": {"is_read": True}},
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Message not found or already read")

    return {"message": "Message marked as read by user"}


# 4. User “Sent Messages” (view messages they’ve sent)
@messages_router.get("/sent", tags=["user_messages"])
def get_user_sent_messages(
    user_id: Annotated[str, Depends(is_authenticated)],
):
    """View all messages the user has sent to pharmacies."""
    messages = list(
        messages_collection.find({"user_id": ObjectId(user_id), "is_reply": False})
    )
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


# 5. Pharmacy Reply to User Message
@messages_router.post("/reply/{message_id}", tags=["pharmacy_messages"])
def pharm_reply_to_message(
    message_id: str,
    reply_message: Annotated[str, Form(...)],
    user_id: Annotated[str, Depends(is_authenticated)],
    _: Annotated[None, Depends(has_roles(["pharmacy"]))],
):
    """Allow pharmacy to reply to a user's message."""
    # Find the pharmacy linked to this user
    pharmacy = pharmacies_collection.find_one({"user_id": ObjectId(user_id)})
    if not pharmacy:
        raise HTTPException(status_code=404, detail="Pharmacy not found")

    # Get the original message to find the user who sent it
    original_msg = messages_collection.find_one({"_id": ObjectId(message_id)})
    if not original_msg:
        raise HTTPException(status_code=404, detail="Original message not found")

    # Insert a reply as a new message record (pharmacy → user)
    messages_collection.insert_one(
        {
            "user_id": original_msg["user_id"],  # Recipient user
            "pharmacy_id": pharmacy["_id"],  # Sender pharmacy
            "subject": f"Re: {original_msg['subject']}",
            "message": reply_message.strip(),
            "sent_at": datetime.now(tz=timezone.utc),
            "is_read": False,
            "is_reply": True,
            "parent_message_id": ObjectId(message_id),
        }
    )

    return {"message": "Reply sent successfully"}


# 6. User Reply to Pharmacy Message
@messages_router.post("/reply/user/{message_id}", tags=["user_messages"])
def user_reply_to_message(
    message_id: str,
    reply_message: Annotated[str, Form(...)],
    user_id: Annotated[str, Depends(is_authenticated)],
):
    """Allow user to reply to a pharmacy's message."""
    # Find the original message
    original_msg = messages_collection.find_one({"_id": ObjectId(message_id)})
    if not original_msg:
        raise HTTPException(status_code=404, detail="Original message not found")

    # Ensure this message belongs to the user
    if original_msg.get("user_id") != ObjectId(user_id):
        raise HTTPException(
            status_code=403, detail="You are not authorized to reply to this message"
        )

    # Insert a reply as a new message record (user → pharmacy)
    messages_collection.insert_one(
        {
            "user_id": ObjectId(user_id),  # Sender user
            "pharmacy_id": original_msg["pharmacy_id"],  # Recipient pharmacy
            "subject": f"Re: {original_msg['subject']}",
            "message": reply_message.strip(),
            "sent_at": datetime.now(tz=timezone.utc),
            "is_read": False,
            "is_reply": True,
            "parent_message_id": ObjectId(message_id),
        }
    )

    return {"message": "Reply sent successfully"}


# 7. User Inbox (View replies from pharmacies)
@messages_router.get("/inbox/user", tags=["user_messages"])
def get_user_inbox(
    user_id: Annotated[str, Depends(is_authenticated)],
):
    """Get all messages (including replies) sent to the user."""
    messages = list(messages_collection.find({"user_id": ObjectId(user_id)}))
    if not messages:
        raise HTTPException(status_code=404, detail="No messages found")

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
                "is_reply": msg.get("is_reply", False),
            }
        )

    return {"inbox": result}


# 8. Pharmacy Full Inbox (see both user messages and their own replies)
@messages_router.get("/inbox/pharmacy/full", tags=["pharmacy_messages"])
def get_pharmacy_full_inbox(
    user_id: Annotated[str, Depends(is_authenticated)],
    _: Annotated[None, Depends(has_roles(["pharmacy"]))],
):
    """Allow pharmacy to see both incoming user messages and their own replies."""
    # Find the pharmacy linked to this user
    pharmacy = pharmacies_collection.find_one({"user_id": ObjectId(user_id)})
    if not pharmacy:
        raise HTTPException(status_code=404, detail="Pharmacy not found")

    # Fetch all messages related to this pharmacy (both received and sent)
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
                "sender": (
                    user.get("username")
                    if not msg.get("is_reply")
                    else pharmacy.get("pharmacy_name")
                ),
                "recipient": (
                    pharmacy.get("pharmacy_name")
                    if not msg.get("is_reply")
                    else user.get("username")
                ),
                "sent_at": msg["sent_at"].isoformat(),
                "is_read": msg.get("is_read", False),
                "is_reply": msg.get("is_reply", False),
            }
        )

    return {"inbox": result}


# 9. Pharmacy Threaded Inbox (group by conversations)
@messages_router.get("/inbox/pharmacy/threaded", tags=["pharmacy_messages"])
def get_pharmacy_threaded_inbox(
    user_id: Annotated[str, Depends(is_authenticated)],
    _: Annotated[None, Depends(has_roles(["pharmacy"]))],
):
    """Return pharmacy messages grouped by user conversation threads."""
    # Find the pharmacy linked to the logged-in user
    pharmacy = pharmacies_collection.find_one({"user_id": ObjectId(user_id)})
    if not pharmacy:
        raise HTTPException(status_code=404, detail="Pharmacy not found")

    # Fetch all messages related to this pharmacy
    messages = list(
        messages_collection.find({"pharmacy_id": pharmacy["_id"]}).sort("sent_at", 1)
    )
    if not messages:
        raise HTTPException(status_code=404, detail="No messages found")

    threads = {}
    for msg in messages:
        user_id_str = str(msg["user_id"])
        user = users_collection.find_one({"_id": ObjectId(msg["user_id"])})
        username = user.get("username") if user else "Unknown"

        # Group messages by user (conversation thread)
        if user_id_str not in threads:
            threads[user_id_str] = {
                "user_id": user_id_str,
                "username": username,
                "conversation": [],
            }

        threads[user_id_str]["conversation"].append(
            {
                "message_id": str(msg["_id"]),
                "subject": msg["subject"],
                "message": msg["message"],
                "sent_at": msg["sent_at"].isoformat(),
                "is_reply": msg.get("is_reply", False),
                "is_read": msg.get("is_read", False),
            }
        )

    return {"conversations": list(threads.values())}


# 10. User Threaded Inbox (group by pharmacy)
@messages_router.get("/inbox/user/threaded", tags=["user_messages"])
def get_user_threaded_inbox(
    user_id: Annotated[str, Depends(is_authenticated)],
):
    """Return user messages grouped by pharmacy conversation threads."""
    messages = list(
        messages_collection.find({"user_id": ObjectId(user_id)}).sort("sent_at", 1)
    )
    if not messages:
        raise HTTPException(status_code=404, detail="No messages found")

    threads = {}
    for msg in messages:
        pharmacy_id_str = str(msg["pharmacy_id"])
        pharmacy = pharmacies_collection.find_one({"_id": ObjectId(msg["pharmacy_id"])})
        pharmacy_name = pharmacy.get("pharmacy_name") if pharmacy else "Unknown"

        # Group messages by pharmacy
        if pharmacy_id_str not in threads:
            threads[pharmacy_id_str] = {
                "pharmacy_id": pharmacy_id_str,
                "pharmacy_name": pharmacy_name,
                "conversation": [],
            }

        threads[pharmacy_id_str]["conversation"].append(
            {
                "message_id": str(msg["_id"]),
                "subject": msg["subject"],
                "message": msg["message"],
                "sent_at": msg["sent_at"].isoformat(),
                "is_reply": msg.get("is_reply", False),
                "is_read": msg.get("is_read", False),
            }
        )

    return {"conversations": list(threads.values())}
