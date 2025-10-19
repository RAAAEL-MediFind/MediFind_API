from fastapi import FastAPI
from routes.users import users_router
from routes.admin import admin_router
from routes.meds import inventory_router
from routes.search import search_router
from routes.profiles import profile_router
from routes.public import public_router
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

app = FastAPI(
    title="RAAAEL MediFind Web App",
    description="A comprehensive advertisement and medicine management app that connects patients and pharmacies",
    version="1.0.0",
    contact={
        "name": "RAAAEL CODE TEAM",
        "url": "https://github.com/orgs/RAAAEL-MediFind/repositories",
        "admin": "awudiakorfa2@gmail.com",
        "lead": "dojale007@gmail.com",
    },
)


@app.get("/")
def read_root():
    return {"Message": "Welcome to the RAAEL MediFind App"}


# Plugging routers into main.py
app.include_router(users_router)
app.include_router(admin_router)
app.include_router(inventory_router)
app.include_router(search_router)
app.include_router(profile_router)
app.include_router(public_router)
