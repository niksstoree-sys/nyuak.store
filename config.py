import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TOKEN = os.getenv("DISCORD_TOKEN")
    GUILD_ID = int(os.getenv("GUILD_ID")) if os.getenv("GUILD_ID") else None
    DATABASE_PATH = os.getenv("DATABASE_URL", "noctra.db")
    
    # Brand Identity Colors
    COLOR_PRIMARY = 0x3D1E6D   # Dark Purple
    COLOR_SECONDARY = 0x7048E8 # Blue Violet
    COLOR_SUCCESS = 0x2B8A3E   # Premium Dark Green
    COLOR_DANGER = 0xC92A2A    # Premium Dark Red
    
    BRAND_NAME = "NOCTRA"
    FOOTER_TEXT = "NOCTRA Premium Store System"
