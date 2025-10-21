from pymongo import MongoClient
import os
from dotenv import load_dotenv


load_dotenv()

# Connect to Mongo Atlas Cluster
mongo_client = MongoClient(os.getenv("MONGO_URI"))


# Access database
medifind_db = mongo_client["medi_find_db"]


# Access a collection to operate on
users_collection = medifind_db["users"]
med_inventory_collection = medifind_db["inventory"]
pharmacies_collection = medifind_db["pharmacies"]
user_history_collection = medifind_db["user_history"]
cart_collection = medifind_db["carts"]
# orders_collection = medifind_db["orders"]
prescriptions_collection = medifind_db["prescriptions"]
saved_pharmacies_collection = medifind_db["saved_pharmacies"]   
messages_collection = medifind_db["messages"]
