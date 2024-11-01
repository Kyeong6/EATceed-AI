import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, ValidationError
from apis.api import food_image_analyze, search_similar_food
from auth.decoded_token import get_current_member
from db.database import get_db
from db.crud import get_food_pk_by_name
from errors.custom_exceptions import InvalidJWT, AnalysisError

router = APIRouter(
    prefix="/v1/ai/food_image_analysis",
    tags=["음식 이미지 분석"]
)

# 음식 이미지 분석 API 테스트
@router.post("/test")
async def food_image_analysis_test():
    return {"success": "성공"}


# 리팩토링 과정에서 pydantic 위치 변경 진행할 예정
class ImageAnalysisRequest(BaseModel):
    # base64에 따른 문자열 타입 설정 
    image_base64: str


# 음식 이미지 분석 API
@router.post("/")
async def analyze_food_image(request: ImageAnalysisRequest,
                            db: Session = Depends(get_db), member_id: int = Depends(get_current_member)):
    
    # 인증 확인
    if not member_id:
        raise InvalidJWT()
    
    """
    1. 요청 횟수 제한 구현(Redis)
    """

    # OpenAI API를 이용한 이미지 분석: 음식명과 음식대분류코드 결과 얻기
    try:
        # OpenAI API 호출로 이미지 분석 및 음식명 추출
        detected_food_data = food_image_analyze(request.image_base64)
        # 문자열로 반환된 데이터 JSON으로 변환
        detected_food_data = json.loads(detected_food_data)

        # 음식명 분석 결과가 없을 경우
        if not detected_food_data:
            raise AnalysisError("음식 분석 결과가 비어있습니다.")
        
    except json.JSONDecodeError:
        raise AnalysisError("이미지 분석 결과의 형식이 잘못되었습니다.")
    except ValidationError as e:
        raise AnalysisError(f"이미지 분석 중 오류 발생: {str(e)}")

    """
    2. food_image_analyze 함수를 통해 얻은 음식명(리스트 값)을 이용해 
    Elasticsearch 유사도 검색을 진행해 유사도가 높은 음식(들) 반환 진행
    """
    # 유사도 검색 결과 저장할 리스트 초기화
    similar_food_results = []

    # 유사도 검색 진행
    for food_data in detected_food_data:
        # 데이터 형식 확인 후 인덱싱 접근
        food_name = food_data["food_name"] if isinstance(food_data, dict) else None

        # 음식명 또는 코드 누락
        if not food_name:
            raise AnalysisError("음식명 데이터가 누락되었습니다.")
        
        try:
            # Elasticsearch에서 유사도 분석 수행
            similar_foods = search_similar_food(food_name)

            # 유사도 분석 결과에서 음식명 리스트 추출
            similar_food_names = [similar_food["_source"]["food_name"] for similar_food in similar_foods]
            if not similar_food_names:
                raise AnalysisError(f"유사도 분석 결과가 없습니다: food_name={food_name}")

            
            # 유사도 분석 진행 후 얻은 음식의 pk값 얻기
            food_pks = get_food_pk_by_name(db, similar_food_names)

            # 결과 형식에 맞게 데이터 정리 진행
            similar_food_list = [
                {"food_name": name, "food_pk": food_pks.get(name)}
                for name in similar_food_names
            ]
            
            # detected_food와 해당 유사도 검색 결과 추가
            similar_food_results.append({
                "detected_food": food_name,
                "similar_foods": similar_food_list
            })
            
            # 반환값 구성
            response = {
                "success": True,
                "response": similar_food_results,
                "error": None
            }

        except Exception as e:
            raise AnalysisError(f"유사도 분석 중 오류 발생: {str(e)}")

    return response