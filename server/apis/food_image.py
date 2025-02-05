import os
import base64
import redis
import aiofiles
import time
from datetime import datetime, timedelta
from openai import AsyncOpenAI
from pinecone.grpc import PineconeGRPC as Pinecone
from core.config import settings
from errors.business_exception import RateLimitExceeded, ImageAnalysisError, ImageProcessingError
from errors.server_exception import FileAccessError, ServiceConnectionError, ExternalAPIError
from logs.logger_config import get_logger

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

# 요청 제한 설정
RATE_LIMIT = settings.RATE_LIMIT  # 하루 최대 요청 가능 횟수

# 프롬프트 캐싱
CACHE_TTL = 3600

# 공용 로거
logger = get_logger()

# OpenAI API 사용
client = AsyncOpenAI(api_key = settings.OPENAI_API_KEY)

# Upsage API 사용
upstage = AsyncOpenAI(
    api_key = settings.UPSTAGE_API_KEY,
    base_url="https://api.upstage.ai/v1/solar"
)

# Pinecone 설정
pc = Pinecone(api_key=settings.PINECONE_API_KEY)
index = pc.Index(host=settings.INDEX_HOST)


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


# Multi-part 방식 이미지 처리 및 Base64 인코딩
async def process_image_to_base64(file):
    try:
        # 파일 읽기
        file_content = await file.read()

        # Base64 인코딩
        image_base64 = base64.b64encode(file_content).decode("utf-8")
        
        return image_base64
    except Exception as e:
        logger.error(f"이미지 파일 처리 및 Base64 인코딩 실패: {e}")
        raise ImageProcessingError()


# prompt를 불러오기
async def read_prompt(filename):

    # Redis에서 캐싱된 프롬프트 확인
    cached_prompt = redis_client.get(f"prompt:{filename}")

    if cached_prompt:
        # logger.info(f"Redis 캐싱 프롬프트 사용: {filename}")
        return cached_prompt

    try:
        async with aiofiles.open(filename, 'r', encoding='utf-8') as file:
            prompt =  (await file.read()).strip()
        
        if not prompt:
            logger.error("프롬프트 파일 비어있음")
            raise FileAccessError()
        
        # Redis에 프롬프트 캐싱(TTL : 1 hr)
        redis_client.setex(f"prompt:{filename}", CACHE_TTL, prompt)
        logger.info(f"Redis 프롬프트 캐싱 완료: {filename}")

        return prompt

    except Exception as e:
        logger.error(f"프롬프트 파일 읽기 실패: {e}")
        raise FileAccessError()


# 음식 이미지 분석 API: prompt_type은 함수명과 동일
async def food_image_analyze(image_base64: str):

    # prompt 타입 설정
    prompt_file = os.path.join(settings.PROMPT_PATH, "image_detection.txt")
    prompt = await read_prompt(prompt_file)

    # prompt 내용 없을 경우
    if not prompt:
        logger.error("image_detection.txt에 prompt 내용 미존재")
        raise FileAccessError()

    # OpenAI API 호출
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}",
                            # 성능이 좋아지지만, token 소모 큼(tradeoff): 검증 필요
                            # "detail": "high"
                        }
                    }
                ]
            },
            {"role": "system", "content": prompt}
        ],
        temperature=0.0,
        max_tokens=300
    )
    
    result = response.choices[0].message.content
    # print(result)

    # 음식명(반환값)이 존재하지 않을 경우
    if not result:
        logger.error("OpenAI API 음식명 얻기 실패")
        raise ImageAnalysisError()

    # 음식 이미지 분석 
    return result


# 제공받은 음식의 벡터 임베딩 값 변환 작업 수행(Upstage-Embedding 사용)
async def get_embedding(text, model="embedding-query"):
    try:
        text = text.replace("\n", " ")
        response = await upstage.embeddings.create(input=[text], model=model)
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"텍스트 임베딩 변환 실패: {e}")
        raise ExternalAPIError()


# 벡터 임베딩을 통한 유사도 분석 진행(Pinecone)
async def search_similar_food(query_name, top_k=3, score_threshold=0.7, candidate_multiplier=2):
    try:
        # 음식명 Embedding Vector 변환
        query_vector = await get_embedding(query_name)

        # Pinecone에서 유사도 검색
        results = index.query(
            vector=query_vector,
            top_k=top_k * candidate_multiplier,
            include_metadata=True
        )

        # 결과 처리 (점수 필터링 적용)
        candidates = [
            {
                'food_pk': match['id'],
                'food_name': match['metadata']['food_name'],
                'score': match['score']
            }
            for match in results['matches'] if match['score'] >= score_threshold
        ]

        # 유사도 점수를 기준으로 내림차순 정렬
        sorted_candidates = sorted(candidates, key=lambda x: x["score"], reverse=True)

        # 상위 top_k개 선택
        final_results = sorted_candidates[:top_k]

        # null로 채워서 항상 top_k 크기로 반환
        while len(final_results) < top_k:
            final_results.append({'food_name': None, 'food_pk': None})

        return final_results

    except Exception as e:
        logger.error(f"유사도 검색 실패: {e}")
        raise ExternalAPIError()


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