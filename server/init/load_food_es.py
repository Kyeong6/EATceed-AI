import os
import pandas as pd
from core.config import settings
from elasticsearch import Elasticsearch, helpers


# Elasticsearch 클라이언트 설정
es = Elasticsearch(
    settings.ELASTICSEARCH_HOST, 
    basic_auth=(settings.ELASTICSEARCH_USERNAME, settings.ELASTICSEARCH_PASSWORD))


# 인덱스 이름 설정
index_name = "food_names"


# 인덱스 매핑 생성
if not es.indices.exists(index=index_name):
    # Standard 분석기 기반 인덱스 설정
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
                    "food_name": {
                        "type": "text",
                        "analyzer": "standard_analyzer",  # Standard 분석기 적용
                        "search_analyzer": "standard"
                    }
                }
            }
        }
    )



# 데이터셋 불러오기
df = pd.read_csv(os.path.join(settings.DOCKER_DATA_PATH, "food.csv"))


# '_'(underbar)를 공백으로 대체
df['FOOD_NAME'] = df['FOOD_NAME'].str.replace('_', ' ')


# 데이터 적재 세팅
actions = [
    {
        "_index": index_name,
        "_source": {
            "food_name": row['FOOD_NAME']
        }
    }
    for _, row in df.iterrows()
]


# Bulk API로 데이터 적재
helpers.bulk(es, actions)
print(f"Elasticsearch 인덱스 '{index_name}'에 데이터가 적재되었습니다.")