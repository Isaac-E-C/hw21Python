import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://lierazo_db_user:admin@cluster0.vkglsoo.mongodb.net/")
DB_NAME = os.getenv("DB_NAME", "sersalud")

client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]
