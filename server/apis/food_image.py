import os
import logging
import base64
import redis
from datetime import datetime, timedelta
from openai import OpenAI
from elasticsearch import Elasticsearch
from errors.business_exception import RateLimitExceeded, ImageAnalysisError, ImageProcessingError
from errors.server_exception import FileAccessError, ServiceConnectionError, ExternalAPIError

# 환경에 따른 설정 파일 로드
if os.getenv("APP_ENV") == "prod":
    from core.config_prod import settings
else:
    from core.config import settings

# 로그 메시지
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(funcName)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

# Chatgpt API 사용
client = OpenAI(api_key = settings.OPENAI_API_KEY)


# 환경에 따른 설정 파일 로드
if os.getenv("APP_ENV") == "prod":

    # 운영: Elasticsearch 클라이언트 설정
    es = Elasticsearch(
        settings.ELASTICSEARCH_HOST,
        http_auth=(settings.ELASTICSEARCH_USERNAME, settings.ELASTICSEARCH_PASSWORD)
    )
    # 운영: Redis 클라이언트 설정
    redis_client = redis.StrictRedis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        decode_responses=True
    )
else:
    # 개발: Elasticsearch 클라이언트 설정
    es = Elasticsearch(
        settings.ELASTICSEARCH_LOCAL_HOST, 
        http_auth=(settings.ELASTICSEARCH_USERNAME, settings.ELASTICSEARCH_PASSWORD)
    )
    # 개발: Redis 클라이언트 설정
    redis_client = redis.StrictRedis(
        host=settings.REDIS_LOCAL_HOST,  
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        decode_responses=True
    )


# 요청 제한 설정
RATE_LIMIT = settings.RATE_LIMIT  # 하루 최대 요청 가능 횟수


# Redis 기반 요청 제한 함수
def rate_limit_user(user_id: int):
    redis_key = f"rate_limit:{user_id}"
    current_count = redis_client.get(redis_key)

    if current_count:
        if int(current_count) >= RATE_LIMIT:
            logger.info(f"음식 이미지 분석 기능 횟수 제한: {user_id}")
            # 기능 횟수 제한 예외처리
            raise RateLimitExceeded()
        redis_client.incr(redis_key)
        remaning_requests = RATE_LIMIT - int(current_count) - 1
    else:
        redis_client.set(redis_key, 1)
        # 매일 자정 횟수 리셋
        next_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        redis_client.expireat(redis_key, int(next_time.timestamp()))
        remaning_requests = RATE_LIMIT - 1

    return remaning_requests


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
    prompt_file = os.path.join(settings.PROMPT_PATH, "food_image_analyze.txt")
    prompt = read_prompt(prompt_file)

    # prompt 내용 없을 경우
    if not prompt:
        logger.error("food_image_analyze.txt에 prompt 내용 미존재")
        raise FileAccessError()

    # OpenAI API 호출
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                            # 성능이 좋아지지만, token 소모 큼(tradeoff): 검증 필요
                            # "detail": "high"
                        }
                    }
                ]
            }
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


# 제공받은 음식의 벡터 임베딩 값 변환 작업 수행
def get_embedding(text, model="text-embedding-3-small"):
    text = text.replace("\n", " ")
    embedding = client.embeddings.create(input=[text], model=model).data[0].embedding
    return embedding


# 벡터 임베딩을 통한 유사도 분석 진행
def search_similar_food(query_name):
    index_name = "food_names"

    # OpenAI API를 사용하여 임베딩 생성
    try:
        query_vector = get_embedding(query_name)
    except Exception:
        logger.error("OpenAI API 텍스트 임베딩 실패")
        raise ExternalAPIError()

    # Elasticsearch 벡터 유사도 검색
    try:
        response = es.search(
            index=index_name,
            body={
                "query": {
                    "script_score": {
                        "query": {"match_all": {}},
                        "script": {
                            # 코사인 유사도 진행
                            "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                            "params": {"query_vector": query_vector}
                        }
                    }
                },
                # 상위 3개의 유사한 결과 반환
                "size": 3  
            }
        )
    except Exception:
        logger.error("Elasticsearch 기능(유사도 분석) 실패")
        raise ServiceConnectionError()

    # 검색 결과: food_name, food_pk 추출
    hits = response.get('hits', {}).get('hits', [])

    # 검색 결과가 null 3개일 경우
    if not hits:
        logger.info("유사도 검색 결과가 없습니다: null 값 3개 반환")
    
    # 검색 결과가 있을 경우 food_name과 food_pk 추출, 없을 경우 null로 설정: AOS와 논의 필요
    result = [{"food_name": hit["_source"]["food_name"], "food_pk": hit["_source"]["food_pk"]} for hit in hits] if hits else [{"food_name": None, "food_pk": None}]
    
    # 최대 3개의 결과 반환 또는 null
    return result  