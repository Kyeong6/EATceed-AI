import json
from fastapi import APIRouter, Depends, File, UploadFile
from apis.food_image import food_image_analyze, search_similar_food, rate_limit_user, process_image_to_base64, get_remaining_requests
from auth.decoded_token import get_current_member
from errors.business_exception import InvalidFileFormat, InvalidFoodImageError
from swagger.response_config import analyze_food_image_responses, remaining_requests_check_responses
from logs.logger_config import get_logger
import time

# 공용 로거
logger = get_logger()


router = APIRouter(
    tags=["음식 이미지 분석"]
)

# # 음식 이미지 분석 API 테스트
# @router.post("/test")
# async def food_image_analysis_test():
#     return {"success": "성공"}


# # 음식 이미지 분석 API
# @router.post("/image", responses=analyze_food_image_responses)
# async def analyze_food_image(file: UploadFile = File(...), member_id: int = Depends(get_current_member)):

#     # 시작 시간 기록
#     start_time = time.time()

#     # 지원하는 파일 형식
#     ALLOWED_FILE_TYPES = ["image/jpeg", "image/png"]

#     # 파일 형식 검증
#     if file.content_type not in ALLOWED_FILE_TYPES:
#         raise InvalidFileFormat(allowed_types=ALLOWED_FILE_TYPES)

#     # 이미지 처리 및 Base64 인코딩 진행
#     image_base64 = await process_image_to_base64(file)

#     # OpenAI API 호출로 이미지 분석 및 음식명 추출
#     detected_food_data = await food_image_analyze(image_base64)

#     # 음식 이미지를 업로드하지 않았을 경우
#     if detected_food_data == {"error": True}:
#         # 해당 유저를 찾기 위한 예외처리 routers에 포함
#         logger.info(f"사용자가 음식 이미지를 사용하지 않음: {member_id}")
#         raise InvalidFoodImageError()    

#     # 문자열로 반환된 데이터 JSON으로 변환
#     detected_food_data = json.loads(detected_food_data)
        
#     # 유사도 검색 결과 저장할 리스트 초기화
#     similar_food_results = []

#     # 유사도 검색 진행
#     for food_data in detected_food_data:

#         # 데이터 형식 확인 후 인덱싱 접근
#         food_name = food_data.get("food_name")

#         # 음식명 누락 처리
#         if not food_name:
#             continue
        

#         # 벡터 임베딩 기반 유사도 검색 진행
#         similar_foods = await search_similar_food(food_name)
#         # 검색 결과(임계값으로 필터링된 결과 포함)
#         similar_food_list = [
#             {"food_name": food["food_name"], "food_pk": food["food_pk"]}
#             for food in similar_foods
#         ]

#         # 반환값 구성
#         similar_food_results.append({
#             "detected_food": food_name,
#             "similar_foods": similar_food_list
#         })
    
#     """
#     2. 요청 횟수 제한 구현(Redis)
#     """

#     # 요청 횟수 차감: 해당 부분에 존재해야지 분석 실패했을 때는 횟수 차감 x
#     remaining_requests = rate_limit_user(member_id, increment=True)

#     response = {
#         "success": True,
#         "response": {
#             "remaining_requests": remaining_requests,
#             "food_info": similar_food_results
#         },
#         "error": None
#     }

#     # 종료 시간 기록
#     end_time = time.time()
#     execution_time = end_time - start_time
#     logger.info(f"analyze_food_image API 수행 시간: {execution_time:.4f}초")

#     return response


# 기능 잔여 횟수 확인 API
@router.get("/count", responses=remaining_requests_check_responses)
async def remaning_requests_check(member_id: int = Depends(get_current_member)):

    """
    사용자의 남은 요청 횟수 반환
    """
    remaining_requests = await get_remaining_requests(member_id)

    response = {
        "success": True,
        "response": {
            "remaining_requests": remaining_requests
        },
        "error": None
    }

    return response


# 음식 이미지 분석 API 평가 테스트
@router.post("/image", responses=analyze_food_image_responses)
async def analyze_food_image(file: UploadFile = File(...), member_id: int = Depends(get_current_member)):
    start_total = time.time()

    # 이미지 처리 및 Base64 변환
    image_base64 = await process_image_to_base64(file)

    # OpenAI 음식 감지 시간 측정
    start_analyze = time.time()
    detected_food_data = await food_image_analyze(image_base64)
    end_analyze = time.time()
    analyze_time = round(end_analyze - start_analyze, 4)

    # JSON 변환 확인 및 오류 방지
    if isinstance(detected_food_data, str):
        try:
            detected_food_data = json.loads(detected_food_data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON: {e}")

    if not isinstance(detected_food_data, list):
        raise ValueError("Unexpected response format, expected a list of dicts")

    # 유사도 분석 시간 측정
    start_search = time.time()
    food_info = []
    for food in detected_food_data:
        if isinstance(food, dict) and "food_name" in food:
            similar_foods = await search_similar_food(food["food_name"])
            food_info.append({
                "detected_food": food["food_name"],
                "similar_foods": similar_foods
            })
        else:
            print(f"Skipping invalid food item: {food}")
    end_search = time.time()
    search_time = round(end_search - start_search, 4)

    total_time = round(time.time() - start_total, 4)

    return {
        "success": True,
        "food_image_analyze_time": analyze_time,
        "search_similar_time": search_time,
        "total_time": total_time,
        "response": {
            "food_info": food_info
        }
    }