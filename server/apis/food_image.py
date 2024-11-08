import os
import redis
from datetime import datetime, timedelta
from core.config import settings
from errors.exception import RateLimitExceeded, AnalysisError
from openai import OpenAI
from elasticsearch import Elasticsearch


# Chatgpt API 사용
client = OpenAI(api_key = settings.OPENAI_API_KEY)

# Elasticsearch 클라이언트 설정
es = Elasticsearch(
    settings.ELASTICSEARCH_LOCAL_HOST, 
    http_auth=(settings.ELASTICSEARCH_USERNAME, settings.ELASTICSEARCH_PASSWORD))


# Redis 클라이언트 설정
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


# prompt를 불러오기
def read_prompt(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        prompt = file.read().strip()
    return prompt


# 음식 이미지 분석 API: prompt_type은 함수명과 동일
def food_image_analyze(image_base64: str):

    try:
        # prompt 타입 설정
        prompt_file = os.path.join(settings.PROMPT_PATH, "food_image_analyze.txt")
        prompt = read_prompt(prompt_file)

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
                                # 검증 필요
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

        return result
    except Exception:
        raise AnalysisError()


# 제공받은 음식의 벡터 임베딩 값 변환 작업 수행
def get_embedding(text, model="text-embedding-3-small"):
    text = text.replace("\n", " ")
    embedding = client.embeddings.create(input=[text], model=model).data[0].embedding
    return embedding


# 벡터 임베딩을 통한 유사도 분석 진행
"""
서버 예외처리 필요 : 유사도 분석 진행 중 오류 발생
"""
def search_similar_food(query_name):
    index_name = "food_names"

    # OpenAI API를 사용하여 임베딩 생성
    query_vector = get_embedding(query_name)

    # Elasticsearch 벡터 유사도 검색
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

    # 검색 결과: food_name, food_pk 추출
    hits = response.get('hits', {}).get('hits', [])
    
    # 검색 결과가 있을 경우 food_name과 food_pk 추출, 없을 경우 null로 설정: AOS와 논의 필요
    result = [{"food_name": hit["_source"]["food_name"], "food_pk": hit["_source"]["food_pk"]} for hit in hits] if hits else [{"food_name": None, "food_pk": None}]

    # 결과 확인
    # print("Search result:", result)
    
    # 최대 3개의 결과 반환 또는 null
    return result  