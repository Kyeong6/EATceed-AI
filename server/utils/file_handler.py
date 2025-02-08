import os
import redis
import time
import aiofiles
from errors.server_exception import FileAccessError
from logs.logger_config import get_logger
from core.config import settings

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

# 전역 메모리 캐시
prompt_cache = {}
prompt_timestamps = {}

# prompt 불러오기
async def read_prompt(filename: str, category: str, ttl: int):
    
    global prompt_cache, prompt_timestamps

    # 파일 마지막 수정 시간 확인
    try:
        last_modified_time = os.path.getmtime(filename)
    except Exception as e:
        logger.error(f"파일을 찾을 수 없음: {filename}")
        raise FileAccessError()
    
    # 기존 캐시에 동일한 내용이 있으면 그대로 사용
    if category == "diet" and filename in prompt_cache:
        if prompt_timestamps.get(filename) == last_modified_time:
            return prompt_cache[filename]
        
    # Redis에서 캐싱된 프롬프트 확인
    redis_key = f"prompt:{category}:{filename}"
    cached_prompt = redis_client.get(redis_key)

    if cached_prompt:
        return cached_prompt
    
    # 파일에서 직접 읽기
    try:
        async with aiofiles.open(filename, 'r', encoding='utf-8') as file:
            prompt = (await file.read()).strip()
        
        if not prompt:
            raise FileAccessError()
        
        # 기존 데이터와 다르면 캐시 업데이트
        if category == "diet":
            if filename in prompt_cache and prompt_cache[filename] == prompt:
                return prompt

            # 내용 변경
            prompt_cache[filename] = prompt
            prompt_timestamps[filename] = last_modified_time

        # Redis에 캐싱
        redis_client.setex(redis_key, ttl, prompt)
        return prompt

    except Exception as e:
        logger.error(f"프롬프트 파일 읽기 실패: {e}")
        raise FileAccessError()
    
# 식습관 분석 프롬프트 미리 로드
async def load_all_prompts():
    
    prompt_files = [
        "diet_advice.txt", "nutrition_analysis.txt", "diet_improvement.txt",
        "custom_recommendation.txt", "diet_summary.txt", "diet_eval.txt"
    ]

    for filename in prompt_files:
        await read_prompt(filename=os.path.join(settings.PROMPT_PATH, filename), category="diet", ttl=604800)