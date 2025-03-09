from sqlalchemy.orm import Session
from database.models import Food
from pinecone.grpc import PineconeGRPC as Pinecone
from core.config import settings
from utils.embedding import get_embedding
from database.session import get_db
from logs.get_logger import get_logger

logger = get_logger()

# Pinecone 인스턴스 생성
pc = Pinecone(api_key=settings.PINECONE_API_KEY)

# 데이터베이스에 적재
def insert_food_data(db: Session, food_data: dict):
    try:
        new_food = Food(
            FOOD_CODE=food_data["식품코드"],
            FOOD_NAME=food_data["식품명"],
            FOOD_CATEGORY_CODE=food_data["식품대분류코드"],
            FOOD_SERVING_SIZE=food_data["식품중량"],
            FOOD_CALORIE=food_data["에너지(kcal)"],
            FOOD_CARBOHYDRATE=food_data["탄수화물(g)"],
            FOOD_PROTEIN=food_data["단백질(g)"],
            FOOD_FAT=food_data["지방(g)"],
            FOOD_SUGARS=food_data["당류(g)"],
            FOOD_DIETARY_FIBER=food_data["식이섬유(g)"],
            FOOD_SODIUM=food_data["나트륨(mg)"],
            MEMBER_FK=None
        )

        db.add(new_food)
        db.commit()
        db.refresh(new_food)

        return new_food.FOOD_PK
    
    except Exception as e:
        print(f"FOOD_TB 데이터 삽입 중 오류 발생: {e}")
        db.rollback()
        raise 

# Pinecone 인덱스 초기화
def initialize_pinecone_index(index_name: str):
    try:
        # 인덱스 확인
        if settings.INDEX_NAME not in pc.list_indexes().names():
            logger.error(f"'{index_name}' 인덱스 미존재")
            return None
        
        # 인덱스 객체 반환
        return pc.Index(host=settings.INDEX_HOST)
    
    except Exception as e:
        logger.error(f"Pinecone 인덱스 초기화 중 오류 발생: {e}")
        return None


# Pinecone 적재
def insert_food_data_embedding(food_pks: list, index_name: str):
    # Pinecone 인덱스 초기화
    index = initialize_pinecone_index(index_name)
    if not index:
        logger.error("Pinecone 인덱스 초기화 실패: 적재 중단")
        return

    # DB 연결
    db = next(get_db())

    try:
        # 새로 추가된 데이터 가져오기
        new_foods = db.query(Food).filter(Food.FOOD_PK.in_(food_pks)).all()

        if not new_foods:
            logger.info("Pinecone에 적재할 새로운 데이터 미존재")
            return 

        # 벡터화 및 Pinecone 적재
        batch_size = 100
        vectors = []

        for food in new_foods:
            embedding = get_embedding(food.FOOD_NAME)
            if embedding:
                vectors.append({
                    "id": str(food.FOOD_PK),
                    "values": embedding,
                    "metadata": {"food_name": food.FOOD_NAME}
                })

            # 배치 크기마다 Pinecone 업로드 실행
            if len(vectors) >= batch_size:
                index.upsert(vectors=vectors)

                logger.info(f"Pinecone에 {len(vectors)}개 데이터 업로드 완료")
                # 리스트 초기화
                vectors = []

        # 남아있는 벡터가 있으면 업로드
        if vectors:
            index.upsert(vectors=vectors)

        logger.info(f"{len(new_foods)}개의 데이터 Pinecone에 적재")

    except Exception as e:
        logger.error(f"Pinecone 데이터 적재 중 오류 발생: {e}")
        raise

    finally:
        db.close()