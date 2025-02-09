import os
import time
import pytz
import asyncio
from datetime import datetime, timedelta
from core.config import settings
from core.config_redis import redis_client
from logs.logger_config import get_logger
from errors.business_exception import RateLimitExceeded
from errors.server_exception import ServiceConnectionError

# 로거 설정
logger = get_logger()

# 요청 제한 설정
RATE_LIMIT = settings.RATE_LIMIT  # 하루 최대 요청 가능 횟수


## 식습관 분석 API
# Redis 기반 Rate-limit 확인
async def rate_limit_check():

    current_minute = int(time.time() // 60)
    key = f"api_calls:{current_minute}"
    count = redis_client.incr(key)
    if count == 1:
        redis_client.expire(key, 60)
    if count > 500:
        # 다음 분 시작
        sleep_time = 60 - (time.time() % 60) + 1
        logger.info(f"[Rate-Limit] 호출횟수 {count}회 - 분당 제한 초과. {sleep_time:.2f}초 대기")
        await asyncio.sleep(sleep_time)
    elif count > 1:
        redis_client.delete(key)


## 음식 이미지 탐지 API
# Redis 기반 요청 제한 함수
def rate_limit_user(user_id: int, increment=False):
    redis_key = f"rate_limit:{user_id}"
    current_count = redis_client.get(redis_key)

    # 요청 횟수 확인
    if current_count:
        if int(current_count) >= RATE_LIMIT:
            logger.info(f"음식 이미지 분석 기능 횟수 제한: {user_id}")
            # 기능 횟수 제한 예외처리
            raise RateLimitExceeded()
    
    # 요청 성공시에만 증가
    if increment:
        redis_client.incr(redis_key)
        if current_count is None:
            # 매일 자정 횟수 리셋
            next_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            redis_client.expireat(redis_key, int(next_time.timestamp()))
    
    remaining_requests = RATE_LIMIT - int(current_count or 0) - (1 if increment else 0)

    return remaining_requests

# Redis의 정의된 잔여 기능 횟수 확인
async def get_remaining_requests(member_id: int):

    try:
        # Redis 키 생성
        redis_key = f"rate_limit:{member_id}"

        # Redis에서 사용자의 요청 횟수 조회
        current_count = redis_client.get(redis_key)

        # 요청 횟수가 없다면 기본값 반환(RATE_LIMIT)
        if current_count is None:
            return RATE_LIMIT

        # 남은 요청 횟수
        remaining_requests = max(RATE_LIMIT - int(current_count), 0)
        return remaining_requests

    except Exception as e:
        logger.error(f"잔여 기능 횟수 확인 중 에러가 발생했습니다: {e}")
        raise ServiceConnectionError()