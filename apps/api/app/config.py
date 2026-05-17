import logging
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from repo root if running from apps/api
_here = Path(__file__).resolve()
for parent in (_here.parent.parent.parent, _here.parent.parent, _here.parent):
    env = parent / ".env"
    if env.exists():
        load_dotenv(env)
        break
else:
    load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if not GEMINI_API_KEY:
    logging.getLogger("lexguard").warning(
        "GEMINI_API_KEY not set — Gemini calls will fail. Set it in .env"
    )
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
