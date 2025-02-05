from logs.logger_config import get_logger

# 공용 로거 
logger = get_logger()

# 스케줄러 이벤트 리스너 함수
def scheduler_listener(event):
    if event.exception:
        logger.error(f"스케줄러 작업 실패: {event.job_id} - {event.exception}")
    else:
        logger.info(f"스케줄러 작업 종료: {event.job_id}")