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
    es.indices.create(
        index=index_name,
        body={
            # mapping 설정
            "mappings": {
                "properties": {
                    "food_category_code": {
                        # 식품대분류코드를 범위로 사용하여 유사도 분석 진행 범위 줄이기
                        "type": "keyword"
                    },
                    "food_name": {
                        "type": "text",
                        # n-gram 분석기 적용
                        "analyzer": "ngram_analyzer",  
                        # 검색 시 standard 분석기로 매칭
                        "search_analyzer": "standard"  
                    }
                }
            },
            "settings": {
                # max_gram - min_gram 차이 허용
                "index.max_ngram_diff": 2,
                "analysis": {
                    "analyzer": {
                        "ngram_analyzer": {
                            "type": "custom",
                            "tokenizer": "ngram_tokenizer",
                        }
                    },
                    "tokenizer": {
                        "ngram_tokenizer": {
                            # n-gram 분석: 3(최소) ~ 5(최대글자 단위로 분리하여 검색 가능
                            "type": "ngram",
                            "min_gram": 3,
                            "max_gram": 5,
                            "token_chars": ["letter", "digit"]
                        }
                    }
                }
            }
        }
    )



# 데이터셋 불러오기
df = pd.read_csv(os.path.join(settings.DATA_PATH, "food.csv"))


# '_'(underbar)를 공백으로 대체
df['FOOD_NAME'] = df['FOOD_NAME'].str.replace('_', ' ')


# 데이터 적재 세팅
actions = [
    {
        "_index": index_name,
        "_source": {
            "food_category_code": row['FOOD_CODE'],
            "food_name": row['FOOD_NAME']
        }
    }
    for _, row in df.iterrows()
]


# Bulk API로 데이터 적재
helpers.bulk(es, actions)
print(f"Elasticsearch 인덱스 '{index_name}'에 데이터가 적재되었습니다.")