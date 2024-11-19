import os
import sys
import time
from db.database import engine
from logs.logger_config import get_logger

# 환경에 따른 설정 파일 로드
if os.getenv("APP_ENV") == "prod":
    from core.config_prod import settings
else:
    from core.config import settings

# 공용 로거
logger = get_logger()

# DB 접속 URL 설정 유무 확인
if not settings.DB_URL:
    logger.error("DB_URL 환경 변수가 설정되지 않았습니다.")
    sys.exit(1)

# DB 연결 유무 확인
def check_db_connection():
    retries = 5
    for i in range(retries):
        try:
            with engine.connect() as connection:
                logger.info(f"DB 연결 성공: {settings.DB_URL}")
                return
        except Exception as e:
            logger.error(f"ERROR: DB 연결 실패(재시도 횟수-{i+1}/{retries}): {e}")
            time.sleep(5)
    
    logger.error("DB 연결 모두 실패(재시도 횟수 초과)")
    sys.exit(1)

if __name__ == "__main__":
    check_db_connection()
