import os
import base64
import redis
import time
from datetime import datetime, timedelta
from openai import OpenAI
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

# 공용 로거
logger = get_logger()

# OpenAI API 사용
client = OpenAI(api_key = settings.OPENAI_API_KEY)

# Upsage API 사용
upstage = OpenAI(
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
def read_prompt(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        prompt = file.read().strip()
    return prompt


# 음식 이미지 분석 API: prompt_type은 함수명과 동일
def food_image_analyze(image_base64: str):

    # prompt 타입 설정
    prompt_file = os.path.join(settings.PROMPT_PATH, "image_detection.txt")
    prompt = read_prompt(prompt_file)

    # prompt 내용 없을 경우
    if not prompt:
        logger.error("image_detection.txt에 prompt 내용 미존재")
        raise FileAccessError()

    # OpenAI API 호출
    response = client.chat.completions.create(
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

    # 음식명(반환값)이 존재하지 않을 경우
    if not result:
        logger.error("OpenAI API 음식명 얻기 실패")
        raise ImageAnalysisError()

    # 음식 이미지 분석 
    return result


# 제공받은 음식의 벡터 임베딩 값 변환 작업 수행(Upstage-Embedding 사용)
def get_embedding(text, model="embedding-query"):
    text = text.replace("\n", " ")
    embedding = upstage.embeddings.create(
        input=[text], 
        model=model).data[0].embedding
    
    return embedding


# 벡터 임베딩을 통한 유사도 분석 진행(Pinecone)
def search_similar_food(query_name, top_k=3, score_threshold=0.7, candidate_multiplier=2):
    
    # 음식명 Embedding Vector 변환
    try:
        query_vector = get_embedding(query_name)
    except Exception as e:
        logger.error(f"OpenAI API 텍스트 임베딩 실패: {e}")
        raise ExternalAPIError()

    # Pinecone에서 유사도 검색
    results = index.query(
        vector=query_vector,
        # 결과값 갯수 설정: 후처리 진행을 위한 많은 후보군 확보
        top_k=top_k * candidate_multiplier,
        # 메타데이터 포함 유무
        include_metadata=True
    )

    # 유사도 임계값을 넘는 후보들을 리스트로 구성
    candidates = []
    for match in results['matches']:
        if match['score'] >= score_threshold:
            candidate = {
                "fook_pk": match['id'],
                "food_name": match['metadata'].get("food_name"),
                "score": match['score']
            }
            candidates.append(candidate)
    
    # 후보 리스트를 유사도 점수 기준으로 내림차순 정렬
    sorted_candidates = sorted(candidates, key=lambda x: x["score"], reverse=True)

    # 최종적으로 상위 top_k개 선택
    final_results = sorted_candidates[:top_k]

    # 후보가 top_k개 미만일 경우 None으로 패딩
    while len(final_results) < top_k:
        final_results.append({'food_name': None, 'food_pk': None})

    return final_results


# Redis의 정의된 잔여 기능 횟수 확인
def get_remaining_requests(member_id: int):

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