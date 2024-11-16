import os
import time
import pandas as pd
import logging
from elasticsearch import Elasticsearch, helpers, ConnectionError
from errors.server_exception import ExternalAPIError

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


# Elasticsearch 클라이언트 설정 및 재시도 로직
es = None
retries = 10  # 재시도 횟수
for i in range(retries):
    try:
        es = Elasticsearch(
            settings.ELASTICSEARCH_HOST,
            basic_auth=(settings.ELASTICSEARCH_USERNAME, settings.ELASTICSEARCH_PASSWORD)
        )
        # 연결 확인
        if es.ping():
            logger.info("Elasticsearch에 성공적으로 연결되었습니다.")
            break
    except ConnectionError:
        logger.warning(f"Elasticsearch 연결 시도 {i+1}/{retries}번 실패. 재시도 중")
        # 5초 대기
        time.sleep(5)  
else:
    logger.error("Elasticsearch에 연결할 수 없습니다.")
    raise ExternalAPIError()


# 인덱스 이름 설정
index_name = "food_names"


# 인덱스 매핑 생성
if not es.indices.exists(index=index_name):
    # Standard 분석기 및 임베딩 벡터 필드를 포함한 인덱스 설정
    es.indices.create(
        index=index_name,
        body={
            "settings": {
                "index": {
                    "analysis": {
                        "analyzer": {
                            "standard_analyzer": {
                                "type": "standard"
                            }
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "food_pk": {
                        "type": "integer"
                    },
                    "food_name": {
                        "type": "text",
                        "analyzer": "standard_analyzer",
                        "search_analyzer": "standard"
                    },
                    "embedding": {
                        "type": "dense_vector",
                        # 임베딩 차원: 512도 가능
                        "dims": 512  
                    }
                }
            }
        }
    )
    logger.info("Elasticsearch 인덱스가 생성되었습니다.")


# 환경 변수에 따른 데이터셋 경로 설정
if os.getenv("APP_ENV") == "prod":
    # 운영
    df = pd.read_csv(os.path.join(settings.DATA_PATH, "food.csv"))
else:
    # 개발
    df = pd.read_csv(os.path.join(settings.DOCKER_DATA_PATH, "food.csv"))


# '_'(underbar)를 공백으로 대체 : 해당 로직 적용시 pk 값 찾지 못해 사용하지 않음
# df['FOOD_NAME'] = df['FOOD_NAME'].str.replace('_', ' ')


# Elasticsearch에 적재할 데이터 준비
actions = []
for _, row in df.iterrows():
    # 문자열 형태의 리스트를 리스트로 변환
    embedding = eval(row['EMBEDDING'])  
    actions.append({
        "_index": index_name,
        "_source": {
            "food_pk": row["FOOD_PK"],
            "food_name": row['FOOD_NAME'],
            "embedding": embedding
        }
    })

# 시간 측정 시작
start_time = time.time()

# Bulk API로 데이터 적재
# chunk_size를 사용하여 elasticsearch 부하 조절
helpers.bulk(es, actions, chunk_size=1000)

# 시간 측정 종료
end_time = time.time()
logger.info(f"Elasticsearch 인덱스 '{index_name}'에 음식명과 임베딩이 함께 적재되었습니다.")
logger.info(f"총 소요 시간: {end_time - start_time:.2f}초")