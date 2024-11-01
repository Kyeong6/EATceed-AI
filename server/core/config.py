# 환경변수 설정
from dotenv import load_dotenv
import os
import logging

# 로그 설정
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# APP_ENV 환경 변수에 따라 개발 / 운영 환경 설정
"""
개발 환경 : export APP_ENV=dev
운영 환경 : export APP_ENV=prod
"""
env_file = f".env.{os.getenv('APP_ENV', 'dev')}"

load_dotenv(dotenv_path=env_file)

class Settings:

    # 인증
    JWT_SECRET = os.getenv("JWT_SECRET")
    TEST_TOKEN = os.getenv("TEST_TOKEN")

    # Swagger
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

    # OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    # Data
    DATA_PATH = os.getenv("DATA_PATH")
    DOCKER_DATA_PATH = os.getenv("DOCKER_DATA_PATH")
    PROMT_PATH = os.getenv("PROMT_PATH")

    # MariaDB
    RDS_DATABASE_ENDPOINT = os.getenv("RDS_DATABASE_ENDPOINT")
    RDS_DATABASE_USERNAME = os.getenv("RDS_DATABASE_USERNAME")
    RDS_DATABASE_PASSWORD = os.getenv("RDS_DATABASE_PASSWORD")
    RDS_PORT = os.getenv("RDS_PORT")
    RDS_DB_NAME = os.getenv("RDS_DB_NAME")
    DB_URL=f"mysql+pymysql://{RDS_DATABASE_USERNAME}:{RDS_DATABASE_PASSWORD}@{RDS_DATABASE_ENDPOINT}:{RDS_PORT}/{RDS_DB_NAME}?charset=utf8mb4"

    # Elasticsearch
    ELASTICSEARCH_HOST=os.getenv("ELASTICSEARCH_HOST")
    ELASTICSEARCH_LOCAL_HOST =os.getenv("ELASTICSEARCH_LOCAL_HOST")
    ELASTICSEARCH_USERNAME=os.getenv("ELASTICSEARCH_USERNAME")
    ELASTICSEARCH_PASSWORD=os.getenv("ELASTICSEARCH_PASSWORD")

    # Redis
    REDIS_HOST=os.getenv("REDIS_HOST")
    REDIS_PASSWORD=os.getenv("REDIS_PASSWORD")
    
    
settings = Settings()

# 환경 변수 값 디버그 출력
logger.debug(f"DB_URL: {settings.DB_URL}")