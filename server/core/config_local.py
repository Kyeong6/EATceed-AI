# 환경변수 설정
import os
from dotenv import load_dotenv


# 개발 환경
load_dotenv(dotenv_path=".env.local")

class Settings:

    # Auth
    JWT_SECRET = os.getenv("JWT_SECRET")
    TEST_TOKEN = os.getenv("TEST_TOKEN")

    # Decryption
    ENCRYPTION_SECRET = os.getenv("ENCRYPTION_SECRET")

    # Swagger
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

    # OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    # Upstage
    UPSTAGE_API_KEY = os.getenv("UPSTAGE_API_KEY")

    # Data
    DATA_PATH = os.getenv("DATA_PATH")
    DOCKER_DATA_PATH = os.getenv("DOCKER_DATA_PATH")
    PROMPT_PATH = os.getenv("PROMPT_PATH")

    # Test
    TEST_PATH = os.getenv("TEST_PATH")

    # Log
    LOG_PATH = os.getenv("LOG_PATH")

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

    # Redis
    REDIS_HOST = os.getenv("REDIS_HOST")
    REDIS_LOCAL_HOST = os.getenv("REDIS_LOCAL_HOST")
    REDIS_PORT = int(os.getenv("REDIS_PORT"))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
    RATE_LIMIT = int(os.getenv("RATE_LIMIT"))

    # GCP
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    
    
settings = Settings()