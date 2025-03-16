import os

from dotenv import load_dotenv

# .env 참조: 클라우드에서 .env 이용
load_dotenv()

class Settings:

    # Slack
    SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
    CHANNEL_ID = os.getenv("CHANNEL_ID")

    # OpenAI 
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    # Upstage
    UPSTAGE_API_KEY = os.getenv("UPSTAGE_API_KEY")

    # Google API
    API_FILE = os.getenv("API_FILE")

    # Pinecone
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    INDEX_HOST = os.getenv("INDEX_HOST")
    INDEX_NAME = os.getenv("INDEX_NAME")

    # MariaDB
    RDS_DATABASE_ENDPOINT = os.getenv("RDS_DATABASE_ENDPOINT")
    RDS_DATABASE_USERNAME = os.getenv("RDS_DATABASE_USERNAME")
    RDS_DATABASE_PASSWORD = os.getenv("RDS_DATABASE_PASSWORD")
    RDS_PORT = os.getenv("RDS_PORT")
    RDS_DB_NAME = os.getenv("RDS_DB_NAME")
    DB_URL=f"mysql+pymysql://{RDS_DATABASE_USERNAME}:{RDS_DATABASE_PASSWORD}@{RDS_DATABASE_ENDPOINT}:{RDS_PORT}/{RDS_DB_NAME}?charset=utf8mb4"
    
    
settings = Settings()
