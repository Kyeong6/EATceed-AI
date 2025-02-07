import os
import redis
import time
import aiofiles
from errors.server_exception import FileAccessError
from logs.logger_config import get_logger
from core.config import settings

# 프롬프트 캐싱
CACHE_TTL = 3600

# 환경에 따른 설정 파일 로드
if os.getenv("APP_ENV") in ["prod", "dev"]:

    # 운영: Redis 클라이언트 설정
    redis_client = redis.StrictRedis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        decode_responses=True
    )
else:
    # 개발: Redis 클라이언트 설정
    redis_client = redis.StrictRedis(
        host=settings.REDIS_LOCAL_HOST,  
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        decode_responses=True
    )

# 공용 로거 
logger = get_logger()

# prompt를 불러오기
def read_prompt(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        prompt = file.read().strip()

    if not prompt:
        logger.error("prompt 파일을 불러오기에 실패했습니다.")
        raise FileAccessError()
    
    return prompt

# # prompt를 불러오기
# async def read_prompt(filename):

#     # Redis에서 캐싱된 프롬프트 확인
#     cached_prompt = redis_client.get(f"prompt:{filename}")

#     if cached_prompt:
#         # logger.info(f"Redis 캐싱 프롬프트 사용: {filename}")
#         return cached_prompt

#     try:
#         async with aiofiles.open(filename, 'r', encoding='utf-8') as file:
#             prompt =  (await file.read()).strip()
        
#         if not prompt:
#             logger.error("프롬프트 파일 비어있음")
#             raise FileAccessError()
        
#         # Redis에 프롬프트 캐싱(TTL : 1 hr)
#         redis_client.setex(f"prompt:{filename}", CACHE_TTL, prompt)
#         logger.info(f"Redis 프롬프트 캐싱 완료: {filename}")

#         return prompt

#     except Exception as e:
#         logger.error(f"프롬프트 파일 읽기 실패: {e}")
#         raise FileAccessError()