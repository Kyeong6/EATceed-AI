import os

from dotenv import load_dotenv

# .env 참조: 클라우드에서 .env 이용
load_dotenv()

class Settings:

    # Open API
    API_URL = os.getenv("API_URL")
    API_KEY = os.getenv("API_KEY")

    # Slack
    SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
    CHANNEL_ID = os.getenv("CHANNEL_ID")

    # Google API
    API_FILE = os.getenv("API_FILE")    
    
settings = Settings()
