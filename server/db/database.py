# Connection + Session
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 환경에 따른 설정 파일 로드
if os.getenv("APP_ENV") == "prod":
    from core.config_prod import settings
elif os.getenv("APP_ENV") == "dev":
    from core.config_dev import settings
else:
    from core.config_local import settings

db_url = settings.DB_URL

engine = create_engine(
    db_url,
    pool_recycle=3600,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()