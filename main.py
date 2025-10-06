from fastapi import FastAPI
from db import med_inventory_collection
from users import users_router


app = FastAPI()


@app.get("/")
def read_root():
    return {"Message": "Welcome to the RAAEL MediFind App"}


# Plugging routers into main.py
app.include_router(users_router)
