import logging
import os
import pytz 
from datetime import datetime 

# 환경에 따른 설정 파일 로드
if os.getenv("APP_ENV") == "prod":
    from core.config_prod import settings
else:
    from core.config import settings

# 로그 디렉토리 설정
os.makedirs(settings.LOG_PATH, exist_ok=True)

# Formatter 클래스
class KSTFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        # 한국 시간대 설정
        kst = pytz.timezone("Asia/Seoul")
        dt = datetime.fromtimestamp(record.created, tz=kst)
        if datefmt:
            return dt.strftime(datefmt)
        else:
            return dt.isoformat()


# 공용 로거 생성(INFO, ERROR)
def get_logger():
    logger = logging.getLogger("app_logger")
    # 중복 핸들러 방지
    if not logger.handlers:  
        logger.setLevel(logging.INFO)  

         # 포매터 설정
        formatter = KSTFormatter(
            '%(asctime)s - %(levelname)s - %(funcName)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # INFO 로그 핸들러
        info_handler = logging.FileHandler(os.path.join(settings.LOG_PATH, "info.log"))
        info_handler.setLevel(logging.INFO)
        info_handler.setFormatter(formatter)

        # INFO 필터 추가
        class InfoFilter(logging.Filter):
            def filter(self, record):
                return record.levelno == logging.INFO

        info_handler.addFilter(InfoFilter())
        logger.addHandler(info_handler)

        # ERROR 로그 핸들러
        error_handler = logging.FileHandler(os.path.join(settings.LOG_PATH, "error.log"))
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)

        # ERROR 필터 추가 
        class ErrorFilter(logging.Filter):
            def filter(self, record):
                return record.levelno == logging.ERROR

        error_handler.addFilter(ErrorFilter())
        logger.addHandler(error_handler) 

    return logger
