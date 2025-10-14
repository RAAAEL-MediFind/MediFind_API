from fastapi import FastAPI
from routes.users import users_router
from routes.admin import admin_router
from routes.meds import inventory_router
import cloudinary
import os
from dotenv import load_dotenv

load_dotenv()

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)

app = FastAPI()


@app.get("/")
def read_root():
    return {"Message": "Welcome to the RAAEL MediFind App"}


# Plugging routers into main.py
app.include_router(users_router)
app.include_router(admin_router)
app.include_router(inventory_router)
