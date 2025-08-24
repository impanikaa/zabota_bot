from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split()))
OWNER_ID = 786528166
ADMIN_IDS = [1767589934, 786528166]
