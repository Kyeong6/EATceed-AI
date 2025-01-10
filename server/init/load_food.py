import os
import time
import pandas as pd
from errors.server_exception import ExternalAPIError, FileAccessError
from logs.logger_config import get_logger
from pinecone.grpc import PineconeGRPC as Pinecone

# 환경에 따른 설정 파일 로드
if os.getenv("APP_ENV") == "prod":
    from core.config_prod import settings
elif os.getenv("APP_ENV") == "dev":
    from server.core.config_dev import settings
else:
    from server.core.config_local import settings

# 공용 로거
logger = get_logger()

# Pinecone 인스턴스 생성
pc = Pinecone(api_key=settings.PINECONE_API_KEY)

# Pinecone 인덱스 초기화 및 반환
def initialize_pinecone_index(index_name: str):
    try:
        # 인덱스 확인
        if settings.INDEX_NAME not in pc.list_indexes().names():
            logger.error(f"'{index_name}' 인덱스가 없습니다.")
            raise ExternalAPIError()
        
        # 인덱스 객체 가져오기
        return pc.Index(host=settings.INDEX_HOST)
    
    except Exception as e:
        logger.error(f"Pinecone 인덱스 초기화 중 오류가 발생했습니다: {e}")
        raise ExternalAPIError()


# 환경 변수에 따른 데이터셋 경로 설정
def get_csv_path():
    if os.getenv("APP_ENV") == "prod":
        # 운영 환경
        return os.path.join(settings.DATA_PATH, "food.csv")
    else:
        # 개발 환경
        return os.path.join(settings.DOCKER_DATA_PATH, "food.csv")


# Pinecone 데이터 적재
def upload_data_to_pinecone(index_name: str):

    # Pinecone 인덱스 초기화
    index = initialize_pinecone_index(index_name)
    
    # 인덱스 상태 확인
    index_stats = index.describe_index_stats()
    total_vectors = index_stats["namespaces"].get("", {}).get("vector_count", 0)

    # Pinecone에 데이터가 존재할 경우 적재 스킵
    if total_vectors > 0:
        logger.info(f"Pinecone 인덱스 '{index_name}'에 이미 데이터가 존재하여 적재를 건너뜁니다.")
        return

    # CSV 데이터 경로 결정
    csv_path = get_csv_path()

    # CSV 데이터 로드
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        logger.error(f"CSV 파일 로드 중 오류가 발생했습니다: {e}")
        raise FileAccessError()

    # 데이터 변환 및 업로드
    batch_size = 100  # 배치 크기
    for i in range(0, len(df), batch_size):
        batch = df[i:i + batch_size]
        vectors = []
        for _, row in batch.iterrows():
            # 문자열 리스트를 실제 리스트로 변환
            embedding = eval(row['EMBEDDING'])
            vectors.append({
                # 고유 ID는 pk 값으로 설정
                'id': str(row['FOOD_PK']), 
                # 임베딩 벡터값
                'values': embedding, 
                # 음식명을 메타데이터로 저장
                'metadata': {'food_name': row['FOOD_NAME']}  
            })

        # 시간 측정 시작
        start_time = time.time()
    
        # Pinecone에 데이터 적재
        index.upsert(vectors=vectors)

        # 시간 측정 종료
        end_time = time.time()
        logger.info(f"총 소요 시간: {end_time - start_time:.2f}초")

    logger.info(f"{len(df)}개의 데이터가 Pinecone 인덱스 '{index_name}'에 업로드되었습니다.")

# 함수 호출 예시
upload_data_to_pinecone(settings.INDEX_NAME)