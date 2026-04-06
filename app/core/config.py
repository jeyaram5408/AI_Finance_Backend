# app/core/config.py

import os
from dotenv import load_dotenv

# ✅ Load local first
load_dotenv(".env.local")

ENV = os.getenv("ENV", "local")

# ✅ Override if production
if ENV == "production":
    load_dotenv(".env", override=True)

print(f"🔥 CONFIG ENV: {ENV}")

FRONTEND_URL = os.getenv("FRONTEND_URL")
DATABASE_URL = os.getenv("DATABASE_URL")