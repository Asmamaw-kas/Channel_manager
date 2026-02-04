import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Bot configuration
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    OWNER_ID = int(os.getenv('OWNER_ID', 0))
    
    # Webhook configuration (for Render)
    WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')
    PORT = int(os.getenv('PORT', 10000))
    
    # Store channels in memory (simple list)
    channels = []