import logging
import pytz
from datetime import datetime

# Formatter 클래스: 한국 시간 (KST) 적용
class KSTFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        kst = pytz.timezone("Asia/Seoul")
        dt = datetime.fromtimestamp(record.created, tz=kst)
        if datefmt:
            return dt.strftime(datefmt)
        else:
            return dt.isoformat()

# 공용 로거 생성 (CloudWatch 전용)
def get_logger():
    logger = logging.getLogger("lambda_logger")
    
    # 중복 핸들러 방지
    if not logger.hasHandlers():
        logger.setLevel(logging.INFO)

        # 포매터 설정 (KST 시간 적용)
        formatter = KSTFormatter(
            '%(asctime)s - %(levelname)s - %(funcName)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # CloudWatch에 출력하는 콘솔 핸들러 추가
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)

    return logger