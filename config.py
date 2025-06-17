import os
from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
GROUPS_FILE = "groups.json"
BOT_USERNAME = os.getenv("BOT_USERNAME", "drctnewsbot")
