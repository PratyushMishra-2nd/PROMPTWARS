import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_PRO_MODEL = os.getenv("GEMINI_PRO_MODEL", "gemini-2.5-pro")
GEMINI_FLASH_MODEL = os.getenv("GEMINI_FLASH_MODEL", "gemini-2.5-flash")
GEMINI_EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL", "text-embedding-004")

CORS_ORIGIN = os.getenv("CORS_ORIGIN", "http://localhost:3000")
CORS_ORIGINS = [o.strip() for o in CORS_ORIGIN.split(",") if o.strip()]

CONTRACT_TYPES = [
    "employment",
    "freelance",
    "rental",
    "saas",
    "tos",
    "privacy_policy",
    "vendor_nda",
]

PERSPECTIVES = ["employee", "freelancer", "tenant", "customer", "buyer"]
