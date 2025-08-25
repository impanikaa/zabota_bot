from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 786528166

ADMIN_IDS = [1767589934, 786528166]

def add_admin(admin_id):
    if admin_id not in ADMIN_IDS:
        ADMIN_IDS.append(admin_id)
        return True
    return False

def remove_admin(admin_id):
    if admin_id in ADMIN_IDS and admin_id != OWNER_ID:
        ADMIN_IDS.remove(admin_id)
        return True
    return False